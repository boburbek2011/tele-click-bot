import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = "8866043896:AAE6u-f3FoitRJc_ZDSJ4nBfGbbDaJDW_bs"
ADMIN_IDS = [8645173973]  # Asosiy admin
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.onrender.com")

# Darajalar uchun EXP talablari
LEVEL_EXP = {
    1: 0,
    2: 100,
    3: 1000,
    4: 10000,
    5: 100000,
    6: 150000,
    7: 210000,
    8: 1000000,
    9: 2600000,
    10: 5000000
}

# Har bir bosish uchun beriladigan coin va exp
CLICK_COIN = 1
CLICK_EXP = 10

# Olmos narxi
DIAMOND_PRICE = 1500000  # 1.5 mln coin

# Auktsion foizlari
AUCTION_WINNER_PERCENT = 95
AUCTION_SECOND_PERCENT = 2
AUCTION_BOT_PERCENT = 3

# Max chat message length
MAX_MESSAGE_LENGTH = 500

# Database path
DB_PATH = "tele_click.db"