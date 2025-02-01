import sqlite3
from datetime import datetime
from modules.config import DB_FILE

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