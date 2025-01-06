import aiohttp
import asyncio
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from get_cookies import get_gg_deals_session

# Constants
BASE_URL = "https://gg.deals"
LIST_URL = f"{BASE_URL}/deals/new-deals/"
KEYSHOP_URL_TEMPLATE = f"{BASE_URL}/pl/games/keyshopsDeals/{{game_id}}/"
DB_FILE = "listing_data.db"  # SQLite database file

# Settings
filter_mode = True  # Toggle DRM filtering on/off
allowed_drms = ["Steam", "Battle.net"]  # DRMs to focus on when filter_mode is True

# Initialize cookies and CSRF token
gg_session, gg_csrf, csrf_token = get_gg_deals_session()

# Create cookies dictionary for requests
SESSION_COOKIES = {
    "gg-session": gg_session,
    "gg_csrf": gg_csrf
}

# Global variable for tracking the last check
last_check = datetime.now(timezone.utc)


# Database Functions
def initialize_database():
    """Create the database and table if they do not exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            name TEXT NOT NULL,
            drm TEXT NOT NULL,
            price REAL NOT NULL,
            created_at TEXT NOT NULL,
            url TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_to_database(game_id, name, drm, price, url):
    """Save a new listing to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO listings (game_id, name, drm, price, created_at, url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (game_id, name, drm, price, created_at, url))
    conn.commit()
    conn.close()


# Extract Functions
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


# Main Logic
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

        # Apply DRM filter if filter_mode is enabled
        if filter_mode and drm not in allowed_drms:
            print(f"Skipping {game_name} due to DRM ({drm}) not in allowed DRMs.")
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


async def fetch_keyshops(session, game_id, listing_drm):
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

    async with session.post(keyshop_url, data=payload, headers=headers, cookies=SESSION_COOKIES) as response:
        if response.status != 200:
            print(f"Failed to fetch keyshops for game ID {game_id}, status: {response.status}")
            return None

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


async def process_listing(session, listing):
    game_id = listing["game_id"]
    game_name = listing["game_name"]
    drm = listing["drm"]
    listing_url = listing["listing_url"]
    current_price = listing["current_price"]

    # Save to database
    save_to_database(game_id, game_name, drm, current_price, listing_url)
    print(f"Saved listing: {game_name} ({drm}, {current_price})")

    # Fetch and print keyshop prices
    keyshop_data = await fetch_keyshops(session, game_id, drm)
    if keyshop_data:
        kinguin_price = keyshop_data['kinguin_price']
        g2a_price = keyshop_data['g2a_price']
        print(f"Kinguin: {kinguin_price}, G2A: {g2a_price}, [{game_name}]")
    else:
        print(f"No keyshop data for {game_name}")

async def check_new_listings():
    global last_check
    async with aiohttp.ClientSession() as session:
        while True:
            listings = await fetch_listings(session)
            
            # Debugging: Use a fixed timedelta threshold
            threshold_time = datetime.now(timezone.utc) - timedelta(minutes=90)
            new_listings = [
                listing for listing in listings
                if listing["listing_time"] > threshold_time
            ]

            tasks = [process_listing(session, listing) for listing in new_listings]
            await asyncio.gather(*tasks)

            last_check = datetime.now(timezone.utc)
            await asyncio.sleep(30)


if __name__ == "__main__":
    initialize_database()
    asyncio.run(check_new_listings())
