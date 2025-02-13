import aiohttp
import asyncio
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from modules.discord_notification import send_discord_notification
from modules.get_cookies import get_gg_deals_session
from modules.tax_calculations import calculate_profit, get_exchange_rates
from modules.database import initialize_database, save_to_database
from modules.extract import extract_drm_from_listing, extract_listing_details
from modules.logger import get_logger
import pygame
import logging
import os
from modules.config import (
    NOTIFICATION_SOUND,
    REFRESH_RATE,
    MIN_PROFIT,
    MIN_PRICE,
    SOUND_PROFIT,
    BASE_URL
)

# Create 'debug' folder if it doesn't exist
os.makedirs('debug', exist_ok=True)

# Create a logging object
logger = get_logger('main')

# Initialize pygame for sound notifications
pygame.init()

# Constants
LIST_URL = f"{BASE_URL}/deals/new-deals/"
KEYSHOP_URL_TEMPLATE = f"{BASE_URL}/pl/games/keyshopsDeals/{{game_id}}/"

# Global variable to track the last check time
last_check = datetime.now(timezone.utc) - timedelta(minutes=45)  # Initialize to start 10 mins in the past

# Initialize cookies and CSRF token
gg_session, gg_csrf, csrf_token = get_gg_deals_session()

# Create cookies dictionary for requests
SESSION_COOKIES = {
    "gg-session": gg_session,
    "gg_csrf": gg_csrf
}

# Fetch Functions
async def fetch_html(session, url):
    async with session.get(url) as response:
        if response.status != 200:
            logger.info(f"Failed to fetch {url}")
            return None
        return await response.text()

async def fetch_listings(session):
    html_content = await fetch_html(session, LIST_URL)
    if not html_content:
        return []

    # Get exchange rates and calculate USD-to-PLN
    exchange_rates = get_exchange_rates()
    usd_to_pln = exchange_rates[1]

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

        # Convert current price to PLN
        current_price_pln = price * usd_to_pln

        extracted_listings.append({
            "game_id": game_id,
            "game_name": game_name,
            "listing_url": listing_url,
            "current_price": current_price_pln,  # Store price in PLN
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

                logger.info(f"Attempt {attempt + 1}: Failed to fetch keyshops for game ID {game_id}, status: {response.status}")
        except (aiohttp.ClientError, ConnectionResetError) as e:
            logger.info(f"Attempt {attempt + 1}: Connection error while fetching keyshops for game ID {game_id}: {e}")

        await asyncio.sleep(1)  # Add a short delay between retries

    logger.info(f"Failed to fetch keyshops for game ID {game_id} after {retries} attempts.")
    return None


async def process_listing(session, listing):
    """Process a single listing."""
    game_id = listing["game_id"]
    game_name = listing["game_name"]
    drm = listing["drm"]
    listing_url = listing["listing_url"]
    current_price = listing["current_price"]  # Already in PLN

    # Get exchange rates and calculate USD-to-PLN
    exchange_rates = get_exchange_rates()
    usd_to_pln = exchange_rates[1]

    # Ensure the current price meets the minimum price criteria
    if current_price < MIN_PRICE:
        logger.info(f"Skipping {game_name} due to price below MIN_PRICE: {current_price:.2f} PLN")
        return

    # Save to database
    save_to_database(game_id, game_name, drm, current_price, listing_url)
    logger.info(f"Saved listing: {game_name} ({drm}, {current_price:.2f} PLN)")

    # Fetch keyshop prices
    keyshop_data = await fetch_keyshops(session, game_id, drm)
    if not keyshop_data:
        logger.info(f"No keyshop data for {game_name}")
        return

    kinguin_price = keyshop_data['kinguin_price']
    g2a_price = keyshop_data['g2a_price']

    # Convert keyshop prices to PLN
    kinguin_price_pln = kinguin_price * usd_to_pln if kinguin_price else None
    g2a_price_pln = g2a_price * usd_to_pln if g2a_price else None

    # Calculate profits
    kinguin_profit = (
        calculate_profit(kinguin_price_pln, "Kinguin", exchange_rates) - current_price
        if kinguin_price_pln
        else None
    )
    g2a_profit = (
        calculate_profit(g2a_price_pln, "G2A", exchange_rates) - current_price
        if g2a_price_pln
        else None
    )

    # Determine if a Discord notification should be sent
    if max(kinguin_profit or 0, g2a_profit or 0) >= MIN_PROFIT:
        send_discord_notification({
            "name": game_name,
            "game_id": game_id,
            "price": current_price,  # Send price in PLN
            "kinguin_price": kinguin_price_pln,
            "g2a_price": g2a_price_pln,
            "drm": drm,
            "listing_url": listing_url
        })

    # Sound notification for high profits
    max_profit = max(kinguin_profit or 0, g2a_profit or 0)
    if max_profit >= SOUND_PROFIT:
        logger.info(f"[Massive Profit!] {game_name} | Max Profit: {max_profit:.2f} PLN")
        pygame.mixer.Sound(NOTIFICATION_SOUND).play()


async def check_new_listings():
    global last_check
    async with aiohttp.ClientSession() as session:
        while True:
            listings = await fetch_listings(session)

            # Filter listings posted after the last check
            new_listings = [
                listing for listing in listings
                if listing["listing_time"] > last_check and listing["current_price"] >= MIN_PRICE
            ]

            if new_listings:
                # Update the last check time to the latest listing's time
                last_check = max(l["listing_time"] for l in new_listings)

            tasks = [process_listing(session, listing) for listing in new_listings]
            await asyncio.gather(*tasks)

            logger.info(f"Iteration finished, starting again in {REFRESH_RATE} seconds. Last check updated to {last_check}.")
            await asyncio.sleep(REFRESH_RATE)  # Sleep for the refresh interval

if __name__ == "__main__":
    initialize_database()
    asyncio.run(check_new_listings())