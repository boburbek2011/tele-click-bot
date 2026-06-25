import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "tele_click.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                coins INTEGER DEFAULT 0,
                exp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                diamonds INTEGER DEFAULT 0,
                title TEXT DEFAULT '🟢 Yangi o\'yinchi',
                color TEXT DEFAULT '#00ff88',
                total_clicks INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Auctions table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS auctions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                item_name TEXT,
                item_description TEXT,
                start_price INTEGER,
                current_bid INTEGER,
                current_bidder_id INTEGER,
                end_time TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Auction bids table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS auction_bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_id INTEGER,
                user_id INTEGER,
                bid_amount INTEGER,
                bid_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Promo codes table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                coins INTEGER DEFAULT 0,
                exp INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Promo usage table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promo_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, promo_id)
            )
        ''')
        
        # Transactions table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER,
                to_user INTEGER,
                amount INTEGER,
                type TEXT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()

async def create_user(user_id, username, first_name, last_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users 
               (user_id, username, first_name, last_name) 
               VALUES (?, ?, ?, ?)""",
            (user_id, username, first_name, last_name)
        )
        await db.commit()

async def update_user_stats(user_id, coins_delta=0, exp_delta=0, clicks_delta=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users 
               SET coins = coins + ?, 
                   exp = exp + ?,
                   total_clicks = total_clicks + ?
               WHERE user_id = ?""",
            (coins_delta, exp_delta, clicks_delta, user_id)
        )
        await db.commit()

async def get_top_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, first_name, coins, level FROM users ORDER BY coins DESC LIMIT ?",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def get_user_by_username(username):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ) as cursor:
            return await cursor.fetchone()