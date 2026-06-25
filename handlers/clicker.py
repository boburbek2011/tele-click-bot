from aiogram import types
from aiogram.filters import Command
from database import get_user, update_user_stats
import aiosqlite

async def click_command(message: types.Message):
    user_id = message.from_user.id
    
    # Add coins and exp
    await update_user_stats(user_id, coins_delta=1, exp_delta=1, clicks_delta=1)
    
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Xatolik yuz berdi!")
        return
    
    # Check level up
    level = user[5]
    exp = user[4]
    leveled_up = False
    
    while exp >= level * 100:
        exp -= level * 100
        level += 1
        leveled_up = True
    
    if leveled_up:
        async with aiosqlite.connect("tele_click.db") as db:
            await db.execute(
                "UPDATE users SET level = ?, exp = ? WHERE user_id = ?",
                (level, exp, user_id)
            )
            await db.commit()
        
        await message.answer(f"🎉 **DARAJANGIZ OSHDI!**\n\n📊 Yangi daraja: **{level}**\n⭐ EXP: {exp}", parse_mode="Markdown")
    
    # Get updated user data
    user = await get_user(user_id)
    
    click_text = (
        f"🪙 **+1 tanga**\n"
        f"⭐ **+1 EXP**\n\n"
        f"📊 Jami tangalar: `{user[3]}`\n"
        f"📈 Daraja: `{user[5]}`\n"
        f"⭐ EXP: `{user[4]}`"
    )
    
    await message.answer(click_text, parse_mode="Markdown")

async def stats_command(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    
    # Top users
    async with aiosqlite.connect("tele_click.db") as db:
        async with db.execute(
            "SELECT user_id, coins, level FROM users ORDER BY coins DESC LIMIT 5"
        ) as cursor:
            top_users = await cursor.fetchall()
    
    top_text = "🏆 **Top 5 o'yinchilar:**\n\n"
    for i, (uid, coins, level) in enumerate(top_users, 1):
        top_text += f"{i}. ID: `{uid}` - 🪙 {coins} - 📊 {level}-daraja\n"
    
    await message.answer(top_text, parse_mode="Markdown")