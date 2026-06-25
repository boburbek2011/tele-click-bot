from aiogram import types
from aiogram.filters import Command
from database import get_user, update_user_stats
import aiosqlite
from config import ADMIN_IDS

async def add_coins_admin(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Ishlatish: /add_coins [user_id] [miqdor]")
        return
    
    target_id = int(args[1])
    amount = int(args[2])
    
    await update_user_stats(target_id, coins_delta=amount)
    await message.answer(f"✅ {target_id} ga {amount} tanga qo'shildi!")

async def add_exp_admin(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Ishlatish: /add_exp [user_id] [miqdor]")
        return
    
    target_id = int(args[1])
    amount = int(args[2])
    
    await update_user_stats(target_id, exp_delta=amount)
    await message.answer(f"✅ {target_id} ga {amount} EXP qo'shildi!")

async def add_admin(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Ishlatish: /add_admin [user_id]")
        return
    
    new_admin = int(args[1])
    if new_admin not in ADMIN_IDS:
        ADMIN_IDS.append(new_admin)
        await message.answer(f"✅ {new_admin} admin qo'shildi!")
    else:
        await message.answer(f"❌ {new_admin} allaqachon admin!")

async def remove_admin(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Ishlatish: /remove_admin [user_id]")
        return
    
    remove_id = int(args[1])
    if remove_id in ADMIN_IDS and remove_id != user_id:
        ADMIN_IDS.remove(remove_id)
        await message.answer(f"✅ {remove_id} admin o'chirildi!")
    else:
        await message.answer(f"❌ {remove_id} admin emas yoki o'zingizni o'chira olmaysiz!")

async def list_users_admin(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    async with aiosqlite.connect("tele_click.db") as db:
        async with db.execute(
            "SELECT user_id, username, first_name, coins, level FROM users ORDER BY coins DESC LIMIT 20"
        ) as cursor:
            users = await cursor.fetchall()
    
    if not users:
        await message.answer("❌ Foydalanuvchilar topilmadi!")
        return
    
    text = "👥 **Foydalanuvchilar ro'yxati:**\n\n"
    for i, (uid, username, first_name, coins, level) in enumerate(users, 1):
        name = username or first_name or str(uid)
        text += f"{i}. {name} - 🪙{coins} - 📊{level}\n"
    
    await message.answer(text, parse_mode="Markdown")

async def admin_panel(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    await message.answer(
        "👑 **Admin panel**\n\n"
        "🪙 /add_coins [user_id] [miqdor] - Tanga qo'shish\n"
        "⭐ /add_exp [user_id] [miqdor] - EXP qo'shish\n"
        "👤 /add_admin [user_id] - Admin qo'shish\n"
        "❌ /remove_admin [user_id] - Admin o'chirish\n"
        "📋 /list_users - Foydalanuvchilar ro'yxati\n"
        "🎁 /create_promo [tanga] [exp] [kun] - Promokod yaratish",
        parse_mode="Markdown"
    )