import asyncio
from config import CHAT_ID


async def send_telegram_notification(text):
    """Отправляет сообщение в Telegram-бот"""
    from bot import bot  # ОТЛОЖЕННЫЙ ИМПОРТ
    await bot.send_message(CHAT_ID, text)
