import os
import json
from datetime import datetime, timedelta
from tax_settings import TAX_SETTINGS
import requests

CACHE_FILE = "exchange_rates.json"
CACHE_DURATION_HOURS = 24

def get_exchange_rates():
    """Fetch or retrieve cached exchange rates for EUR/USD and USD/PLN."""
    # Check if the cache file exists
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            cache_data = json.load(file)
            last_updated = datetime.fromisoformat(cache_data["last_updated"])
            if datetime.now() - last_updated < timedelta(hours=CACHE_DURATION_HOURS):
                # Return cached rates if still fresh
                return cache_data["eur_to_usd"], cache_data["usd_to_pln"]

    # Fetch fresh rates if cache is missing or stale
    eur_to_usd_url = "https://api.exchangerate-api.com/v4/latest/EUR"
    usd_to_pln_url = "https://api.exchangerate-api.com/v4/latest/USD"

    eur_to_usd_response = requests.get(eur_to_usd_url)
    usd_to_pln_response = requests.get(usd_to_pln_url)

    if eur_to_usd_response.status_code != 200 or usd_to_pln_response.status_code != 200:
        raise Exception("Failed to fetch exchange rates.")

    eur_to_usd_rate = eur_to_usd_response.json()["rates"]["USD"]
    usd_to_pln_rate = usd_to_pln_response.json()["rates"]["PLN"]

    # Save the new rates to the cache file
    with open(CACHE_FILE, "w") as file:
        json.dump({
            "last_updated": datetime.now().isoformat(),
            "eur_to_usd": eur_to_usd_rate,
            "usd_to_pln": usd_to_pln_rate
        }, file)

    return eur_to_usd_rate, usd_to_pln_rate

def calculate_profit(price_zl, platform, exchange_rates):
    """Calculate the profit after tax for Kinguin or G2A."""
    eur_to_usd_rate, usd_to_pln_rate = exchange_rates
    exchange_rate = eur_to_usd_rate * usd_to_pln_rate  # EUR to PLN

    if platform not in TAX_SETTINGS:
        raise ValueError(f"Unknown platform: {platform}")

    platform_tax = TAX_SETTINGS[platform]
    fixed_tax_pln = platform_tax["fixed_tax_eur"] * exchange_rate
    variable_tax_pln = platform_tax["variable_tax"] * price_zl

    profit = price_zl - fixed_tax_pln - variable_tax_pln
    return profit
