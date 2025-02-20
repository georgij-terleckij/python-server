import pandas as pd

def calculate_rsi(data: pd.DataFrame, periods: int = 14) -> float:
    """Расчет индекса относительной силы (RSI)"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


def detect_crash_reversal(data: pd.DataFrame, drop_threshold=5, period=10):
    """
    Анализирует резкое падение и разворот цены.
    :param data: DataFrame с историческими данными (должны быть столбцы 'close' и 'volume').
    :param drop_threshold: Минимальный процент падения цены за указанный период.
    :param period: Количество свечей, за которое анализируем падение.
    :return: True, если обнаружен разворот, иначе False.
    """
    recent_data = data.iloc[-period:]

    # Рассчитываем изменение цены
    price_change = (recent_data["close"].iloc[-1] - recent_data["close"].iloc[0]) / recent_data["close"].iloc[0] * 100

    # Проверяем, что было падение на drop_threshold%
    if price_change < -drop_threshold:
        # Проверяем рост объёмов
        avg_volume_before = data["volume"].iloc[-(period * 2):-period].mean()
        avg_volume_after = recent_data["volume"].mean()

        if avg_volume_after > avg_volume_before * 1.5:  # Объём вырос в 1.5 раза
            return True  # Разворот после резкого падения

    return False
