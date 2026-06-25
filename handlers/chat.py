from aiogram import types
from aiogram.filters import Command
from database import get_user
import aiosqlite
from datetime import datetime

# Global chat messages store (in production use database)
chat_messages = []

async def chat_command(message: types.Message):
    await message.answer(
        "💬 **Global chat**\n\n"
        "Xabar yuborish uchun: /msg [xabar]\n"
        "So'nggi xabarlarni ko'rish: /chat_history\n"
        "Chatga kirish: Web App orqali",
        parse_mode="Markdown"
    )

async def send_chat_message(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer("❌ Ishlatish: /msg [xabar]")
        return
    
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    
    msg_text = args[1]
    timestamp = datetime.now().isoformat()
    
    # Store message
    chat_messages.append({
        'user_id': user_id,
        'username': user[1] or user[2],
        'first_name': user[2],
        'title': user[7],
        'color': user[8],
        'message': msg_text,
        'time': timestamp
    })
    
    # Keep only last 100 messages
    if len(chat_messages) > 100:
        chat_messages.pop(0)
    
    await message.answer("✅ Xabar yuborildi!")

async def chat_history(message: types.Message):
    if not chat_messages:
        await message.answer("💬 Hali xabarlar yo'q.")
        return
    
    # Show last 10 messages
    recent = chat_messages[-10:]
    history_text = "💬 **So'nggi xabarlar:**\n\n"
    
    for msg in recent:
        name = msg['username'] or msg['first_name']
        # Truncate long names
        if len(name) > 20:
            name = name[:17] + "..."
        
        title_color = msg.get('color', '#00ff88')
        history_text += f"<b><span style='color:{title_color}'>{msg['title']}</span> {name}:</b> {msg['message']}\n"
    
    await message.answer(history_text, parse_mode="HTML")

# WebSocket handler for real-time chat
async def handle_websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            data = json.loads(msg.data)
            if data.get('type') == 'chat':
                # Broadcast to all connected clients
                for client in ws_clients:
                    if client != ws:
                        await client.send_json(data)
    
    return ws

ws_clients = set()