from binance.client import Client
import pandas as pd
import numpy as np
import time
from config import API_KEY, API_SECRET, SYMBOL, AMOUNT
from logger import logger
from indicators import detect_crash_reversal

client = Client(API_KEY, API_SECRET)


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
