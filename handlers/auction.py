from aiogram import types
from aiogram.filters import Command
from database import get_user, update_user_stats
import aiosqlite
from datetime import datetime, timedelta

async def auction_command(message: types.Message):
    await message.answer(
        "🔨 **Auktsion**\n\n"
        "Auktsion ochish: /create_auction [nomi] [tavsif] [boshlang'ich_narx] [davomiylik_daqiqa]\n"
        "Taklif qilish: /bid [auction_id] [miqdor]\n"
        "Auktsionlar: /auctions",
        parse_mode="Markdown"
    )

async def create_auction(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=4)
    
    if len(args) < 5:
        await message.answer("❌ Ishlatish: /create_auction [nomi] [tavsif] [boshlang'ich_narx] [davomiylik_daqiqa]")
        return
    
    name = args[1]
    desc = args[2]
    start_price = int(args[3])
    duration = int(args[4])
    
    end_time = datetime.now() + timedelta(minutes=duration)
    
    async with aiosqlite.connect("tele_click.db") as db:
        await db.execute(
            """INSERT INTO auctions 
               (creator_id, item_name, item_description, start_price, current_bid, end_time) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, name, desc, start_price, start_price, end_time.isoformat())
        )
        await db.commit()
    
    await message.answer(f"✅ Auktsion yaratildi!\n\n📦 {name}\n💰 Boshlang'ich narx: {start_price}\n⏰ Tugaydi: {end_time.strftime('%H:%M')}")

async def place_bid(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer("❌ Ishlatish: /bid [auction_id] [miqdor]")
        return
    
    auction_id = int(args[1])
    amount = int(args[2])
    
    user = await get_user(user_id)
    if not user or user[3] < amount:
        await message.answer("❌ Yetarli tanga yo'q!")
        return
    
    async with aiosqlite.connect("tele_click.db") as db:
        # Get auction
        async with db.execute(
            "SELECT * FROM auctions WHERE id = ? AND is_active = 1",
            (auction_id,)
        ) as cursor:
            auction = await cursor.fetchone()
        
        if not auction:
            await message.answer("❌ Auktsion topilmadi yoki tugagan!")
            return
        
        if amount <= auction[5]:  # current_bid
            await message.answer(f"❌ Taklif hozirgi narxdan ({auction[5]}) katta bo'lishi kerak!")
            return
        
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
    
    await message.answer(f"✅ Taklif qabul qilindi!\n💰 Yangi narx: {amount}")

async def list_auctions(message: types.Message):
    async with aiosqlite.connect("tele_click.db") as db:
        async with db.execute(
            """SELECT a.*, u.username, u.first_name 
               FROM auctions a 
               JOIN users u ON a.creator_id = u.user_id 
               WHERE a.is_active = 1 AND a.end_time > datetime('now')
               ORDER BY a.created_at DESC LIMIT 10"""
        ) as cursor:
            auctions = await cursor.fetchall()
    
    if not auctions:
        await message.answer("🔨 Hozircha faol auktsionlar yo'q.")
        return
    
    text = "🔨 **Faol auktsionlar:**\n\n"
    for auction in auctions:
        end_time = datetime.fromisoformat(auction[6])
        time_left = end_time - datetime.now()
        minutes = int(time_left.total_seconds() / 60)
        
        creator_name = auction[11] or auction[12] or str(auction[1])
        text += (
            f"📦 **{auction[3]}**\n"
            f"📝 {auction[4]}\n"
            f"💰 Narx: {auction[5]}\n"
            f"👤 Yaratuvchi: {creator_name}\n"
            f"⏰ Qolgan vaqt: {minutes} daqiqa\n"
            f"🆔 ID: `{auction[0]}`\n\n"
        )
    
    await message.answer(text, parse_mode="Markdown")