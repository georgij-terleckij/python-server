import asyncio
import re
import io
import matplotlib.pyplot as plt
from decimal import Decimal, ROUND_DOWN
from telebot.async_telebot import AsyncTeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from trading import get_price, place_order, get_open_orders, check_market, fetch_historical_data, get_balance, place_test_order, make_order , fetch_candlestick_data
from indicators import calculate_rsi
from config import TELEGRAM_TOKEN, SYMBOL
from logger import logger
import pandas as pd
from binance.client import Client
from config import API_KEY, API_SECRET
from bot.keyboardMenu import get_main_keyboard, get_buy_menu, get_sell_menu

CHAT_ID = 622553104
bot = AsyncTeleBot(TELEGRAM_TOKEN)
client = Client(API_KEY, API_SECRET)


@bot.message_handler(commands=["start", "menu"])
async def send_menu(message):
    """
    Отправляет меню с кнопками.
    """
    text = "Выберите действие:"
    await bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📊 Курс")
async def send_price(message):
    """
    Показывает текущий курс BTC.
    """
    price = get_price()
    await bot.send_message(message.chat.id, f"Текущий курс BTC: {price} USDT", reply_markup=get_main_keyboard())


# @bot.message_handler(commands=["buy"])
# async def buy_order(message):
#     order = place_order("BUY")
#     await bot.send_message(message.chat.id, f"Ордер на покупку размещен! {order}")

# @bot.message_handler(func=lambda message: message.text == "📈 Купить")
# async def buy_order(message):
#     """
#     Покупка BTC.
#     """
#     order = place_order("BUY")
#     await bot.send_message(message.chat.id, f"Ордер на покупку размещен! {order}", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📈 Купить")
async def buy_menu(message):
    """
    Открываем меню выбора способа покупки.
    """
    await bot.send_message(message.chat.id, "Выберите способ покупки:", reply_markup=get_buy_menu())

@bot.message_handler(func=lambda message: message.text == "💰 Купить по текущему курсу")
async def buy_now_menu(message):
    """
    Меню с шагами покупки (25%, 50%, 75%, 100%).
    """
    usdt_balance = get_balance("USDT")
    price = get_price()
    if usdt_balance < 10:  # Проверка, есть ли деньги
        await bot.send_message(message.chat.id, "Недостаточно средств для покупки! 🔴", reply_markup=get_main_keyboard())
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for percent in [25, 50, 75, 100]:
        amount = round((usdt_balance * percent / 100) / price, 6)
        keyboard.add(KeyboardButton(f"{percent}% ({amount} BTC)"))

    keyboard.add(KeyboardButton("🔙 Назад в меню"))
    await bot.send_message(message.chat.id, f"Выберите количество USDT для покупки по {price} BTC:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "🎯 Купить по указанному курсу")
async def ask_price(message):
    """
    Запрашиваем у пользователя цену.
    """
    await bot.send_message(message.chat.id, "Введите цену, по которой хотите оформит ордер BTC:")
    @bot.message_handler(content_types=["text"])
    async def process_buy_step(msg):
        quantity = msg.text.strip()
        await bot.send_message(msg.chat.id, f"Вы ввели {quantity} BTC!")
        await process_custom_price(msg)

async def process_custom_price(message):
    """
    Обрабатываем введённую цену и показываем шаги покупки.
    """
    try:
        price = float(message.text)
        usdt_balance = get_balance("USDT")
        await bot.send_message(message.chat.id, f"Текущий баланс: {usdt_balance} USDT")
        if usdt_balance < 10:
            await bot.send_message(message.chat.id, "Недостаточно средств для покупки! 🔴", reply_markup=get_main_keyboard())
            return

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        for percent in [25, 50, 75, 100]:
            amount = round((usdt_balance * percent / 100), 2)
            quantity = Decimal(usdt_balance * percent / 100).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
            keyboard.add(KeyboardButton(f"Купить {percent}% ({quantity}:BTC={amount}:USDT) Price:{price}") )

        keyboard.add(KeyboardButton("🔙 Назад в меню"))
        await bot.send_message(message.chat.id, f"Выберите количество USDT для покупки по {price} :", reply_markup=keyboard)
    except ValueError:
        await bot.send_message(message.chat.id, "Некорректное значение! Введите число.", reply_markup=get_buy_menu())

@bot.message_handler(func=lambda message: message.text.startswith(("Купить")))
async def buy_selected_amount(message):
    """
    Обрабатываем выбор пользователя и создаем ордер.
    """
    try:
        pattern = r"\(([\d.]+):BTC=([\d.]+):USDT\) Price:([\d.]+)"
        match = re.search(pattern, message.text)

        if match:
            btc = float(match.group(1))
            usdt = float(match.group(2))
            price = float(match.group(3))
            order = make_order("BUY",btc, price)
            await bot.send_message(message.chat.id, f"✅ Ордер на {btc} BTC размещен!\n{order}",
                                   reply_markup=get_main_keyboard())
        else:
            print("Не удалось распарсить строку")
    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка при создании ордера: {e}", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "🔙 Назад в меню")
async def back_to_menu(message):
    await send_menu(message)

# @bot.message_handler(func=lambda message: message.text == "📉 Продать")
# async def sell_order(message):
#     """
#     Продажа BTC.
#     """
#     order = place_order("SELL")
#     await bot.send_message(message.chat.id, f"Ордер на продажу размещен! {order}", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📉 Продать")
async def sell_menu(message):
    """
    Открываем меню выбора способа продажи.
    """
    await bot.send_message(message.chat.id, "Выберите способ продажи:", reply_markup=get_sell_menu())

@bot.message_handler(func=lambda message: message.text == "💰 Продать по текущему курсу")
async def sell_now_menu(message):
    """
    Меню с шагами продажи (25%, 50%, 75%, 100%).
    """
    btc_balance = get_balance("BTC")
    price = get_price()
    await bot.send_message(message.chat.id, f"Текущий курс BTC: {price} USDT", reply_markup=get_main_keyboard())

    if btc_balance < 0.0001:  # Проверка, есть ли BTC для продажи
        await bot.send_message(message.chat.id, "Недостаточно BTC для продажи! 🔴", reply_markup=get_main_keyboard())
        return
    quantity = Decimal(btc_balance).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
    order = place_order("SELL", quantity)
    await bot.send_message(message.chat.id, f"✅ Ордер на продажу {quantity} BTC размещен!\n{order}",
                           reply_markup=get_main_keyboard())

    # keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    # for percent in [25, 50, 75, 100]:
    #     amount = round(btc_balance * percent / 100, 6)
    #     keyboard.add(KeyboardButton(f"{percent}% ({amount} BTC)"))
    #
    # keyboard.add(KeyboardButton("🔙 Назад в меню"))
    # await bot.send_message(message.chat.id, f"Выберите количество BTC для продажи по {price} USDT:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "🎯 Продать по указанному курсу")
async def ask_sell_price(message):
    """
    Запрашиваем у пользователя цену.
    """
    await bot.send_message(message.chat.id, "Введите цену, по которой хотите продать BTC:")
    @bot.message_handler(content_types=["text"])
    async def process_buy_step(msg):
        quantity = msg.text.strip()
        await bot.send_message(msg.chat.id, f"Вы ввели {quantity} BTC!")
        await process_custom_sell_price(msg)

async def process_custom_sell_price(message):
    """
    Обрабатываем введённую цену и показываем шаги продажи.
    """
    try:
        price = float(message.text)
        btc_balance = get_balance("BTC")
        await bot.send_message(message.chat.id, f"Текущий баланс: {btc_balance} BTC")
        if btc_balance < 0.0001:
            await bot.send_message(message.chat.id, "Недостаточно BTC для продажи! 🔴", reply_markup=get_main_keyboard())
            return

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        for percent in [25, 50, 75, 100]:
            amount = Decimal(btc_balance * price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            quantity = Decimal(btc_balance * percent / 100).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
            keyboard.add(KeyboardButton(f"Продать  {percent}% ({quantity}:BTC={amount}:USDT) Price:{price}"))

        keyboard.add(KeyboardButton("🔙 Назад в меню"))
        await bot.send_message(message.chat.id, f"Выберите количество BTC для продажи по {price} USDT:", reply_markup=keyboard)
    except ValueError:
        await bot.send_message(message.chat.id, "Некорректное значение! Введите число.", reply_markup=get_sell_menu())

@bot.message_handler(func=lambda message: message.text.startswith("Продать"))
async def sell_selected_amount(message):
    """
    Обрабатываем выбор пользователя и создаем ордер на продажу.
    """
    try:
        pattern = r"\(([\d.]+):BTC=([\d.]+):USDT\) Price:([\d.]+)"
        match = re.search(pattern, message.text)

        if match:
            btc = float(match.group(1))  # Количество BTC
            usdt = float(match.group(2))  # Эквивалент в USDT
            price = float(match.group(3))  # Цена продажи
            order = make_order("SELL", btc, price)
        else:
            return None, None, None
        await bot.send_message(message.chat.id, f"✅ Ордер на продажу {btc} BTC размещен!\n{order}", reply_markup=get_main_keyboard())
    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка при создании ордера: {e}", reply_markup=get_main_keyboard())


@bot.message_handler(func=lambda message: message.text == "📑 Ордеры")
async def open_orders(message):
    """
    Показывает список открытых ордеров.
    """
    orders = get_open_orders()
    if orders:
        text = "\n".join([f"ID: {o['orderId']}, Сторона: {o['side']}, Цена: {o['price']}" for o in orders])
    else:
        text = "Нет открытых ордеров"
    await bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard())


@bot.message_handler(func=lambda message: message.text == "📊 RSI")
async def send_rsi(message):
    """
    Показывает текущий RSI.
    """
    # data = fetch_historical_data("BTCUSDT", "15m", 50)
    # rsi_value = calculate_rsi(data)
    rsi = await fetch_and_calculate_rsi()
    await bot.send_message(message.chat.id, f"Текущий RSI: {rsi:.2f}", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📊 График")
async def send_chart(message):
    """
    Генерируем и отправляем 15-минутный график BTC/USDT.
    """
    try:
        times, prices = fetch_candlestick_data()

        # Рисуем график
        plt.figure(figsize=(10, 5))
        plt.plot(times, prices, label="BTC/USDT", color="blue")
        plt.xlabel("Время")
        plt.ylabel("Цена (USDT)")
        plt.title("15-минутный график BTC/USDT")
        plt.grid(True)
        plt.legend()

        # Сохраняем картинку в память
        img_io = io.BytesIO()
        plt.savefig(img_io, format="png")
        img_io.seek(0)
        plt.close()

        price = get_price()

        await bot.send_photo(message.chat.id, img_io, caption=f"📊 15-минутный график BTC/USDT. Текущий курс BTC: {price} USDT")

    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка при загрузке графика: {e}")


async def fetch_and_calculate_rsi():
    """ Получаем исторические данные и считаем RSI """
    try:
        klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_1HOUR, limit=30)
        df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time",
                                           "quote_asset_volume", "number_of_trades", "taker_buy_base",
                                           "taker_buy_quote", "ignore"])
        df["close"] = df["close"].astype(float)
        rsi = calculate_rsi(df)
        return rsi
    except Exception as e:
        logger.error(f"Ошибка получения RSI: {e}")
        return None

async def rsi_alert_loop():
    """ Отслеживаем RSI и отправляем алерты в Телеграм """
    while True:
        rsi = await fetch_and_calculate_rsi()
        if rsi is not None:
            if rsi < 30:
                await bot.send_message(CHAT_ID, f"🔴 RSI = {rsi:.2f} (перепродан!) 🚨")
            elif rsi > 70:
                await bot.send_message(CHAT_ID, f"🟢 RSI = {rsi:.2f} (перекуплен!) 🚨")
        await asyncio.sleep(60)  # Проверяем раз в час

async def market_watcher():
    """
    Фоновая задача для мониторинга рынка каждые 15 минут.
    """
    while True:
        try:
            message = check_market()
            if message:
                await bot.send_message(CHAT_ID, f"⚠ Внимание! {message}")
        except Exception as e:
            print(f"Ошибка в market_watcher: {e}")
        await asyncio.sleep(60)  # Ждём 15 минут (900 секунд)


async def main():
    # asyncio.create_task(rsi_alert_loop())  # Запускаем мониторинг RSI
    asyncio.create_task(market_watcher())  # Запускаем фоновый процесс анализа рынка
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
