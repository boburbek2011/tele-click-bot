import sys
import os
os.environ["PYTHONHASHSEED"] = "0"
os.environ["PYTHONIOENCODING"] = "utf-8"

import asyncio
import logging
import json
import random
import string
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
    purchase_item, get_required_exp, get_user_total_multiplier,
    get_leaderboard_current, get_leaderboard_total, get_user_rank_current, get_user_rank_total,
    search_users, get_all_users, get_total_users_count,
    admin_add_coins, admin_add_exp, admin_add_energy
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

# ==================== STATIC FILES ====================

@routes.get('/')
async def index(request):
    return web.FileResponse('web_app/index.html')

@routes.get('/style.css')
async def style(request):
    return web.FileResponse('web_app/style.css')

@routes.get('/script.js')
async def script(request):
    return web.FileResponse('web_app/script.js')

# ==================== USER API ====================

@routes.get('/api/user')
async def get_user_data(request):
    try:
        user_id = request.query.get('user_id')
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
        logging.error(f"Error in /api/user GET: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/user')
async def create_or_get_user(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        user = await get_user(int(user_id))
        if not user:
            await create_user(int(user_id), "", "", "")
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
        logging.error(f"Error in /api/user POST: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ==================== CLICK API ====================

@routes.post('/api/click')
async def handle_click(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        await refill_energy(int(user_id))
        
        user = await get_user(int(user_id))
        if not user:
            return web.json_response({'error': 'User not found'}, status=404)
        
        if user[11] <= 0:
            return web.json_response({
                'success': False,
                'error': 'Energiya tugadi! Kuting yoki shopdan sotib oling.'
            }, status=400)
        
        click_power = user[13] or 1
        total_multiplier = await get_user_total_multiplier(int(user_id))
        exp_gain = random.randint(10, 20)
        coins_gain = click_power * total_multiplier
        
        await update_user_stats(
            int(user_id), 
            coins_delta=coins_gain, 
            exp_delta=exp_gain, 
            clicks_delta=1,
            energy_delta=-1
        )
        
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
            try:
                await bot.send_message(
                    int(user_id),
                    f"🎉 **DARAJANGIZ OSHDI!**\n\n📊 Yangi daraja: **{level}**",
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

# ==================== TITLE API ====================

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

# ==================== DIAMOND API ====================

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

# ==================== SEND COINS API ====================

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

# ==================== PROMO API ====================

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
        
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM shop_items WHERE id = ? AND is_available = 1",
                (int(item_id),)
            ) as cursor:
                item = await cursor.fetchone()
        
        if not item:
            return web.json_response({'error': 'Item not found'}, status=404)
        
        if user[6] < item[4]:
            return web.json_response({
                'error': f'Bu narsa uchun {item[4]}-daraja kerak! Sizda: {user[6]}'
            }, status=400)
        
        if user[4] < item[3]:
            return web.json_response({
                'error': f'Yetarli tanga yo\'q! Kerak: {item[3]}, Sizda: {user[4]}'
            }, status=400)
        
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
        
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM skins WHERE id = ? AND is_available = 1",
                (int(skin_id),)
            ) as cursor:
                skin = await cursor.fetchone()
        
        if not skin:
            return web.json_response({'error': 'Skin not found'}, status=404)
        
        if user[6] < skin[3]:
            return web.json_response({
                'error': f'Bu skin uchun {skin[3]}-daraja kerak! Sizda: {user[6]}'
            }, status=400)
        
        if user[4] < skin[4]:
            return web.json_response({
                'error': f'Yetarli tanga yo\'q! Kerak: {skin[4]}, Sizda: {user[4]}'
            }, status=400)
        
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM user_skins WHERE user_id = ? AND skin_id = ?",
                (int(user_id), int(skin_id))
            ) as cursor:
                existing = await cursor.fetchone()
        
        if existing:
            return web.json_response({'error': 'Sizda bu skin allaqachon bor!'}, status=400)
        
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
        
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM user_skins WHERE user_id = ? AND skin_id = ?",
                (int(user_id), int(skin_id))
            ) as cursor:
                skin = await cursor.fetchone()
        
        if not skin:
            return web.json_response({'error': 'Sizda bu skin yo\'q!'}, status=400)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE user_skins SET is_active = 0 WHERE user_id = ?",
                (int(user_id),)
            )
            await db.execute(
                "UPDATE user_skins SET is_active = 1 WHERE user_id = ? AND skin_id = ?",
                (int(user_id), int(skin_id))
            )
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

# ==================== LEADERBOARD API ====================

@routes.get('/api/leaderboard/current')
async def get_leaderboard_current_api(request):
    try:
        limit = request.query.get('limit', 10)
        try:
            limit = int(limit)
        except:
            limit = 10
        
        leaders = await get_leaderboard_current(limit)
        result = []
        for i, user in enumerate(leaders, 1):
            name = user[1] or user[2] or f"ID:{user[0]}"
            result.append({
                'rank': i,
                'user_id': user[0],
                'name': name,
                'coins': user[3],
                'level': user[4],
                'clicks': user[5]
            })
        return web.json_response(result)
    except Exception as e:
        logging.error(f"Error in /api/leaderboard/current: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.get('/api/leaderboard/total')
async def get_leaderboard_total_api(request):
    try:
        limit = request.query.get('limit', 10)
        try:
            limit = int(limit)
        except:
            limit = 10
        
        leaders = await get_leaderboard_total(limit)
        result = []
        for i, user in enumerate(leaders, 1):
            name = user[1] or user[2] or f"ID:{user[0]}"
            result.append({
                'rank': i,
                'user_id': user[0],
                'name': name,
                'total_clicks': user[3],
                'coins': user[4],
                'level': user[5]
            })
        return web.json_response(result)
    except Exception as e:
        logging.error(f"Error in /api/leaderboard/total: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.get('/api/leaderboard/rank')
async def get_user_rank_api(request):
    try:
        user_id = request.query.get('user_id')
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        current_rank = await get_user_rank_current(int(user_id))
        total_rank = await get_user_rank_total(int(user_id))
        
        return web.json_response({
            'current_rank': current_rank,
            'total_rank': total_rank
        })
    except Exception as e:
        logging.error(f"Error in /api/leaderboard/rank: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ==================== ADMIN API (Web App) ====================

@routes.get('/api/admin/users')
async def admin_get_users(request):
    try:
        user_id = request.query.get('user_id')
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        if int(user_id) not in ADMIN_IDS:
            return web.json_response({'error': 'Unauthorized'}, status=403)
        
        limit = request.query.get('limit', 50)
        offset = request.query.get('offset', 0)
        try:
            limit = int(limit)
            offset = int(offset)
        except:
            limit = 50
            offset = 0
        
        users = await get_all_users(limit, offset)
        total = await get_total_users_count()
        
        result = []
        for user in users:
            result.append({
                'user_id': user[0],
                'username': user[1] or 'No username',
                'first_name': user[2] or 'No name',
                'last_name': user[3] or '',
                'coins': user[4],
                'level': user[5],
                'total_clicks': user[6],
                'diamonds': user[7]
            })
        
        return web.json_response({
            'users': result,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logging.error(f"Error in /api/admin/users: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/admin/search')
async def admin_search_users(request):
    try:
        data = await request.json()
        user_id = data.get('user_id')
        query = data.get('query', '')
        
        if not user_id:
            return web.json_response({'error': 'No user_id'}, status=400)
        
        if int(user_id) not in ADMIN_IDS:
            return web.json_response({'error': 'Unauthorized'}, status=403)
        
        if not query or len(query) < 2:
            return web.json_response({'error': 'Query too short'}, status=400)
        
        users = await search_users(query)
        
        result = []
        for user in users:
            result.append({
                'user_id': user[0],
                'username': user[1] or 'No username',
                'first_name': user[2] or 'No name',
                'last_name': user[3] or '',
                'coins': user[4],
                'level': user[5],
                'total_clicks': user[6]
            })
        
        return web.json_response({
            'users': result,
            'query': query,
            'count': len(result)
        })
    except Exception as e:
        logging.error(f"Error in /api/admin/search: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/admin/add_coins')
async def admin_add_coins_api(request):
    try:
        data = await request.json()
        admin_id = data.get('admin_id')
        target_id = data.get('target_id')
        amount = data.get('amount')
        
        if not all([admin_id, target_id, amount]):
            return web.json_response({'error': 'Missing data'}, status=400)
        
        if int(admin_id) not in ADMIN_IDS:
            return web.json_response({'error': 'Unauthorized'}, status=403)
        
        await admin_add_coins(int(target_id), int(amount))
        
        user = await get_user(int(target_id))
        return web.json_response({
            'success': True,
            'user_id': target_id,
            'new_coins': user[4] if user else 0,
            'message': f'✅ {target_id} ga {amount} tanga qo\'shildi!'
        })
    except Exception as e:
        logging.error(f"Error in /api/admin/add_coins: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/admin/add_exp')
async def admin_add_exp_api(request):
    try:
        data = await request.json()
        admin_id = data.get('admin_id')
        target_id = data.get('target_id')
        amount = data.get('amount')
        
        if not all([admin_id, target_id, amount]):
            return web.json_response({'error': 'Missing data'}, status=400)
        
        if int(admin_id) not in ADMIN_IDS:
            return web.json_response({'error': 'Unauthorized'}, status=403)
        
        await admin_add_exp(int(target_id), int(amount))
        
        user = await get_user(int(target_id))
        return web.json_response({
            'success': True,
            'user_id': target_id,
            'new_exp': user[5] if user else 0,
            'message': f'✅ {target_id} ga {amount} EXP qo\'shildi!'
        })
    except Exception as e:
        logging.error(f"Error in /api/admin/add_exp: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/admin/add_energy')
async def admin_add_energy_api(request):
    try:
        data = await request.json()
        admin_id = data.get('admin_id')
        target_id = data.get('target_id')
        amount = data.get('amount')
        
        if not all([admin_id, target_id, amount]):
            return web.json_response({'error': 'Missing data'}, status=400)
        
        if int(admin_id) not in ADMIN_IDS:
            return web.json_response({'error': 'Unauthorized'}, status=403)
        
        await admin_add_energy(int(target_id), int(amount))
        
        user = await get_user(int(target_id))
        return web.json_response({
            'success': True,
            'user_id': target_id,
            'new_energy': user[11] if user else 0,
            'message': f'✅ {target_id} ga {amount} energiya qo\'shildi!'
        })
    except Exception as e:
        logging.error(f"Error in /api/admin/add_energy: {e}")
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
        
        logging.info(f"Creating auction: user_id={user_id}, name={name}, price={price}")
        
        if not all([user_id, name, desc, price, duration]):
            return web.json_response({'error': 'Missing data'}, status=400)
        
        user = await get_user(int(user_id))
        if not user:
            return web.json_response({'error': 'User not found'}, status=404)
        
        if user[4] < int(price):
            return web.json_response({'error': 'Not enough coins to create auction'}, status=400)
        
        await update_user_stats(int(user_id), coins_delta=-int(price))
        
        end_time = datetime.now() + timedelta(minutes=int(duration))
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """INSERT INTO auctions 
                   (creator_id, item_name, item_description, start_price, current_bid, end_time) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (int(user_id), name, desc, int(price), int(price), end_time.isoformat())
            )
            await db.commit()
            auction_id = cursor.lastrowid
        
        updated_user = await get_user(int(user_id))
        
        return web.json_response({
            'success': True,
            'auction_id': auction_id,
            'coins': updated_user[4],
            'message': f'✅ Auktsion yaratildi! ID: {auction_id}'
        })
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
        
        logging.info(f"Placing bid: user_id={user_id}, auction_id={auction_id}, amount={amount}")
        
        if not all([user_id, auction_id, amount]):
            return web.json_response({'error': 'Missing data'}, status=400)
        
        user = await get_user(int(user_id))
        if not user:
            return web.json_response({'error': 'User not found'}, status=404)
        
        if user[4] < amount:
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
            
            if auction[6] and auction[6] > 0:
                await update_user_stats(int(auction[6]), coins_delta=auction[5])
            
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
            'coins': updated_user[4],
            'message': f'✅ Taklif qabul qilindi! Yangi narx: {amount}'
        })
    except Exception as e:
        logging.error(f"Error in /api/auction/bid: {e}")
        return web.json_response({'error': str(e)}, status=500)

@routes.get('/api/auctions')
async def list_auctions(request):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                """SELECT a.*, u.username, u.first_name, u.title 
                   FROM auctions a 
                   LEFT JOIN users u ON a.creator_id = u.user_id 
                   WHERE a.is_active = 1 AND a.end_time > datetime('now')
                   ORDER BY a.created_at DESC LIMIT 20"""
            ) as cursor:
                auctions = await cursor.fetchall()
        
        result = []
        for auction in auctions:
            creator_name = auction[11] or auction[12] or str(auction[1])
            result.append({
                'id': auction[0],
                'creator_id': auction[1],
                'creator_name': creator_name,
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
                        await ws.send_json({
                            'type': 'system',
                            'message': '✅ Chatga ulandingiz!'
                        })
                        
                    elif data.get('type') == 'chat' and user_id:
                        user = await get_user(int(user_id))
                        if user:
                            chat_msg = {
                                'type': 'chat',
                                'user_id': user_id,
                                'username': user[1] or user[2] or 'Anonim',
                                'first_name': user[2] or 'Anonim',
                                'title': user[8] or '🟢 Yangi oyinchi',
                                'color': user[9] or '#00ff88',
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
                                
                except json.JSONDecodeError as e:
                    logging.error(f"JSON decode error: {e}")
                except Exception as e:
                    logging.error(f"WebSocket message error: {e}")
                    
            elif msg.type == web.WSMsgType.ERROR:
                logging.error(f"WebSocket error: {ws.exception()}")
                break
                
    except Exception as e:
        logging.error(f"WebSocket handler error: {e}")
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
        "🎨 Skinlar\n"
        "🏆 Reyting\n\n"
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
    await init_db()
    
    if not os.path.exists('web_app'):
        os.makedirs('web_app')
    
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logging.info("Web App server started on port 8080")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
