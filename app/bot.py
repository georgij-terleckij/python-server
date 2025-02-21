import asyncio
import re
import io
import matplotlib.pyplot as plt
from database import log_to_db
from decimal import Decimal, ROUND_DOWN
from telebot.async_telebot import AsyncTeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from trading import get_price, place_order, get_open_orders, check_market, fetch_historical_data, get_balance, \
    make_order, fetch_candlestick_data, start_ws_monitoring, stop_ws_monitoring, monitoring
from indicators import calculate_rsi, detect_crash_reversal, combined_market_analysis
from config import TELEGRAM_TOKEN, SYMBOL
from logger import logger
import pandas as pd
from binance.client import Client
from config import API_KEY, API_SECRET, CHAT_ID
from keyboardMenu import get_main_keyboard, get_buy_menu, get_sell_menu

bot = AsyncTeleBot(TELEGRAM_TOKEN)
client = Client(API_KEY, API_SECRET)
# monitoring = True


def is_authorized(user_id):
    return str(user_id) == CHAT_ID


def is_monitoring():
    return monitoring


def start_monitoring():
    global monitoring
    if not monitoring:
        monitoring = True
        asyncio.create_task(monitor_market())


def stop_monitoring():
    global monitoring
    monitoring = False


@bot.message_handler(commands=["start", "menu"])
async def send_menu(message):
    """
    Отправляет меню с кнопками.
    """
    text = "Выберите действие:"
    await bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard())


@bot.message_handler(func=lambda message: message.text == "📊 Анализ рынка")
async def market_analysis(message):
    data = fetch_historical_data("BTCUSDT", interval="15m", limit=50)
    analysis = combined_market_analysis(data)
    await bot.send_message(message.chat.id, f"📊 Анализ рынка:\n\n{analysis}")


@bot.message_handler(func=lambda message: message.text == "📊 Курс")
async def send_price(message):
    """
    Показывает текущий курс BTC.
    """
    price = get_price()
    await bot.send_message(message.chat.id, f"Текущий курс BTC: {price} USDT", reply_markup=get_main_keyboard())


@bot.message_handler(func=lambda message: message.text == "📉 Купить")
async def buy_menu(message):
    """
    Открываем меню выбора способа покупки.
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

    await bot.send_message(message.chat.id, "Выберите способ покупки:", reply_markup=get_buy_menu())


@bot.message_handler(func=lambda message: message.text == "💰 Купить по текущему курсу")
async def buy_now_menu(message):
    """
    Меню с шагами покупки (25%, 50%, 75%, 100%).
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

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
    await bot.send_message(message.chat.id, f"Выберите количество USDT для покупки по {price} BTC:",
                           reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "🎯 Купить по указанному курсу")
async def ask_price(message):
    """
    Запрашиваем у пользователя цену.
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

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
            await bot.send_message(message.chat.id, "Недостаточно средств для покупки! 🔴",
                                   reply_markup=get_main_keyboard())
            return

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        for percent in [25, 50, 75, 100]:
            amount = round((usdt_balance * percent / 100), 2)
            quantity = Decimal(usdt_balance * percent / 100).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
            keyboard.add(KeyboardButton(f"Купить {percent}% ({quantity}:BTC={amount}:USDT) Price:{price}"))

        keyboard.add(KeyboardButton("🔙 Назад в меню"))
        await bot.send_message(message.chat.id, f"Выберите количество USDT для покупки по {price} :",
                               reply_markup=keyboard)
    except ValueError:
        await bot.send_message(message.chat.id, "Некорректное значение! Введите число.", reply_markup=get_buy_menu())


@bot.message_handler(func=lambda message: message.text.startswith(("Купить")))
async def buy_selected_amount(message):
    """
    Обрабатываем выбор пользователя и создаем ордер.
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

    try:
        pattern = r"\(([\d.]+):BTC=([\d.]+):USDT\) Price:([\d.]+)"
        match = re.search(pattern, message.text)

        if match:
            btc = float(match.group(1))
            usdt = float(match.group(2))
            price = float(match.group(3))
            order = make_order("BUY", btc, price)
            await bot.send_message(message.chat.id, f"✅ Ордер на {btc} BTC размещен!\n{order}",
                                   reply_markup=get_main_keyboard())
        else:
            print("Не удалось распарсить строку")
    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка при создании ордера: {e}", reply_markup=get_main_keyboard())


@bot.message_handler(func=lambda message: message.text == "🔙 Назад в меню")
async def back_to_menu(message):
    await send_menu(message)

@bot.message_handler(func=lambda message: message.text == "📈 Продать")
async def sell_menu(message):
    """
    Открываем меню выбора способа продажи.
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

    await bot.send_message(message.chat.id, "Выберите способ продажи:", reply_markup=get_sell_menu())


@bot.message_handler(func=lambda message: message.text == "💰 Продать по текущему курсу")
async def sell_now_menu(message):
    """
    Меню с шагами продажи (25%, 50%, 75%, 100%).
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

    btc_balance = get_balance("BTC")
    if btc_balance < 0.0001:  # Проверка, есть ли BTC для продажи
        await bot.send_message(message.chat.id, "Недостаточно BTC для продажи! 🔴", reply_markup=get_main_keyboard())
        return

    price = get_price()
    await bot.send_message(message.chat.id, f"Текущий курс BTC: {price} USDT", reply_markup=get_main_keyboard())

    quantity = Decimal(btc_balance).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
    order = place_order("SELL", quantity)
    await bot.send_message(message.chat.id, f"✅ Ордер на продажу {quantity} BTC размещен!\n{order}",
                           reply_markup=get_main_keyboard())


@bot.message_handler(func=lambda message: message.text == "🎯 Продать по указанному курсу")
async def ask_sell_price(message):
    """
    Запрашиваем у пользователя цену.
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

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
        await bot.send_message(message.chat.id, f"Выберите количество BTC для продажи по {price} USDT:",
                               reply_markup=keyboard)
    except ValueError:
        await bot.send_message(message.chat.id, "Некорректное значение! Введите число.", reply_markup=get_sell_menu())


@bot.message_handler(func=lambda message: message.text.startswith("Продать"))
async def sell_selected_amount(message):
    """
    Обрабатываем выбор пользователя и создаем ордер на продажу.
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

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
        await bot.send_message(message.chat.id, f"✅ Ордер на продажу {btc} BTC размещен!\n{order}",
                               reply_markup=get_main_keyboard())
    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка при создании ордера: {e}", reply_markup=get_main_keyboard())


@bot.message_handler(func=lambda message: message.text == "📑 Ордеры")
async def open_orders(message):
    """
    Показывает список открытых ордеров.
    """
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

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

        await bot.send_photo(message.chat.id, img_io,
                             caption=f"📊 15-минутный график BTC/USDT. Текущий курс BTC: {price} USDT")

    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка при загрузке графика: {e}")


async def fetch_and_calculate_rsi():
    """ Получаем исторические данные и считаем RSI """
    try:
        klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_15MINUTE, limit=30)
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


# async def monitor_market():
#     while True:
#         data = fetch_historical_data("BTCUSDT", interval="1m", limit=50)
#         if detect_crash_reversal(data):
#             await bot.send_message(CHAT_ID, "📉 Обнаружен резкий разворот! Возможен рост!")
#         await asyncio.sleep(60)  # Мониторим каждую минуту

@bot.message_handler(func=lambda message: message.text == 'Старт/Стоп мониторинг')
async def toggle_monitoring(message):
    global monitoring
    if monitoring:
        monitoring = False
        await bot.send_message(message.chat.id, 'Мониторинг остановлен.')
    else:
        monitoring = True
        await bot.send_message(message.chat.id, 'Мониторинг запущен.')
        await monitor_market()

async def monitor_market():
    while monitoring:
        price = get_price()
        # log_to_db("INFO", f"Текущая цена BTC: {price}")
        data = fetch_historical_data("BTCUSDT", interval="1m", limit=50)
        if detect_crash_reversal(data, 1):
            await bot.send_message(CHAT_ID, "📉 Обнаружен резкий разворот! Возможен рост!")
        await asyncio.sleep(60)

@bot.message_handler(func=lambda message: message.text == '🚀 Авто продажа')
async def sell_auto_bot(message):
    if not is_authorized(message.chat.id):
        await bot.send_message(message.chat.id, "⛔ У вас нет прав на выполнение этой команды.")
        return

    await bot.send_message(message.chat.id, "Введите цену, по которой хотите продать BTC:")

    @bot.message_handler(content_types=["text"])
    async def process_sell_step(msg):
        try:
            price = float(msg.text.strip())
            start_ws_monitoring(price)
            await bot.send_message(msg.chat.id, f"🎯 Ожидаем достижения цены {price} USDT...")
        except ValueError:
            await bot.send_message(msg.chat.id, "❌ Некорректное значение! Введите число.")


@bot.message_handler(commands=["sell_status"])
async def check_sell_status(message):
    """Проверяет статус авто-продажи"""
    if monitoring:
        await bot.send_message(message.chat.id, f"✅ Авто-продажа активна! Ждём цену: {target_price} USDT")
    else:
        await bot.send_message(message.chat.id, "⛔ Авто-продажа отключена.")

@bot.message_handler(commands=["sell_cancel"])
async def cancel_auto_sell(message):
    """Отменяет авто-продажу"""
    if monitoring:
        stop_ws_monitoring()
        await bot.send_message(message.chat.id, "🚫 Авто-продажа отменена!")
    else:
        await bot.send_message(message.chat.id, "⛔ Авто-продажа и так отключена.")


@bot.message_handler(func=lambda message: message.text == "📊 Статус авто-продажи")
async def check_auto_sell_button(message):
    await check_sell_status(message)

@bot.message_handler(func=lambda message: message.text == "🛑 Отмена авто-продажи")
async def cancel_auto_sell_button(message):
    await cancel_auto_sell(message)


async def main():
    logger.info("Бот запущен")
    # asyncio.create_task(rsi_alert_loop())  # Запускаем мониторинг RSI
    # asyncio.create_task(market_watcher())  # Запускаем фоновый процесс анализа рынка
    asyncio.create_task(monitor_market())
    await bot.polling()


if __name__ == "__main__":
    asyncio.run(main())
