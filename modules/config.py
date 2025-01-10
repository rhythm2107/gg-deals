import os
from dotenv import load_dotenv
from configparser import ConfigParser

# Load variables from the .env file
load_dotenv()

# Load settings
config = ConfigParser()
config.read("settings.ini")

# Extract settings
REFRESH_RATE = int(config["GENERAL"]["refresh_rate"])
MIN_PROFIT = float(config["GENERAL"]["min_profit"])
MIN_PRICE = float(config["GENERAL"]["min_price"])
SOUND_PROFIT = float(config["GENERAL"]["sound_profit"])

NOTIFICATION_SOUND = os.getenv("NOTIFICATION_SOUND")