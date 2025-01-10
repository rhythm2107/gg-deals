import requests
import sqlite3
from datetime import datetime
from tax_calculations import calculate_profit, get_exchange_rates

# Allowed DRMs
allowed_drms = ["Steam", "Ubisoft Connect"]

# Define Discord Webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1355271759888126294/4QPFDei11Xyogm_6I0Purp72XIzeGa7OWXBjRU3-0PXJdNlV4HMYd3mKf7CWKnhg13gG"

# Platform emojis for Discord notifications
PLATFORM_EMOJIS = {
    "Steam": "<:steam:1260267708717465721>",
    "Other DRM": "<:innyklucz:1260269158403145820>"
}

def fetch_price_data(game_id, drm, db_path="listing_data.db"):
    """
    Fetch average price and last 10 prices for a given game ID and DRM from the SQLite database.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Calculate the average price
    cursor.execute(
        "SELECT AVG(price) FROM listings WHERE game_id = ? AND drm = ?",
        (game_id, drm)
    )
    avg_price = cursor.fetchone()[0]

    # Fetch the last 10 prices
    cursor.execute(
        "SELECT price, created_at FROM listings WHERE game_id = ? AND drm = ? ORDER BY created_at DESC LIMIT 10",
        (game_id, drm)
    )
    last_10_prices = cursor.fetchall()

    conn.close()
    return avg_price, last_10_prices

def format_last_10_prices(last_10_prices):
    """
    Format the last 10 prices into a readable string for Discord notifications.
    Extract only the date (year-month-day) from the timestamp.
    """
    return "\n".join([f"{price[0]:.2f} zł ({price[1][:10]})" for price in last_10_prices])

def send_discord_notification(listing, db_path="listing_data.db"):
    """
    Send a notification to Discord for a given listing.
    """
    # Fetch exchange rates
    exchange_rates = get_exchange_rates()

    # Prices are already in PLN
    current_price_pln = listing["price"]
    kinguin_price_pln = listing.get("kinguin_price")
    g2a_price_pln = listing.get("g2a_price")

    # Calculate profits using the tax formulas
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

    # Fetch average price and last 10 prices from the database
    avg_price, last_10_prices = fetch_price_data(listing["game_id"], listing["drm"], db_path)

    # Format the last 10 prices
    last_10_prices_str = format_last_10_prices(last_10_prices)

    # Platform emoji
    platform = listing["drm"]
    platform_emoji = PLATFORM_EMOJIS.get(platform, platform)

    # Prepare the embed payload
    embed = {
        "title": listing["name"],
        "url": listing["listing_url"],
        "fields": [
            {"name": "Current Price", "value": f"```css\n{current_price_pln:.2f} zł\n```", "inline": True},
            {"name": "Kinguin Price", "value": f"```css\n{kinguin_price_pln:.2f} zł\n```" if kinguin_price_pln else "N/A", "inline": True},
            {"name": "G2A Price", "value": f"```css\n{g2a_price_pln:.2f} zł\n```" if g2a_price_pln else "N/A", "inline": True},
            {"name": "Kinguin Profit", "value": f"```diff\n{'+ ' if kinguin_profit and kinguin_profit > 0 else ''}{kinguin_profit:.2f} zł\n```" if kinguin_profit is not None else "N/A", "inline": True},
            {"name": "G2A Profit", "value": f"```diff\n{'+ ' if g2a_profit and g2a_profit > 0 else ''}{g2a_profit:.2f} zł\n```" if g2a_profit is not None else "N/A", "inline": True},
            {"name": "Platform", "value": platform_emoji, "inline": True},
            {"name": "Average Price", "value": f"```ini\n{avg_price:.2f} zł\n```" if avg_price else "N/A", "inline": True},
            {"name": "Last 10 Prices", "value": last_10_prices_str, "inline": False}
        ]
    }

    data = {
        "content": None,
        "embeds": [embed]
    }

    print(listing["drm"])

    if listing["drm"] in allowed_drms:
        # Send the notification to Discord
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code != 204:
            print(f"Failed to send notification: {response.status_code}, {response.text}")
    else:
        print(f"{listing["drm"]} is not in allowed list. Skipping!")
