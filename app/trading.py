from binance.client import Client
import pandas as pd
import numpy as np
import asyncio
import concurrent.futures
import time
from database import log_to_db
from notifications import send_telegram_notification
from binance import ThreadedWebsocketManager
from config import API_KEY, API_SECRET, SYMBOL, AMOUNT
from logger import logger
from indicators import detect_crash_reversal

client = Client(API_KEY, API_SECRET)

monitoring = False  # Флаг отслеживания цены
target_price = None
ws_manager = None
latest_price = None  # Глобальная переменная для хранения последней цены


def start_ws_monitoring(price):
    """Запускает WebSocket для отслеживания цены через поток"""
    global monitoring, target_price, ws_manager
    target_price = float(price)
    monitoring = True

    # Запускаем WebSocket в отдельном потоке
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_running_loop()
    loop.run_in_executor(executor, start_ws)

def start_ws():
    """Запускает WebSocket в отдельном потоке"""
    global ws_manager
    ws_manager = ThreadedWebsocketManager()
    ws_manager.start()
    ws_manager.start_symbol_ticker_socket(callback=handle_ws_message, symbol=SYMBOL)


def stop_ws_monitoring():
    """Останавливает WebSocket мониторинг"""
    global monitoring, ws_manager
    monitoring = False

    if ws_manager:
        ws_manager.stop()
        ws_manager = None

def handle_ws_message(msg):
    """Обрабатывает входящие данные с Binance WebSocket"""
    global monitoring, latest_price
    if not monitoring:
        return

    latest_price = float(msg["c"])  # Обновляем глобальную переменную
    print(f"🔥 Текущая цена: {latest_price} USDT")

    # Запускаем проверку в уже существующем loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(check_sell_trigger(latest_price))
    else:
        asyncio.run(check_sell_trigger(latest_price))

async def check_sell_trigger(price):
    """Проверяет условия для продажи"""
    global monitoring, target_price

    if price >= target_price:
        print(f"🎯 Цена достигла {target_price}, начинаем анализ тренда...")
        await monitor_price_trend()

async def monitor_price_trend():
    """Следим за ценой 10 секунд и ищем момент максимума"""
    global monitoring
    max_price = None
    start_price = get_latest_price()  # Запоминаем стартовую цену

    for i in range(10):
        await asyncio.sleep(1)
        latest_price = get_latest_price()

        # Запоминаем максимум за 10 секунд
        if max_price is None or latest_price > max_price:
            max_price = latest_price

        print(f"📊 [{i + 1}/10] Цена BTC: {latest_price}, макс: {max_price}")

    if max_price < start_price * 1.001:  # Если цена не пошла вверх на 0.1%, продаём
        print(f"✅ Цена стабилизировалась, продаём по {max_price}!")
        # place_order("SELL", 0.001)
        log_to_db("SELL", f"Продажа BTC по {max_price}, старт был {start_price}")
        # await send_telegram_notification(f"🚀 Авто-продажа! Продали BTC по {max_price} USDT!")
    else:
        print(f"❌ Цена ещё растёт, ждём дальше.")
        # await send_telegram_notification(f"⏳ Цена растёт, не продаём! Макс: {max_price} USDT")

    stop_ws_monitoring()

    # for _ in range(10):
    #     await asyncio.sleep(1)
    #     latest_price = get_latest_price()
    #     if max_price is None or latest_price > max_price:
    #         max_price = latest_price
    #     else:
    #         print(f"📉 Цена начала падать: {latest_price}, продаём!")
    #         # place_order("SELL", 0.001)  # Продаём 0.001 BTC
    #         log_to_db("SELL",f"Текущая цена BTC: {latest_price} Залочено {target_price}")
    #         stop_ws_monitoring()
    #         return
    #
    # print(f"⏳ 10 секунд прошло, продаём по {max_price}!")
    # # place_order("SELL", 0.001)
    # log_to_db("SELL", f"Текущая цена BTC: {max_price} Залочено {target_price}")
    # stop_ws_monitoring()

def get_latest_price():
    """Получает текущую цену BTC (из WebSocket)"""
    return latest_price
    # return float(ws_manager.tickers[SYMBOL]["c"])

def get_price():
    """Получаем текущую цену BTC"""
    try:
        price = client.get_symbol_ticker(symbol=SYMBOL)["price"]
        return float(price)
    except Exception as e:
        logger.error(f"Ошибка получения цены: {e}")
        return None


def place_order(side, quantity = AMOUNT):
    """Размещаем лимитный ордер"""
    try:
        price = get_price()
        if price:
            order = client.create_order(
                symbol=SYMBOL,
                side=side,
                type="LIMIT",
                timeInForce="GTC",
                quantity=quantity,
                price=str(price),
            )
            logger.info(f"Ордер размещен: {order}")
            return order
    except Exception as e:
        logger.error(f"Ошибка при размещении ордера: {e}")
        return None


def make_order(side, quantity, price):
    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=side,
            type="LIMIT",
            timeInForce="GTC",
            quantity=quantity,
            price=str(price),
        )
        logger.info(f"Ордер размещен: {order}")
        return order
    except Exception as e:
        logger.error(f"Ошибка при размещении ордера: {e}")
        return None


def place_test_order(quantity, price):
    try:
        order = client.create_test_order(
            symbol=SYMBOL,
            side="BUY",
            type="LIMIT",
            timeInForce="GTC",
            quantity=quantity,
            price=price)
        print(order)
        logger.info(f"Ордер размещен: {order}")
        return order
    except Exception as e:
        logger.error(f"Ошибка при размещении ордера: {e}")
        return None


def get_open_orders():
    """Получаем список открытых ордеров"""
    try:
        orders = client.get_open_orders(symbol=SYMBOL)
        logger.info(f"Открытые ордера: {orders}")
        return orders
    except Exception as e:
        logger.error(f"Ошибка получения ордеров: {e}")
        return []


def fetch_historical_data(symbol: str, interval="1h", limit=100):
    """
    Получаем исторические данные с Binance.
    :param symbol: Торговая пара (например, "BTCUSDT").
    :param interval: Таймфрейм (например, "1h" – 1 час).
    :param limit: Количество свечей для анализа.
    :return: DataFrame с историческими данными.
    """
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time",
                                       "quote_asset_volume", "number_of_trades", "taker_buy_base", "taker_buy_quote",
                                       "ignore"])
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df


def check_market():
    """
    Проверяем рынок на резкое падение и возможный разворот.
    """
    data = fetch_historical_data(SYMBOL, "15m", 50)  # Анализируем 50 свечей по 15 минут

    if detect_crash_reversal(data):
        mes = "⚠ Обнаружен разворот после падения! Возможно, хорошая точка для входа в рынок."
        print(mes)
        return mes
    else:
        print("🚀 Никаких резких изменений, рынок стабилен.")


def get_balance(asset: str) -> float:
    """
    Получает баланс указанной валюты.

    :param asset: Тикер валюты (например, 'USDT', 'BTC')
    :return: Баланс в виде числа с плавающей точкой
    """
    try:
        balance = client.get_asset_balance(asset=asset)
        if balance:
            return float(balance["free"])
        return 0.0
    except Exception as e:
        print(f"Ошибка при получении баланса {asset}: {e}")
        return 0.0


def fetch_candlestick_data():
    """
    Запрашиваем 15-минутные свечи BTC/USDT с Binance.
    """
    klines = client.get_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)

    times = [int(entry[0]) for entry in klines]  # Время в миллисекундах
    prices = [float(entry[4]) for entry in klines]  # Цена закрытия
    times = np.array(times, dtype='datetime64[ms]')  # Преобразуем время

    return times, prices
