import requests
from datetime import datetime
from tax_calculations import calculate_profit, get_exchange_rates
import sqlite3

# Define Discord Webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1325877605747921006/9_3qtzLplhBN5hllMsNYhdfxBL5AMHvR0evWVymXpi-7YKXkHgYQzHAsGr_VrLNStUoW"

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

    # Convert the current price to PLN
    current_price_pln = listing["price"] * exchange_rates[1]

    # Convert keyshop prices to PLN and calculate profits
    kinguin_profit = None
    g2a_profit = None
    kinguin_price_pln = None
    g2a_price_pln = None

    if listing.get("kinguin_price"):
        kinguin_price_pln = listing["kinguin_price"] * exchange_rates[1]
        kinguin_profit = calculate_profit(kinguin_price_pln, "Kinguin", exchange_rates) - current_price_pln

    if listing.get("g2a_price"):
        g2a_price_pln = listing["g2a_price"] * exchange_rates[1]
        g2a_profit = calculate_profit(g2a_price_pln, "G2A", exchange_rates) - current_price_pln

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
            {"name": "Kinguin Profit", "value": f"```diff\n+{kinguin_profit:.2f} zł\n```" if kinguin_profit else "N/A", "inline": True},
            {"name": "G2A Profit", "value": f"```diff\n+{g2a_profit:.2f} zł\n```" if g2a_profit else "N/A", "inline": True},
            {"name": "Platform", "value": platform_emoji, "inline": True},
            {"name": "Average Price", "value": f"```ini\n{avg_price:.2f} zł\n```" if avg_price else "N/A", "inline": True},
            {"name": "Last 10 Prices", "value": last_10_prices_str, "inline": False}
        ]
    }

    data = {
        "content": None,
        "embeds": [embed]
    }

    # Send the notification to Discord
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code != 204:
        print(f"Failed to send notification: {response.status_code}, {response.text}")


# Sample listing for testing
sample_listing = {
    "name": "Craft The World",
    "game_id": 2074,
    "price": 8,  # Current price in USD
    "kinguin_price": 10,  # Kinguin price in USD
    "g2a_price": 12,  # G2A price in USD
    "drm": "Steam",  # DRM platform
    "listing_url": "https://gg.deals/game/craft-the-world/"
}

# Call the function to test it
send_discord_notification(sample_listing)
