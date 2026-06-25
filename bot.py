import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import aiohttp
from aiohttp import web
import json
from datetime import datetime, timedelta
import sqlite3

from config import BOT_TOKEN, ADMIN_IDS, WEBAPP_URL
from database import init_db, get_user, create_user, update_user_stats
from handlers import start, profile, clicker, chat, auction, promo, admin

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Web App server
routes = web.RouteTableDef()

@routes.get('/')
async def index(request):
    return web.FileResponse('web_app/index.html')

@routes.get('/style.css')
async def style(request):
    return web.FileResponse('web_app/style.css')

@routes.get('/script.js')
async def script(request):
    return web.FileResponse('web_app/script.js')

@routes.get('/api/user')
async def get_user_data(request):
    # Get user from Telegram WebApp data
    data = await request.json()
    user_id = data.get('user_id')
    if not user_id:
        return web.json_response({'error': 'No user_id'}, status=400)
    
    user = await get_user(user_id)
    if user:
        return web.json_response({
            'coins': user[3],
            'exp': user[4],
            'level': user[5],
            'diamonds': user[6],
            'title': user[7],
            'color': user[8],
            'total_clicks': user[9],
            'username': user[1],
            'first_name': user[2]
        })
    return web.json_response({'error': 'User not found'}, status=404)

@routes.post('/api/click')
async def handle_click(request):
    data = await request.json()
    user_id = data.get('user_id')
    
    # Update user stats
    await update_user_stats(user_id, coins_delta=1, exp_delta=1, clicks_delta=1)
    
    user = await get_user(user_id)
    if user:
        # Check level up
        level = user[5]
        exp = user[4]
        # Simple level up logic
        while True:
            next_exp = level * 100  # Oddiy formula, siz o'zingiz xohlagancha
            if exp >= next_exp:
                level += 1
                exp -= next_exp
            else:
                break
        
        # Update level if changed
        if level != user[5]:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET level = ?, exp = ? WHERE user_id = ?",
                    (level, exp, user_id)
                )
                await db.commit()
        
        return web.json_response({
            'success': True,
            'coins': user[3] + 1,
            'exp': user[4] + 1,
            'level': level
        })
    
    return web.json_response({'success': False}, status=404)

# Bot handlers
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    await create_user(user_id, username, first_name, last_name)
    
    # Create WebApp button
    web_app = WebAppInfo(url=f"{WEBAPP_URL}?user_id={user_id}")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 O'yinni ochish", web_app=web_app)]
        ]
    )
    
    await message.answer(
        "🎮 **Tele Click Bot**\n\n"
        "Salom! Bu o'yin orqali siz tanga yig'ib, darajangizni oshirishingiz mumkin.\n"
        "🔽 Quyidagi tugmani bosing va o'yinni boshlang!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Admin commands
@dp.message(Command("add_coins"))
async def add_coins_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Ishlatish: /add_coins [user_id] [miqdor]")
        return
    
    target_id = int(args[1])
    amount = int(args[2])
    
    await update_user_stats(target_id, coins_delta=amount)
    await message.answer(f"✅ {target_id} ga {amount} tanga qo'shildi!")

@dp.message(Command("add_admin"))
async def add_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Ishlatish: /add_admin [user_id]")
        return
    
    new_admin = int(args[1])
    ADMIN_IDS.append(new_admin)
    await message.answer(f"✅ {new_admin} admin qo'shildi!")

async def main():
    # Initialize database
    await init_db()
    
    # Start Web App server
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    # Start bot
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())