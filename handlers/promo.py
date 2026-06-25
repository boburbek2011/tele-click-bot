from aiogram import types
from aiogram.filters import Command
from database import get_user, update_user_stats
import aiosqlite
from datetime import datetime
import random
import string

async def promo_command(message: types.Message):
    await message.answer(
        "🎁 **Promokodlar**\n\n"
        "Promokod kiritish: /redeem [kod]\n"
        "Admin uchun: /create_promo [tanga] [exp] [kun]",
        parse_mode="Markdown"
    )

async def create_promo(message: types.Message):
    user_id = message.from_user.id
    
    # Check if admin
    from config import ADMIN_IDS
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    args = message.text.split()
    if len(args) < 4:
        await message.answer("❌ Ishlatish: /create_promo [tanga] [exp] [kun]")
        return
    
    coins = int(args[1])
    exp = int(args[2])
    days = int(args[3])
    
    # Generate random code
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    expires_at = datetime.now() + timedelta(days=days)
    
    async with aiosqlite.connect("tele_click.db") as db:
        await db.execute(
            "INSERT INTO promo_codes (code, coins, exp, expires_at, created_by) VALUES (?, ?, ?, ?, ?)",
            (code, coins, exp, expires_at.isoformat(), user_id)
        )
        await db.commit()
    
    await message.answer(
        f"✅ Promokod yaratildi!\n\n"
        f"📝 Kod: `{code}`\n"
        f"🪙 Tanga: {coins}\n"
        f"⭐ EXP: {exp}\n"
        f"⏰ Tugaydi: {expires_at.strftime('%Y-%m-%d %H:%M')}",
        parse_mode="Markdown"
    )

async def redeem_promo(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer("❌ Ishlatish: /redeem [kod]")
        return
    
    code = args[1].upper()
    
    async with aiosqlite.connect("tele_click.db") as db:
        # Check promo code
        async with db.execute(
            "SELECT * FROM promo_codes WHERE code = ? AND expires_at > datetime('now')",
            (code,)
        ) as cursor:
            promo = await cursor.fetchone()
        
        if not promo:
            await message.answer("❌ Promokod topilmadi yoki muddati o'tgan!")
            return
        
        # Check if already used
        async with db.execute(
            "SELECT * FROM promo_usage WHERE user_id = ? AND promo_id = ?",
            (user_id, promo[0])
        ) as cursor:
            used = await cursor.fetchone()
        
        if used:
            await message.answer("❌ Siz bu promokodni allaqachon ishlatgansiz!")
            return
        
        # Apply promo
        coins = promo[2]
        exp = promo[3]
        
        await update_user_stats(user_id, coins_delta=coins, exp_delta=exp)
        
        # Mark as used
        await db.execute(
            "INSERT INTO promo_usage (user_id, promo_id) VALUES (?, ?)",
            (user_id, promo[0])
        )
        await db.commit()
    
    await message.answer(
        f"🎉 Promokod aktivlashtirildi!\n\n"
        f"🪙 +{coins} tanga\n"
        f"⭐ +{exp} EXP",
        parse_mode="Markdown"
    )