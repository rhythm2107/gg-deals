import requests
from datetime import datetime
from tax_calculations import calculate_profit, get_exchange_rates
from tax_settings import TAX_SETTINGS

# Discord webhook URL
webhook_url = "https://discord.com/api/webhooks/1325877605747921006/9_3qtzLplhBN5hllMsNYhdfxBL5AMHvR0evWVymXpi-7YKXkHgYQzHAsGr_VrLNStUoW"

# Platform-specific emojis
platform_emojis = {
    "Steam": "<:steam:1260267708717465721>",
    "Other DRM": "<:otherdrm:1260269158403145820>"
}

def send_discord_notification(listing):
    """Send a notification to Discord for a given listing."""
    # Extract listing details
    game_name = listing.get('name', 'Unknown Game')
    price = listing.get('price', 'N/A')
    url = listing.get('url', '#')
    drm = listing.get('drm', 'Other DRM')

    # Prepare the platform display with emoji
    platform_display = platform_emojis.get(drm, drm)

    # Fetch exchange rates
    exchange_rates = get_exchange_rates()

    # Calculate profits for Kinguin and G2A
    kinguin_profit = (
        calculate_profit(listing.get("kinguin_price", 0), "kinguin", exchange_rates)
        if listing.get("kinguin_price") is not None else "N/A"
    )
    g2a_profit = (
        calculate_profit(listing.get("g2a_price", 0), "g2a", exchange_rates)
        if listing.get("g2a_price") is not None else "N/A"
    )

    # Prepare the embed for Discord
    embed = {
        "title": game_name,
        "url": url,
        "fields": [
            {"name": "Current Price", "value": f"```css\n{price} USD\n```", "inline": True},
            {"name": "Platform", "value": platform_display, "inline": True},
            {"name": "Kinguin Profit", "value": f"```diff\n{kinguin_profit:.2f} PLN\n```" if kinguin_profit != "N/A" else "N/A", "inline": True},
            {"name": "G2A Profit", "value": f"```diff\n{g2a_profit:.2f} PLN\n```" if g2a_profit != "N/A" else "N/A", "inline": True}
        ]
    }

    # Data payload for the webhook
    data = {
        "content": None,
        "embeds": [embed]
    }

    # Send the POST request to Discord
    response = requests.post(webhook_url, json=data)
    if response.status_code != 204:
        print(f"Failed to send notification: {response.status_code}, {response.text}")
    else:
        print(f"Notification sent for {game_name}")
