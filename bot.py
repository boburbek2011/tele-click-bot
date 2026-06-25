import sys
import os
# Bu qatorlar pydantic bilan bog'liq muammolarni oldini oladi
os.environ["PYTHONHASHSEED"] = "0"
os.environ["PYTHONIOENCODING"] = "utf-8"

import asyncio
import logging
import json
from datetime import datetime, timedelta
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import BOT_TOKEN, ADMIN_IDS, WEBAPP_URL, DB_PATH
from database import init_db, get_user, create_user, update_user_stats, get_top_users

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Web App server routes
routes = web.RouteTableDef()

# WebSocket clients
ws_clients = set()

@routes.get('/')
async def index(request):
    return web.FileResponse('web_app/index.html')

@routes.get('/style.css')
async def style(request):
    return web.FileResponse('web_app/style.css')

@routes.get('/script.js')
async def script(request):
    return web.FileResponse('web_app/script.js')

@routes.post('/api/user')
async def get_user_data(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        user = await get_user(user_id)
        if user:
            return web.json_response({
                'user_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'coins': user[4],
                'exp': user[5],
                'level': user[6],
                'diamonds': user[7],
                'title': user[8],
                'color': user[9],
                'total_clicks': user[10]
            })
        return web.json_response({'error': 'User not found'}, status=404)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/click')
async def handle_click(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        # Update user stats
        await update_user_stats(user_id, coins_delta=1, exp_delta=1, clicks_delta=1)
        
        user = await get_user(user_id)
        if not user:
            return web.json_response({'error': 'User not found'}, status=404)
        
        # Check level up
        level = user[6]
        exp = user[5]
        leveled_up = False
        
        # Level up logic
        while exp >= level * 100:
            exp -= level * 100
            level += 1
            leveled_up = True
        
        if leveled_up:
            await update_user_stats(user_id, level_update=level)
        
        return web.json_response({
            'success': True,
            'coins': user[4] + 1,
            'exp': user[5] + 1,
            'level': level
        })
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/title')
async def change_title(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        title = data.get('title')
        
        if not user_id or not title:
            return web.json_response({'error': 'Missing data'}, status=400)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET title = ? WHERE user_id = ?",
                (title, user_id)
            )
            await db.commit()
        
        return web.json_response({
            'success': True,
            'title': title
        })
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/diamond')
async def buy_diamond(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        user = await get_user(user_id)
        if not user or user[4] < 1500000:
            return web.json_response({'error': 'Not enough coins'}, status=400)
        
        await update_user_stats(user_id, coins_delta=-1500000)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET diamonds = diamonds + 1 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
        
        updated_user = await get_user(user_id)
        return web.json_response({
            'success': True,
            'coins': updated_user[4],
            'diamonds': updated_user[7]
        })
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/send')
async def send_coins(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        target_id = data.get('target')
        amount = data.get('amount')
        
        if not all([user_id, target_id, amount]):
            return web.json_response({'error': 'Missing data'}, status=400)
        
        user = await get_user(user_id)
        if not user or user[4] < amount:
            return web.json_response({'error': 'Not enough coins'}, status=400)
        
        target = await get_user(target_id)
        if not target:
            return web.json_response({'error': 'Target user not found'}, status=404)
        
        await update_user_stats(user_id, coins_delta=-amount)
        await update_user_stats(target_id, coins_delta=amount)
        
        updated_user = await get_user(user_id)
        return web.json_response({
            'success': True,
            'coins': updated_user[4]
        })
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/promo')
async def redeem_promo(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        code = data.get('code')
        
        if not user_id or not code:
            return web.json_response({'error': 'Missing data'}, status=400)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Check promo code
            async with db.execute(
                "SELECT * FROM promo_codes WHERE code = ? AND expires_at > datetime('now')",
                (code.upper(),)
            ) as cursor:
                promo = await cursor.fetchone()
            
            if not promo:
                return web.json_response({'error': 'Invalid or expired promo code'}, status=400)
            
            # Check if already used
            async with db.execute(
                "SELECT * FROM promo_usage WHERE user_id = ? AND promo_id = ?",
                (user_id, promo[0])
            ) as cursor:
                used = await cursor.fetchone()
            
            if used:
                return web.json_response({'error': 'Promo code already used'}, status=400)
            
            # Apply promo
            added_coins = promo[2]
            added_exp = promo[3]
            
            await update_user_stats(user_id, coins_delta=added_coins, exp_delta=added_exp)
            
            # Mark as used
            await db.execute(
                "INSERT INTO promo_usage (user_id, promo_id) VALUES (?, ?)",
                (user_id, promo[0])
            )
            await db.commit()
        
        updated_user = await get_user(user_id)
        return web.json_response({
            'success': True,
            'coins': updated_user[4],
            'exp': updated_user[5],
            'added_coins': added_coins,
            'added_exp': added_exp
        })
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/auction/create')
async def create_auction(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        name = data.get('name')
        desc = data.get('desc')
        price = data.get('price')
        duration = data.get('duration')
        
        if not all([user_id, name, desc, price, duration]):
            return web.json_response({'error': 'Missing data'}, status=400)
        
        end_time = datetime.now() + timedelta(minutes=duration)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO auctions 
                   (creator_id, item_name, item_description, start_price, current_bid, end_time) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, name, desc, price, price, end_time.isoformat())
            )
            await db.commit()
        
        return web.json_response({'success': True})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/auction/bid')
async def place_bid(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        auction_id = data.get('auction_id')
        amount = data.get('amount')
        
        if not all([user_id, auction_id, amount]):
            return web.json_response({'error': 'Missing data'}, status=400)
        
        user = await get_user(user_id)
        if not user or user[4] < amount:
            return web.json_response({'error': 'Not enough coins'}, status=400)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Get auction
            async with db.execute(
                "SELECT * FROM auctions WHERE id = ? AND is_active = 1 AND end_time > datetime('now')",
                (auction_id,)
            ) as cursor:
                auction = await cursor.fetchone()
            
            if not auction:
                return web.json_response({'error': 'Auction not found or ended'}, status=404)
            
            if amount <= auction[5]:
                return web.json_response({'error': f'Bid must be higher than {auction[5]}'}, status=400)
            
            # Update bid
            await db.execute(
                "UPDATE auctions SET current_bid = ?, current_bidder_id = ? WHERE id = ?",
                (amount, user_id, auction_id)
            )
            
            # Record bid
            await db.execute(
                "INSERT INTO auction_bids (auction_id, user_id, bid_amount) VALUES (?, ?, ?)",
                (auction_id, user_id, amount)
            )
            await db.commit()
        
        await update_user_stats(user_id, coins_delta=-amount)
        updated_user = await get_user(user_id)
        
        return web.json_response({
            'success': True,
            'coins': updated_user[4]
        })
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.get('/api/auctions')
async def list_auctions(request):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                """SELECT a.*, u.username, u.first_name 
                   FROM auctions a 
                   LEFT JOIN users u ON a.creator_id = u.user_id 
                   WHERE a.is_active = 1 AND a.end_time > datetime('now')
                   ORDER BY a.created_at DESC LIMIT 20"""
            ) as cursor:
                auctions = await cursor.fetchall()
        
        result = []
        for auction in auctions:
            result.append({
                'id': auction[0],
                'creator_id': auction[1],
                'creator_name': auction[11] or auction[12] or str(auction[1]),
                'item_name': auction[2],
                'item_description': auction[3],
                'start_price': auction[4],
                'current_bid': auction[5],
                'current_bidder_id': auction[6],
                'end_time': auction[7]
            })
        
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

# WebSocket handler
@routes.get('/ws')
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    user_id = None
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    
                    if data.get('type') == 'auth':
                        user_id = data.get('user_id')
                        ws_clients.add(ws)
                        
                    elif data.get('type') == 'chat' and user_id:
                        # Get user info
                        user = await get_user(user_id)
                        if user:
                            chat_msg = {
                                'type': 'chat',
                                'user_id': user_id,
                                'username': user[1],
                                'first_name': user[2],
                                'title': user[8],
                                'color': user[9],
                                'message': data.get('message', '')[:500],
                                'time': datetime.now().isoformat()
                            }
                            
                            # Broadcast to all clients
                            for client in list(ws_clients):
                                if not client.closed:
                                    try:
                                        await client.send_json(chat_msg)
                                    except:
                                        pass
                            
                            # Store in database
                            async with aiosqlite.connect(DB_PATH) as db:
                                await db.execute(
                                    "INSERT INTO chat_messages (user_id, message) VALUES (?, ?)",
                                    (user_id, chat_msg['message'])
                                )
                                await db.commit()
                                
                except json.JSONDecodeError:
                    pass
                    
            elif msg.type == web.WSMsgType.ERROR:
                break
                
    finally:
        if ws in ws_clients:
            ws_clients.remove(ws)
    
    return ws

# Bot handlers
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    await create_user(user_id, username, first_name, last_name)
    
    web_app = WebAppInfo(url=f"{WEBAPP_URL}?user_id={user_id}")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 O'yinni ochish", web_app=web_app)]
        ]
    )
    
    await message.answer(
        "🎮 **Tele Click Bot**\n\n"
        "Salom! Bu o'yin orqali siz tanga yig'ib, darajangizni oshirishingiz mumkin.\n\n"
        "📊 **Xususiyatlar:**\n"
        "🪙 Tanga yig'ish\n"
        "⭐ EXP va daraja oshirish\n"
        "💬 Global chat\n"
        "🔨 Auktsionlar\n"
        "💎 Olmoslar\n"
        "🎁 Promokodlar\n\n"
        "🔽 Quyidagi tugmani bosing va o'yinni boshlang!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    
    level = user[6]
    exp = user[5]
    next_exp = level * 100
    
    progress = int((exp / next_exp) * 100) if next_exp > 0 else 0
    
    profile_text = (
        f"👤 **Profil**\n\n"
        f"🆔 ID: `{user[0]}`\n"
        f"👤 Ism: {user[2]}\n"
        f"📛 Username: @{user[1] or 'Mavjud emas'}\n"
        f"🏷️ Unvon: {user[8]}\n\n"
        f"🪙 Tangalar: `{user[4]}`\n"
        f"⭐ EXP: `{user[5]}`\n"
        f"📊 Daraja: `{user[6]}`\n"
        f"📈 Progress: `{progress}%`\n"
        f"💎 Olmoslar: `{user[7]}`\n"
        f"🖱️ Jami bosishlar: `{user[10]}`"
    )
    
    await message.answer(profile_text, parse_mode="Markdown")

@dp.message(Command("admin"))
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

@dp.message(Command("add_coins"))
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

@dp.message(Command("add_exp"))
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

@dp.message(Command("add_admin"))
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

@dp.message(Command("remove_admin"))
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

@dp.message(Command("list_users"))
async def list_users_admin(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
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

@dp.message(Command("create_promo"))
async def create_promo(message: types.Message):
    user_id = message.from_user.id
    
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
    import random
    import string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    expires_at = datetime.now() + timedelta(days=days)
    
    async with aiosqlite.connect(DB_PATH) as db:
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

async def main():
    # Initialize database
    await init_db()
    
    # Create web_app directory if not exists
    import os
    if not os.path.exists('web_app'):
        os.makedirs('web_app')
    
    # Start Web App server
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logging.info("Web App server started on port 8080")
    
    # Start bot
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
