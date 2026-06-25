import sys
import os
os.environ["PYTHONHASHSEED"] = "0"
os.environ["PYTHONIOENCODING"] = "utf-8"

import asyncio
import logging
import json
import random
from datetime import datetime, timedelta
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import BOT_TOKEN, ADMIN_IDS, WEBAPP_URL, DB_PATH
from database import (
    init_db, get_user, create_user, update_user_stats, 
    refill_energy, get_shop_items, get_skins, get_user_skins, 
    purchase_item, get_required_exp, get_user_total_multiplier
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Web App server routes
routes = web.RouteTableDef()
ws_clients = set()

# ==================== WEB APP ROUTES ====================

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
        
        user = await get_user(int(user_id))
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
                'total_clicks': user[10],
                'energy': user[11],
                'max_energy': user[12],
                'click_power': user[13],
                'offline_mining': user[14],
                'mining_rate': user[15],
                'auto_clicker_level': user[17],
                'active_skin_id': user[18],
                'multiplier': user[19]
            })
        return web.json_response({'error': 'User not found'}, status=404)
    except Exception as e:
        logging.error(f"Error in /api/user: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/click')
async def handle_click(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        user = await get_user(int(user_id))
        if not user:
            return web.json_response({'error': 'User not found'}, status=404)
        
        # Energiyani to'ldirish
        await refill_energy(int(user_id))
        user = await get_user(int(user_id))
        
        # Energiyani tekshirish
        if user[11] <= 0:
            return web.json_response({
                'success': False,
                'error': 'Energiya tugadi! Kuting yoki shopdan sotib oling.'
            }, status=400)
        
        # Click power
        click_power = user[13] or 1
        
        # Total multiplier
        total_multiplier = await get_user_total_multiplier(int(user_id))
        
        # EXP (10-20 oralig'ida)
        exp_gain = random.randint(10, 20)
        
        # Coins: click_power * multiplier
        coins_gain = click_power * total_multiplier
        
        # Energiyani kamaytirish
        await update_user_stats(
            int(user_id), 
            coins_delta=coins_gain, 
            exp_delta=exp_gain, 
            clicks_delta=1,
            energy_delta=-1
        )
        
        # Level up tekshirish
        user = await get_user(int(user_id))
        level = user[6]
        exp = user[5]
        required_exp = await get_required_exp(level)
        
        leveled_up = False
        while exp >= required_exp:
            exp -= required_exp
            level += 1
            required_exp = await get_required_exp(level)
            leveled_up = True
        
        if leveled_up:
            await update_user_stats(int(user_id), level_update=level)
            # Level up notification (Telegramga)
            try:
                await bot.send_message(
                    int(user_id),
                    f"🎉 **DARAJANGIZ OSHDI!**\n\n"
                    f"📊 Yangi daraja: **{level}**\n"
                    f"⭐ EXP: {exp}\n"
                    f"🪙 Tangalar: {user[4] + coins_gain}",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        updated_user = await get_user(int(user_id))
        
        return web.json_response({
            'success': True,
            'coins': updated_user[4],
            'exp': updated_user[5],
            'level': updated_user[6],
            'energy': updated_user[11],
            'max_energy': updated_user[12],
            'click_power': click_power,
            'multiplier': total_multiplier,
            'coins_gained': coins_gain,
            'exp_gained': exp_gain,
            'leveled_up': leveled_up
        })
    except Exception as e:
        logging.error(f"Error in /api/click: {e}")
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
                (title, int(user_id))
            )
            await db.commit()
        
        return web.json_response({
            'success': True,
            'title': title
        })
    except Exception as e:
        logging.error(f"Error in /api/title: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/diamond')
async def buy_diamond(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        user = await get_user(int(user_id))
        if not user or user[4] < 1500000:
            return web.json_response({'error': 'Not enough coins'}, status=400)
        
        await update_user_stats(int(user_id), coins_delta=-1500000)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET diamonds = diamonds + 1 WHERE user_id = ?",
                (int(user_id),)
            )
            await db.commit()
        
        updated_user = await get_user(int(user_id))
        return web.json_response({
            'success': True,
            'coins': updated_user[4],
            'diamonds': updated_user[7]
        })
    except Exception as e:
        logging.error(f"Error in /api/diamond: {e}")
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
        
        user = await get_user(int(user_id))
        if not user or user[4] < amount:
            return web.json_response({'error': 'Not enough coins'}, status=400)
        
        target = await get_user(int(target_id))
        if not target:
            return web.json_response({'error': 'Target user not found'}, status=404)
        
        await update_user_stats(int(user_id), coins_delta=-amount)
        await update_user_stats(int(target_id), coins_delta=amount)
        
        updated_user = await get_user(int(user_id))
        return web.json_response({
            'success': True,
            'coins': updated_user[4]
        })
    except Exception as e:
        logging.error(f"Error in /api/send: {e}")
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
            async with db.execute(
                "SELECT * FROM promo_codes WHERE code = ? AND expires_at > datetime('now')",
                (code.upper(),)
            ) as cursor:
                promo = await cursor.fetchone()
            
            if not promo:
                return web.json_response({'error': 'Invalid or expired promo code'}, status=400)
            
            async with db.execute(
                "SELECT * FROM promo_usage WHERE user_id = ? AND promo_id = ?",
                (int(user_id), promo[0])
            ) as cursor:
                used = await cursor.fetchone()
            
            if used:
                return web.json_response({'error': 'Promo code already used'}, status=400)
            
            added_coins = promo[2]
            added_exp = promo[3]
            
            await update_user_stats(int(user_id), coins_delta=added_coins, exp_delta=added_exp)
            
            await db.execute(
                "INSERT INTO promo_usage (user_id, promo_id) VALUES (?, ?)",
                (int(user_id), promo[0])
            )
            await db.commit()
        
        updated_user = await get_user(int(user_id))
        return web.json_response({
            'success': True,
            'coins': updated_user[4],
            'exp': updated_user[5],
            'added_coins': added_coins,
            'added_exp': added_exp
        })
    except Exception as e:
        logging.error(f"Error in /api/promo: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ==================== SHOP API ====================

@routes.get('/api/shop/items')
async def get_shop_items_api(request):
    try:
        items = await get_shop_items()
        result = []
        for item in items:
            result.append({
                'id': item[0],
                'name': item[1],
                'description': item[2],
                'category': item[3],
                'price': item[4],
                'level_required': item[5],
                'effect_type': item[6],
                'effect_value': item[7],
                'emoji': item[8]
            })
        return web.json_response(result)
    except Exception as e:
        logging.error(f"Error in /api/shop/items: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/shop/buy')
async def buy_shop_item(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        item_id = data.get('item_id')
        
        if not user_id or not item_id:
            return web.json_response({'error': 'Missing data'}, status=400)
        
        user = await get_user(int(user_id))
        if not user:
            return web.json_response({'error': 'User not found'}, status=404)
        
        # Get item
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM shop_items WHERE id = ? AND is_available = 1",
                (int(item_id),)
            ) as cursor:
                item = await cursor.fetchone()
        
        if not item:
            return web.json_response({'error': 'Item not found'}, status=404)
        
        # Check level requirement
        if user[6] < item[4]:
            return web.json_response({
                'error': f'Bu narsa uchun {item[4]}-daraja kerak! Sizda: {user[6]}'
            }, status=400)
        
        # Check price
        if user[4] < item[3]:
            return web.json_response({
                'error': f'Yetarli tanga yo\'q! Kerak: {item[3]}, Sizda: {user[4]}'
            }, status=400)
        
        # Apply effect
        effect_type = item[5]
        effect_value = item[6]
        
        if effect_type == 'max_energy':
            await update_user_stats(int(user_id), max_energy_delta=effect_value, coins_delta=-item[3])
        elif effect_type == 'click_power':
            await update_user_stats(int(user_id), click_power_delta=effect_value, coins_delta=-item[3])
        elif effect_type == 'auto_clicker':
            await update_user_stats(int(user_id), auto_clicker_delta=effect_value, coins_delta=-item[3])
        elif effect_type == 'offline_mining':
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET offline_mining = 1, mining_rate = mining_rate + ? WHERE user_id = ?",
                    (effect_value, int(user_id))
                )
                await db.commit()
            await update_user_stats(int(user_id), coins_delta=-item[3])
        elif effect_type == 'multiplier':
            end_time = datetime.now() + timedelta(minutes=30)
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET multiplier = ?, multiplier_end_time = ? WHERE user_id = ?",
                    (effect_value, end_time.isoformat(), int(user_id))
                )
                await db.commit()
            await update_user_stats(int(user_id), coins_delta=-item[3])
        
        # Add to inventory
        await purchase_item(int(user_id), int(item_id))
        
        updated_user = await get_user(int(user_id))
        
        return web.json_response({
            'success': True,
            'coins': updated_user[4],
            'max_energy': updated_user[12],
            'click_power': updated_user[13],
            'auto_clicker_level': updated_user[17],
            'message': f'✅ {item[1]} sotib olindi!'
        })
    except Exception as e:
        logging.error(f"Error in /api/shop/buy: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ==================== SKINS API ====================

@routes.get('/api/skins')
async def get_skins_api(request):
    try:
        skins = await get_skins()
        result = []
        for skin in skins:
            result.append({
                'id': skin[0],
                'name': skin[1],
                'emoji': skin[2],
                'rarity': skin[3],
                'level_required': skin[4],
                'price': skin[5],
                'multiplier': skin[6]
            })
        return web.json_response(result)
    except Exception as e:
        logging.error(f"Error in /api/skins: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/skin/buy')
async def buy_skin(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        skin_id = data.get('skin_id')
        
        if not user_id or not skin_id:
            return web.json_response({'error': 'Missing data'}, status=400)
        
        user = await get_user(int(user_id))
        if not user:
            return web.json_response({'error': 'User not found'}, status=404)
        
        # Get skin
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM skins WHERE id = ? AND is_available = 1",
                (int(skin_id),)
            ) as cursor:
                skin = await cursor.fetchone()
        
        if not skin:
            return web.json_response({'error': 'Skin not found'}, status=404)
        
        # Check level requirement
        if user[6] < skin[3]:
            return web.json_response({
                'error': f'Bu skin uchun {skin[3]}-daraja kerak! Sizda: {user[6]}'
            }, status=400)
        
        # Check price
        if user[4] < skin[4]:
            return web.json_response({
                'error': f'Yetarli tanga yo\'q! Kerak: {skin[4]}, Sizda: {user[4]}'
            }, status=400)
        
        # Check if already has skin
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM user_skins WHERE user_id = ? AND skin_id = ?",
                (int(user_id), int(skin_id))
            ) as cursor:
                existing = await cursor.fetchone()
        
        if existing:
            return web.json_response({'error': 'Sizda bu skin allaqachon bor!'}, status=400)
        
        # Purchase skin
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO user_skins (user_id, skin_id) VALUES (?, ?)",
                (int(user_id), int(skin_id))
            )
            await db.commit()
        
        await update_user_stats(int(user_id), coins_delta=-skin[4])
        
        updated_user = await get_user(int(user_id))
        
        return web.json_response({
            'success': True,
            'coins': updated_user[4],
            'message': f'✅ {skin[1]} skin sotib olindi!'
        })
    except Exception as e:
        logging.error(f"Error in /api/skin/buy: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/skin/activate')
async def activate_skin(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        skin_id = data.get('skin_id')
        
        if not user_id or not skin_id:
            return web.json_response({'error': 'Missing data'}, status=400)
        
        # Check if has skin
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM user_skins WHERE user_id = ? AND skin_id = ?",
                (int(user_id), int(skin_id))
            ) as cursor:
                skin = await cursor.fetchone()
        
        if not skin:
            return web.json_response({'error': 'Sizda bu skin yo\'q!'}, status=400)
        
        # Deactivate all skins
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE user_skins SET is_active = 0 WHERE user_id = ?",
                (int(user_id),)
            )
            
            # Activate selected skin
            await db.execute(
                "UPDATE user_skins SET is_active = 1 WHERE user_id = ? AND skin_id = ?",
                (int(user_id), int(skin_id))
            )
            
            # Update user's active skin
            await db.execute(
                "UPDATE users SET active_skin_id = ? WHERE user_id = ?",
                (int(skin_id), int(user_id))
            )
            await db.commit()
        
        return web.json_response({
            'success': True,
            'message': '✅ Skin faollashtirildi!'
        })
    except Exception as e:
        logging.error(f"Error in /api/skin/activate: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.get('/api/user/skins')
async def get_user_skins_api(request):
    try:
        user_id = request.query.get('user_id')
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        skins = await get_user_skins(int(user_id))
        result = []
        for skin in skins:
            result.append({
                'skin_id': skin[0],
                'is_active': skin[1]
            })
        return web.json_response(result)
    except Exception as e:
        logging.error(f"Error in /api/user/skins: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ==================== AUCTION API ====================

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
        
        end_time = datetime.now() + timedelta(minutes=int(duration))
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO auctions 
                   (creator_id, item_name, item_description, start_price, current_bid, end_time) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (int(user_id), name, desc, int(price), int(price), end_time.isoformat())
            )
            await db.commit()
        
        return web.json_response({'success': True})
    except Exception as e:
        logging.error(f"Error in /api/auction/create: {e}")
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
        
        user = await get_user(int(user_id))
        if not user or user[4] < amount:
            return web.json_response({'error': 'Not enough coins'}, status=400)
        
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM auctions WHERE id = ? AND is_active = 1 AND end_time > datetime('now')",
                (int(auction_id),)
            ) as cursor:
                auction = await cursor.fetchone()
            
            if not auction:
                return web.json_response({'error': 'Auction not found or ended'}, status=404)
            
            if amount <= auction[5]:
                return web.json_response({'error': f'Bid must be higher than {auction[5]}'}, status=400)
            
            await db.execute(
                "UPDATE auctions SET current_bid = ?, current_bidder_id = ? WHERE id = ?",
                (amount, int(user_id), int(auction_id))
            )
            
            await db.execute(
                "INSERT INTO auction_bids (auction_id, user_id, bid_amount) VALUES (?, ?, ?)",
                (int(auction_id), int(user_id), amount)
            )
            await db.commit()
        
        await update_user_stats(int(user_id), coins_delta=-amount)
        updated_user = await get_user(int(user_id))
        
        return web.json_response({
            'success': True,
            'coins': updated_user[4]
        })
    except Exception as e:
        logging.error(f"Error in /api/auction/bid: {e}")
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
        logging.error(f"Error in /api/auctions: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ==================== WEBSOCKET ====================

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
                        user = await get_user(int(user_id))
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
                            
                            for client in list(ws_clients):
                                if not client.closed:
                                    try:
                                        await client.send_json(chat_msg)
                                    except:
                                        pass
                            
                            async with aiosqlite.connect(DB_PATH) as db:
                                await db.execute(
                                    "INSERT INTO chat_messages (user_id, message) VALUES (?, ?)",
                                    (int(user_id), chat_msg['message'])
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

# ==================== BOT COMMANDS ====================

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    await create_user(user_id, username, first_name, last_name)
    
    web_app = WebAppInfo(url=f"{WEBAPP_URL}?user_id={user_id}")
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="🚀 O'yinni ochish", web_app=web_app)]
    ]
    
    if user_id in ADMIN_IDS:
        keyboard_buttons.append([InlineKeyboardButton(text="👑 Admin panel", callback_data="admin_panel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(
        "🎮 **Tele Click Bot**\n\n"
        "Salom! Bu o'yin orqali siz tanga yig'ib, darajangizni oshirishingiz mumkin.\n\n"
        "📊 **Xususiyatlar:**\n"
        "🪙 Tanga yig'ish\n"
        "⭐ EXP va daraja oshirish\n"
        "⚡ Energiya tizimi\n"
        "💬 Global chat\n"
        "🔨 Auktsionlar\n"
        "💎 Olmoslar\n"
        "🎁 Promokodlar\n"
        "🏪 Do'kon\n"
        "🎨 Skinlar\n\n"
        "🔽 Quyidagi tugmani bosing va o'yinni boshlang!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await callback_query.answer("❌ Bu faqat adminlar uchun!", show_alert=True)
        return
    
    await callback_query.message.answer(
        "👑 **Admin panel**\n\n"
        "🪙 /add_coins [user_id] [miqdor] - Tanga qo'shish\n"
        "⭐ /add_exp [user_id] [miqdor] - EXP qo'shish\n"
        "👤 /add_admin [user_id] - Admin qo'shish\n"
        "❌ /remove_admin [user_id] - Admin o'chirish\n"
        "📋 /list_users - Foydalanuvchilar ro'yxati\n"
        "🎁 /create_promo [tanga] [exp] [kun] - Promokod yaratish\n"
        "⚡ /add_energy [user_id] [miqdor] - Energiya qo'shish",
        parse_mode="Markdown"
    )
    await callback_query.answer()

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
        "🎁 /create_promo [tanga] [exp] [kun] - Promokod yaratish\n"
        "⚡ /add_energy [user_id] [miqdor] - Energiya qo'shish",
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

@dp.message(Command("add_energy"))
async def add_energy_admin(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Ishlatish: /add_energy [user_id] [miqdor]")
        return
    
    target_id = int(args[1])
    amount = int(args[2])
    
    await update_user_stats(target_id, energy_delta=amount)
    await message.answer(f"✅ {target_id} ga {amount} energiya qo'shildi!")

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

# ==================== MAIN ====================

async def main():
    # Initialize database
    await init_db()
    
    # Create web_app directory if not exists
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
