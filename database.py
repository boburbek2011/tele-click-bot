import aiosqlite
from datetime import datetime, timedelta
import random

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
                title TEXT DEFAULT "🟢 Yangi oyinchi",
                color TEXT DEFAULT "#00ff88",
                total_clicks INTEGER DEFAULT 0,
                energy INTEGER DEFAULT 500,
                max_energy INTEGER DEFAULT 500,
                click_power INTEGER DEFAULT 1,
                offline_mining BOOLEAN DEFAULT 0,
                mining_rate INTEGER DEFAULT 0,
                last_energy_refill TIMESTAMP,
                auto_clicker_level INTEGER DEFAULT 0,
                active_skin_id INTEGER DEFAULT 0,
                multiplier INTEGER DEFAULT 1,
                multiplier_end_time TIMESTAMP,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Shop items table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                category TEXT,
                price INTEGER,
                level_required INTEGER DEFAULT 1,
                effect_type TEXT,
                effect_value INTEGER,
                emoji TEXT,
                is_available BOOLEAN DEFAULT 1
            )
        ''')
        
        # User inventory
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                quantity INTEGER DEFAULT 1,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, item_id)
            )
        ''')
        
        # Skins table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS skins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                emoji TEXT,
                rarity TEXT,
                level_required INTEGER DEFAULT 1,
                price INTEGER,
                multiplier INTEGER DEFAULT 1,
                is_available BOOLEAN DEFAULT 1
            )
        ''')
        
        # User skins
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_skins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                skin_id INTEGER,
                is_active BOOLEAN DEFAULT 0,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, skin_id)
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
        
        # Auction bids
        await db.execute('''
            CREATE TABLE IF NOT EXISTS auction_bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_id INTEGER,
                user_id INTEGER,
                bid_amount INTEGER,
                bid_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Promo codes
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
        
        # Promo usage
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promo_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, promo_id)
            )
        ''')
        
        # Transactions
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
        
        # Chat messages
        await db.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.commit()
        
        await init_shop_items()
        await init_skins()

async def init_shop_items():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM shop_items") as cursor:
            count = await cursor.fetchone()
            if count[0] > 0:
                return
        
        items = [
            ('Energiya +500', 'Maksimal energiyani 500 ga oshiradi', 'energy', 500, 1, 'max_energy', 500, '⚡'),
            ('Energiya +1000', 'Maksimal energiyani 1000 ga oshiradi', 'energy', 1500, 3, 'max_energy', 1000, '⚡'),
            ('Energiya +2000', 'Maksimal energiyani 2000 ga oshiradi', 'energy', 4000, 5, 'max_energy', 2000, '⚡'),
            ('Energiya +5000', 'Maksimal energiyani 5000 ga oshiradi', 'energy', 10000, 10, 'max_energy', 5000, '⚡'),
            
            ('Click Kuch +1', 'Har bir bosishda +1 qo\'shimcha', 'click', 300, 1, 'click_power', 1, '💪'),
            ('Click Kuch +2', 'Har bir bosishda +2 qo\'shimcha', 'click', 1000, 3, 'click_power', 2, '💪'),
            ('Click Kuch +5', 'Har bir bosishda +5 qo\'shimcha', 'click', 3000, 5, 'click_power', 5, '💪'),
            ('Click Kuch +10', 'Har bir bosishda +10 qo\'shimcha', 'click', 8000, 8, 'click_power', 10, '💪'),
            ('Click Kuch +20', 'Har bir bosishda +20 qo\'shimcha', 'click', 20000, 12, 'click_power', 20, '💪'),
            
            ('Auto Clicker Lv.1', 'Har 10 soniyada 1 ta avto bosish', 'auto', 2000, 2, 'auto_clicker', 1, '🤖'),
            ('Auto Clicker Lv.2', 'Har 10 soniyada 2 ta avto bosish', 'auto', 5000, 4, 'auto_clicker', 2, '🤖'),
            ('Auto Clicker Lv.3', 'Har 10 soniyada 3 ta avto bosish', 'auto', 10000, 6, 'auto_clicker', 3, '🤖'),
            ('Auto Clicker Lv.4', 'Har 10 soniyada 5 ta avto bosish', 'auto', 20000, 8, 'auto_clicker', 5, '🤖'),
            ('Auto Clicker Lv.5', 'Har 10 soniyada 10 ta avto bosish', 'auto', 50000, 12, 'auto_clicker', 10, '🤖'),
            
            ('Offline Mining', 'Offline mining yoqish (1 soat)', 'offline', 2000, 2, 'offline_mining', 1, '⛏️'),
            ('Offline Mining Pro', 'Offline mining yoqish (3 soat)', 'offline', 5000, 4, 'offline_mining', 3, '⛏️'),
            ('Offline Mining Elite', 'Offline mining yoqish (6 soat)', 'offline', 12000, 7, 'offline_mining', 6, '⛏️'),
            
            ('2x Multiplier', '30 daqiqa davomida 2x ko\'p', 'multiplier', 1000, 2, 'multiplier', 2, '🌟'),
            ('3x Multiplier', '30 daqiqa davomida 3x ko\'p', 'multiplier', 3000, 4, 'multiplier', 3, '🌟'),
            ('5x Multiplier', '30 daqiqa davomida 5x ko\'p', 'multiplier', 8000, 6, 'multiplier', 5, '🌟'),
            ('10x Multiplier', '30 daqiqa davomida 10x ko\'p', 'multiplier', 20000, 10, 'multiplier', 10, '🌟'),
        ]
        
        for item in items:
            await db.execute(
                """INSERT INTO shop_items 
                   (name, description, category, price, level_required, effect_type, effect_value, emoji) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                item
            )
        
        await db.commit()

async def init_skins():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM skins") as cursor:
            count = await cursor.fetchone()
            if count[0] > 0:
                return
        
        skins = [
            ('Yangi o\'yinchi', '🟢', 'common', 1, 0, 1),
            ('Tajribali', '🔵', 'common', 2, 500, 1),
            ('Usta', '🟣', 'common', 3, 1000, 1),
            ('Jangchi', '🔴', 'common', 4, 2000, 1),
            ('Qahramon', '🟠', 'common', 5, 3000, 1),
            
            ('Legend', '🟡', 'rare', 6, 5000, 2),
            ('Epic Warrior', '🟣', 'rare', 7, 8000, 2),
            ('Dragon Slayer', '🐉', 'rare', 8, 12000, 2),
            ('Phoenix', '🔥', 'rare', 9, 18000, 2),
            ('Shadow', '🌑', 'rare', 10, 25000, 2),
            
            ('Star Lord', '⭐', 'epic', 11, 40000, 4),
            ('God of War', '⚔️', 'epic', 12, 60000, 4),
            ('Angel', '👼', 'epic', 13, 80000, 4),
            ('Demon', '👿', 'epic', 14, 100000, 4),
            ('Dragon King', '🐲', 'epic', 15, 120000, 4),
            
            ('Legendary Hero', '🌟', 'legendary', 16, 200000, 10),
            ('God of Click', '👑', 'legendary', 18, 350000, 10),
            ('Immortal', '✨', 'legendary', 20, 500000, 10),
            ('Cosmic', '🌌', 'legendary', 25, 750000, 10),
            ('Infinity', '♾️', 'legendary', 30, 1000000, 10),
        ]
        
        for skin in skins:
            await db.execute(
                """INSERT INTO skins 
                   (name, emoji, rarity, level_required, price, multiplier) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                skin
            )
        
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
               (user_id, username, first_name, last_name, energy, max_energy, last_energy_refill) 
               VALUES (?, ?, ?, ?, 500, 500, datetime('now'))""",
            (user_id, username, first_name, last_name)
        )
        await db.commit()

async def update_user_stats(user_id, coins_delta=0, exp_delta=0, clicks_delta=0, 
                            level_update=None, energy_delta=0, max_energy_delta=0,
                            click_power_delta=0, auto_clicker_delta=0, multiplier_delta=0):
    async with aiosqlite.connect(DB_PATH) as db:
        if level_update is not None:
            await db.execute(
                """UPDATE users 
                   SET coins = coins + ?, 
                       exp = exp + ?,
                       total_clicks = total_clicks + ?,
                       level = ?,
                       energy = energy + ?,
                       max_energy = max_energy + ?,
                       click_power = click_power + ?,
                       auto_clicker_level = auto_clicker_level + ?,
                       multiplier = multiplier + ?
                   WHERE user_id = ?""",
                (coins_delta, exp_delta, clicks_delta, level_update, 
                 energy_delta, max_energy_delta, click_power_delta, auto_clicker_delta, multiplier_delta, user_id)
            )
        else:
            await db.execute(
                """UPDATE users 
                   SET coins = coins + ?, 
                       exp = exp + ?,
                       total_clicks = total_clicks + ?,
                       energy = energy + ?,
                       max_energy = max_energy + ?,
                       click_power = click_power + ?,
                       auto_clicker_level = auto_clicker_level + ?,
                       multiplier = multiplier + ?
                   WHERE user_id = ?""",
                (coins_delta, exp_delta, clicks_delta, 
                 energy_delta, max_energy_delta, click_power_delta, auto_clicker_delta, multiplier_delta, user_id)
            )
        await db.commit()

async def refill_energy(user_id):
    user = await get_user(user_id)
    if not user:
        return
    
    now = datetime.now()
    last_refill = user[16]
    
    if last_refill:
        try:
            last_time = datetime.fromisoformat(last_refill)
            diff = (now - last_time).total_seconds() / 60
            
            if diff >= 5:
                max_energy = user[12]
                current_energy = user[11]
                refill_amount = int(max_energy * 0.2)
                
                new_energy = min(max_energy, current_energy + refill_amount)
                
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE users SET energy = ?, last_energy_refill = datetime('now') WHERE user_id = ?",
                        (new_energy, user_id)
                    )
                    await db.commit()
        except:
            pass

async def get_shop_items():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM shop_items WHERE is_available = 1 ORDER BY price"
        ) as cursor:
            return await cursor.fetchall()

async def get_skins():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM skins WHERE is_available = 1 ORDER BY level_required, price"
        ) as cursor:
            return await cursor.fetchall()

async def get_user_skins(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT skin_id, is_active FROM user_skins WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

async def purchase_item(user_id, item_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM user_inventory WHERE user_id = ? AND item_id = ?",
            (user_id, item_id)
        ) as cursor:
            existing = await cursor.fetchone()
        
        if existing:
            await db.execute(
                "UPDATE user_inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
        else:
            await db.execute(
                "INSERT INTO user_inventory (user_id, item_id) VALUES (?, ?)",
                (user_id, item_id)
            )
        await db.commit()

async def get_required_exp(level):
    if level <= 5:
        return level * 100
    elif level <= 10:
        return level * 200
    elif level <= 15:
        return level * 300
    elif level <= 20:
        return level * 500
    else:
        return level * 800

async def get_user_total_multiplier(user_id):
    user = await get_user(user_id)
    if not user:
        return 1
    
    total_multiplier = 1
    
    if user[18] and user[18] > 0:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT multiplier FROM skins WHERE id = ?",
                (user[18],)
            ) as cursor:
                skin = await cursor.fetchone()
                if skin:
                    total_multiplier *= skin[0]
    
    if user[19] and user[19] > 1:
        total_multiplier *= user[19]
    
    return total_multiplier

# ==================== LEADERBOARD FUNCTIONS ====================

async def get_leaderboard_current(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT user_id, username, first_name, coins, level, total_clicks 
               FROM users 
               ORDER BY coins DESC 
               LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def get_leaderboard_total(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT user_id, username, first_name, total_clicks, coins, level 
               FROM users 
               ORDER BY total_clicks DESC 
               LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def get_user_rank_current(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE coins > (SELECT coins FROM users WHERE user_id = ?)",
            (user_id,)
        ) as cursor:
            rank = await cursor.fetchone()
            return rank[0] if rank else None

async def get_user_rank_total(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE total_clicks > (SELECT total_clicks FROM users WHERE user_id = ?)",
            (user_id,)
        ) as cursor:
            rank = await cursor.fetchone()
            return rank[0] if rank else None

# ==================== ADMIN FUNCTIONS ====================

async def search_users(query, limit=20):
    """Foydalanuvchilarni username yoki first_name bo'yicha qidirish"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT user_id, username, first_name, last_name, coins, level, total_clicks 
               FROM users 
               WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?
               ORDER BY coins DESC 
               LIMIT ?""",
            (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit)
        ) as cursor:
            return await cursor.fetchall()

async def get_all_users(limit=50, offset=0):
    """Barcha foydalanuvchilarni olish (pagination bilan)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT user_id, username, first_name, last_name, coins, level, total_clicks, diamonds 
               FROM users 
               ORDER BY coins DESC 
               LIMIT ? OFFSET ?""",
            (limit, offset)
        ) as cursor:
            return await cursor.fetchall()

async def get_total_users_count():
    """Jami foydalanuvchilar soni"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            count = await cursor.fetchone()
            return count[0] if count else 0

async def admin_add_coins(user_id, amount):
    """Admin tomonidan tanga qo'shish"""
    await update_user_stats(user_id, coins_delta=amount)

async def admin_add_exp(user_id, amount):
    """Admin tomonidan EXP qo'shish"""
    await update_user_stats(user_id, exp_delta=amount)

async def admin_add_energy(user_id, amount):
    """Admin tomonidan energiya qo'shish"""
    await update_user_stats(user_id, energy_delta=amount)
