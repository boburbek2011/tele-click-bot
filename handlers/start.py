from aiogram import types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from database import create_user
from config import WEBAPP_URL

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