from aiogram import types
from aiogram.filters import Command
from database import get_user, update_user_stats
from config import ADMIN_IDS
import aiosqlite

async def profile_command(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    
    # Get level progress
    level = user[5]
    exp = user[4]
    next_exp = level * 100
    
    progress = int((exp / next_exp) * 100) if next_exp > 0 else 0
    
    profile_text = (
        f"👤 **Profil**\n\n"
        f"🆔 ID: `{user[0]}`\n"
        f"👤 Ism: {user[2]}\n"
        f"📛 Username: @{user[1] or 'Mavjud emas'}\n"
        f"🏷️ Unvon: {user[7]}\n\n"
        f"🪙 Tangalar: `{user[3]}`\n"
        f"⭐ EXP: `{user[4]}`\n"
        f"📊 Daraja: `{user[5]}`\n"
        f"📈 Progress: `{progress}%`\n"
        f"💎 Olmoslar: `{user[6]}`\n"
        f"🖱️ Jami bosishlar: `{user[9]}`\n\n"
        f"📅 Ro'yxatdan o'tgan: {user[10]}"
    )
    
    await message.answer(profile_text, parse_mode="Markdown")

async def change_title(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer("❌ Ishlatish: /title [yangi unvon]")
        return
    
    new_title = args[1]
    
    async with aiosqlite.connect("tele_click.db") as db:
        await db.execute(
            "UPDATE users SET title = ? WHERE user_id = ?",
            (new_title, user_id)
        )
        await db.commit()
    
    await message.answer(f"✅ Unvoningiz o'zgartirildi: {new_title}")

async def send_coins(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer("❌ Ishlatish: /send [user_id] [miqdor]")
        return
    
    target_id = int(args[1])
    amount = int(args[2])
    
    user = await get_user(user_id)
    if not user or user[3] < amount:
        await message.answer("❌ Yetarli tanga yo'q!")
        return
    
    # Check if target exists
    target = await get_user(target_id)
    if not target:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    
    # Transfer coins
    await update_user_stats(user_id, coins_delta=-amount)
    await update_user_stats(target_id, coins_delta=amount)
    
    # Log transaction
    async with aiosqlite.connect("tele_click.db") as db:
        await db.execute(
            "INSERT INTO transactions (from_user, to_user, amount, type, reason) VALUES (?, ?, ?, ?, ?)",
            (user_id, target_id, amount, 'coin', 'transfer')
        )
        await db.commit()
    
    await message.answer(f"✅ {amount} tanga {target_id} ga yuborildi!")

async def buy_diamond(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user or user[3] < 1500000:
        await message.answer("❌ Yetarli tanga yo'q! 1.5 mln tanga kerak.")
        return
    
    await update_user_stats(user_id, coins_delta=-1500000)
    
    async with aiosqlite.connect("tele_click.db") as db:
        await db.execute(
            "UPDATE users SET diamonds = diamonds + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
    
    await message.answer("💎 Olmos sotib olindi! Endi sizda 1 ta olmos bor.")