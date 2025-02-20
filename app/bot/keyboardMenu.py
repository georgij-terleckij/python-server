from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    """
    Создаёт клавиатуру с основными кнопками.
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📊 Курс"), KeyboardButton("📈 Купить"), KeyboardButton("📉 Продать"))
    keyboard.add(KeyboardButton("📑 Ордеры"), KeyboardButton("📊 RSI"), KeyboardButton("📊 График"))
    return keyboard

def get_buy_menu():
    """
    Меню покупки.
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💰 Купить по текущему курсу"), KeyboardButton("🎯 Купить по указанному курсу"))
    keyboard.add(KeyboardButton("🔙 Назад в меню"))
    return keyboard

def get_sell_menu():
    """
    Меню продажи.
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💰 Продать по текущему курсу"), KeyboardButton("🎯 Продать по указанному курсу"))
    keyboard.add(KeyboardButton("🔙 Назад в меню"))
    return keyboard