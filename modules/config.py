import os
from dotenv import load_dotenv
from configparser import ConfigParser

# Load variables from the .env file
load_dotenv()

# Load settings
config = ConfigParser()
config.read("../settings.ini")

# Extract settings
REFRESH_RATE = int(config["GENERAL"]["refresh_rate"])
MIN_PROFIT = float(config["GENERAL"]["min_profit"])
MIN_PRICE = float(config["GENERAL"]["min_price"])
SOUND_PROFIT = float(config["GENERAL"]["sound_profit"])

NOTIFICATION_SOUND = os.getenv("NOTIFICATION_SOUND")
DB_FILE = os.getenv("DB_FILE")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
BASE_URL = os.getenv("BASE_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CACHE_DURATION_HOURS = os.getenv("CACHE_DURATION_HOURS")
CACHE_FILE = os.getenv("CACHE_FILE")

ALLOWED_DRMS = os.getenv("ALLOWED_DRMS", "")
ALLOWED_DRMS = [drm.strip() for drm in ALLOWED_DRMS.split(",") if drm.strip()]