import os
import json
from datetime import datetime, timedelta
from modules.tax_settings import TAX_SETTINGS
import requests
from modules.config import (
    CACHE_DURATION_HOURS,
    CACHE_FILE,
    EUR_TO_USD_URL,
    USD_TO_PLN_URL
)

def get_exchange_rates():
    """Fetch or retrieve cached exchange rates for EUR/USD and USD/PLN."""
    # Check if the cache file exists
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            cache_data = json.load(file)
            last_updated = datetime.fromisoformat(cache_data["placeholderValue"])
            if datetime.now() - last_updated < timedelta(hours=CACHE_DURATION_HOURS):
                # Return cached rates if still fresh
                return cache_data["placeholderValue"], cache_data["placeholderValue"]

    # Fetch fresh rates if cache is missing or stale
    eur_to_usd_response = requests.get(EUR_TO_USD_URL)
    usd_to_pln_response = requests.get(USD_TO_PLN_URL)

    if eur_to_usd_response.status_code != 200 or usd_to_pln_response.status_code != 200:
        raise Exception("Failed to fetch exchange rates.")

    eur_to_usd_rate = eur_to_usd_response.json()["rates"]["placeholderValue"]
    usd_to_pln_rate = usd_to_pln_response.json()["rates"]["placeholderValue"]

    # Save the new rates to the cache file
    with open(CACHE_FILE, "w") as file:
        json.dump({
            "placeholderValue": datetime.now().isoformat(),
            "placeholderValue": eur_to_usd_rate,
            "placeholderValue": usd_to_pln_rate
        }, file)

    return eur_to_usd_rate, usd_to_pln_rate

def calculate_profit(price_zl, platform, exchange_rates):
    """Calculate the profit after tax for Kinguin or G2A."""
    eur_to_usd_rate, usd_to_pln_rate = exchange_rates
    exchange_rate = eur_to_usd_rate * usd_to_pln_rate  # EUR to PLN

    if platform not in TAX_SETTINGS:
        raise ValueError(f"Unknown platform: {platform}")

    platform_tax = TAX_SETTINGS[platform]
    fixed_tax_pln = platform_tax["placeholderValue"] * exchange_rate
    variable_tax_pln = platform_tax["placeholderValue"] * price_zl

    profit = price_zl - fixed_tax_pln - variable_tax_pln
    return profit
