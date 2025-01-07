import aiohttp
import asyncio
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from configparser import ConfigParser
from discord_notification import send_discord_notification
from get_cookies import get_gg_deals_session
from tax_calculations import calculate_profit, get_exchange_rates
from database import initialize_database, save_to_database
import pygame

# Load settings
config = ConfigParser()
config.read("settings.ini")

# Extract settings
REFRESH_RATE = int(config["GENERAL"]["refresh_rate"])
MIN_PROFIT = float(config["GENERAL"]["min_profit"])
MIN_PRICE = float(config["GENERAL"]["min_price"])
SOUND_PROFIT = float(config["GENERAL"]["sound_profit"])

# Initialize pygame for sound notifications
pygame.init()
NOTIFICATION_SOUND = "notification_sound.mp3"

# Constants
BASE_URL = "https://gg.deals"
LIST_URL = f"{BASE_URL}/deals/new-deals/"
KEYSHOP_URL_TEMPLATE = f"{BASE_URL}/pl/games/keyshopsDeals/{{game_id}}/"
DB_FILE = "listing_data.db"  # SQLite database file

# Initialize cookies and CSRF token
gg_session, gg_csrf, csrf_token = get_gg_deals_session()

# Create cookies dictionary for requests
SESSION_COOKIES = {
    "gg-session": gg_session,
    "gg_csrf": gg_csrf
}

# Helper Functions
def extract_drm_from_listing(listing_html):
    """Extract DRM from the listing HTML."""
    soup = BeautifulSoup(listing_html, 'html.parser')
    drm_tag = soup.find("div", class_="tag-drm")
    if drm_tag:
        svg_tag = drm_tag.find("svg")
        if svg_tag and "title" in svg_tag.attrs:
            return svg_tag["title"].replace("Activates on ", "").strip()
    return None


def extract_listing_details(listing_html):
    """Extract additional details (game name, URL, price) from a listing."""
    soup = BeautifulSoup(listing_html, 'html.parser')

    # Full game name and URL
    link_tag = soup.find("a", class_="full-link")
    if link_tag:
        game_name = link_tag.get("aria-label", "").replace("Go to: ", "").strip()
        listing_url = BASE_URL + link_tag.get("href", "")
    else:
        game_name = "Unknown Game"
        listing_url = None

    # Current price
    price = soup.find("div", class_="hoverable-box").get("data-deal-value", None)

    return game_name, listing_url, float(price) if price else None


# Fetch Functions
async def fetch_html(session, url):
    async with session.get(url) as response:
        if response.status != 200:
            print(f"Failed to fetch {url}")
            return None
        return await response.text()


async def fetch_listings(session):
    html_content = await fetch_html(session, LIST_URL)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    listings = soup.find_all('div', class_='hoverable-box')

    extracted_listings = []
    for listing in listings:
        listing_html = str(listing)
        game_id = listing.get('data-container-game-id')
        drm = extract_drm_from_listing(listing_html)
        game_name, listing_url, price = extract_listing_details(listing_html)

        if not drm:
            continue

        time_tag = listing.find('time')
        if not time_tag:
            continue

        listing_time = datetime.fromisoformat(time_tag['datetime']).astimezone(timezone.utc)
        extracted_listings.append({
            "game_id": game_id,
            "game_name": game_name,
            "listing_url": listing_url,
            "current_price": price,
            "listing_time": listing_time,
            "drm": drm
        })

    return extracted_listings


async def fetch_keyshops(session, game_id, listing_drm, retries=3):
    """Fetch keyshop prices for a game with retry logic."""
    keyshop_url = KEYSHOP_URL_TEMPLATE.format(game_id=game_id)
    payload = {'gg_csrf': csrf_token}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': LIST_URL,
        'X-CSRF-Token': csrf_token,
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': BASE_URL,
        'x-requested-with': 'XMLHttpRequest'
    }

    for attempt in range(retries):
        try:
            async with session.post(keyshop_url, data=payload, headers=headers, cookies=SESSION_COOKIES) as response:
                if response.status == 200:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')

                    keyshops = []
                    keyshop_divs = soup.select('div[data-shop-name]')
                    for shop in keyshop_divs:
                        shop_name = shop.get('data-shop-name', '').lower()
                        price = shop.get('data-deal-value')
                        drm = extract_drm_from_listing(str(shop))

                        if not drm or drm != listing_drm:
                            continue

                        keyshops.append({"name": shop_name, "price": float(price), "drm": drm})

                    kinguin_price = next((shop['price'] for shop in keyshops if shop['name'] == 'kinguin'), None)
                    g2a_price = next((shop['price'] for shop in keyshops if shop['name'] == 'g2a'), None)

                    return {"kinguin_price": kinguin_price, "g2a_price": g2a_price}

                print(f"Attempt {attempt + 1}: Failed to fetch keyshops for game ID {game_id}, status: {response.status}")
        except (aiohttp.ClientError, ConnectionResetError) as e:
            print(f"Attempt {attempt + 1}: Connection error while fetching keyshops for game ID {game_id}: {e}")

        await asyncio.sleep(1)  # Add a short delay between retries

    print(f"Failed to fetch keyshops for game ID {game_id} after {retries} attempts.")
    return None


async def process_listing(session, listing):
    """Process a single listing."""
    game_id = listing["game_id"]
    game_name = listing["game_name"]
    drm = listing["drm"]
    listing_url = listing["listing_url"]
    current_price = listing["current_price"]

    # Save to database
    save_to_database(game_id, game_name, drm, current_price, listing_url)
    print(f"Saved listing: {game_name} ({drm}, {current_price})")

    # Fetch keyshop prices
    keyshop_data = await fetch_keyshops(session, game_id, drm)
    if not keyshop_data:
        print(f"No keyshop data for {game_name}")
        return

    kinguin_price = keyshop_data['kinguin_price']
    g2a_price = keyshop_data['g2a_price']
    print(f"Kinguin: {kinguin_price}, G2A: {g2a_price}, [{game_name}]")

    # Fetch exchange rates
    exchange_rates = get_exchange_rates()
    usd_to_pln = exchange_rates[1]

    # Convert prices to PLN
    current_price_pln = current_price * usd_to_pln
    kinguin_price_pln = kinguin_price * usd_to_pln if kinguin_price else None
    g2a_price_pln = g2a_price * usd_to_pln if g2a_price else None

    # Calculate profits
    kinguin_profit = (
        calculate_profit(kinguin_price_pln, "Kinguin", exchange_rates) - current_price_pln
        if kinguin_price_pln
        else None
    )
    g2a_profit = (
        calculate_profit(g2a_price_pln, "G2A", exchange_rates) - current_price_pln
        if g2a_price_pln
        else None
    )

    # Debugging profit values
    print(f"Debug: {game_name} | Current Price PLN: {current_price_pln:.2f} | Kinguin Profit: {kinguin_profit} | G2A Profit: {g2a_profit}")

    # Determine if a Discord notification should be sent
    if max(kinguin_profit or 0, g2a_profit or 0) >= MIN_PROFIT:
        send_discord_notification({
            "name": game_name,
            "game_id": game_id,
            "price": current_price,
            "kinguin_price": kinguin_price,
            "g2a_price": g2a_price,
            "drm": drm,
            "listing_url": listing_url
        })

    # Sound notification for high profits
    max_profit = max(kinguin_profit or 0, g2a_profit or 0)
    if max_profit >= SOUND_PROFIT:
        print(f"Sound Triggered: {game_name} | Max Profit: {max_profit:.2f}")
        pygame.mixer.Sound(NOTIFICATION_SOUND).play()
    else:
        print(f"Sound Skipped: {game_name} | Max Profit: {max_profit:.2f} (Below {SOUND_PROFIT})")

async def check_new_listings():
    """Check for new listings and process them."""
    async with aiohttp.ClientSession() as session:
        while True:
            listings = await fetch_listings(session)
            new_listings = [l for l in listings if l["current_price"] >= MIN_PRICE]

            tasks = [process_listing(session, listing) for listing in new_listings]
            await asyncio.gather(*tasks)

            # Print message before sleep
            print(f"Iteration finished, starting again in {REFRESH_RATE} seconds.")
            
            await asyncio.sleep(REFRESH_RATE)

if __name__ == "__main__":
    initialize_database()
    asyncio.run(check_new_listings())