# 🎮 GG-Deals Scraper Bot

A robust Discord notification bot that periodically scrapes [GG-Deals](https://gg.deals) for the latest game offers, evaluates potential profits from reselling on platforms like Kinguin and G2A, and sends detailed notifications directly to your Discord webhook.

This project is intended for **demonstration purposes only** and is **not fully functional** in its public form. Certain core components have been intentionally removed or modified to prevent misuse or unauthorized deployment.

If you're a recruiter or interviewer and would like to see the complete working version, feel free to reach out — I'm happy to provide access upon request.

## 📸 Example Notifications

![Discord Notifications Example](assets/notification_example_1.png)
![Discord Notifications Example](assets/notification_example_2.png)

---

## 🚀 Features

- **Periodic Web Scraping**: Automatically fetches new offers from GG-Deals.
- **Real-Time Price Analysis**: Compares current lowest prices with Kinguin and G2A, calculating potential profits after fees.
- **Dynamic Currency Conversion**: Uses real-time EUR/USD/PLN exchange rates for accurate profit calculations.
- **Discord Integration**: Sends clean, visually appealing notifications to Discord with profit analysis, using a color-coded embed (`diff` trick) for quick profit/loss visibility.
- **Customizable Notifications**: Set profit thresholds and notification sounds directly from the configuration file.
- **Data Persistence**: Stores historical listings in a local database to prevent duplicate processing and enable future analysis.

---

## ⚙️ Installation

### Clone Repository
```bash
git clone YOUR_REPOSITORY_URL
cd gg-deals-scraper
```

### Install Dependencies
Ensure Python 3.9+ is installed, then run:
```bash
pip install -r requirements.txt
```

### Requirements
```
aiohttp==3.9.3
beautifulsoup4==4.13.3
pygame==2.6.0
python-dotenv==1.1.0
requests==2.32.3
selenium==4.30.0
webdriver_manager==4.0.2
```

---

## 🔧 Configuration

Create a `.env` file based on the provided `.env.example`:

```env
# Database file location
DB_FILE=your_database_file.db

# Chromedriver executable path
CHROMEDRIVER_PATH=path/to/chromedriver.exe

# List allowed DRM platforms separated by commas (e.g., Steam,Origin)
ALLOWED_DRMS=Steam,Origin

# Your Discord webhook URL
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK

# Duration for cached exchange rates in hours (recommended: 24)
CACHE_DURATION_HOURS=24

# Cache file for exchange rates
CACHE_FILE=exchange_rates.json

# Base URL for GG-Deals
BASE_URL=https://gg.deals
```

Replace placeholders (such as `your_database_file.db`, webhook URLs, and paths) with your actual values.

---

### 🔔 Notification Customization
- Adjust the notification thresholds directly within the configuration to filter notifications based on profitability.
- Notifications will appear green (profitable) or red (unprofitable) for quick evaluation.
- Sound alerts can be configured to trigger only when specific profitability thresholds are met.

---

## 📚 Database
The bot maintains an SQLite database for:
- Tracking processed listings to avoid duplication.
- Facilitating future data analysis and insights.

---

## 🙌 Acknowledgements
- [GG-Deals](https://gg.deals) for providing price data.
- ExchangeRate-API for currency conversion data.

