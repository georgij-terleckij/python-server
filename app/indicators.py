import pandas as pd


def bollinger_bands(data: pd.DataFrame, window=20, std_dev=2):
    """
    Рассчитывает полосы Боллинджера.
    :param data: DataFrame с колонкой 'close'.
    :param window: Окно для скользящей средней.
    :param std_dev: Количество стандартных отклонений.
    :return: (верхняя полоса, средняя полоса, нижняя полоса)
    """
    rolling_mean = data['close'].rolling(window=window).mean()
    rolling_std = data['close'].rolling(window=window).std()

    upper_band = rolling_mean + (rolling_std * std_dev)
    lower_band = rolling_mean - (rolling_std * std_dev)

    return upper_band, rolling_mean, lower_band


def is_price_outside_bollinger(data: pd.DataFrame):
    """
    Проверяет, пробила ли цена верхнюю/нижнюю границу Боллинджера.
    """
    upper_band, _, lower_band = bollinger_bands(data)
    latest_close = data['close'].iloc[-1]

    if latest_close > upper_band.iloc[-1]:
        return "🔴 Цена выше верхней границы (перекупленность)"
    elif latest_close < lower_band.iloc[-1]:
        return "🟢 Цена ниже нижней границы (перепроданность)"
    return "⚪ В пределах нормального диапазона"


def calculate_rsi(data: pd.DataFrame, periods: int = 14) -> float:
    """
    Рассчитывает RSI.
    :param data: DataFrame с колонкой 'close'.
    :param window: Окно для расчета RSI.
    :return: Последнее значение RSI.
    """
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]  # Возвращаем последнее значение RSI


def check_rsi_signal(data: pd.DataFrame):
    """
    Анализирует RSI и дает сигнал.
    """
    rsi = calculate_rsi(data)
    if rsi > 70:
        return f"🔴 RSI = {round(rsi, 2)} (Перекупленность)"
    elif rsi < 30:
        return f"🟢 RSI = {round(rsi, 2)} (Перепроданность)"
    return f"⚪ RSI = {round(rsi, 2)} (Нейтрально)"


def combined_market_analysis(data: pd.DataFrame):
    """
    Анализ рынка с помощью Боллинджера и RSI.
    """
    bollinger_signal = is_price_outside_bollinger(data)
    rsi_signal = check_rsi_signal(data)

    print(bollinger_signal)
    print(rsi_signal)

    if "Перекупленность" in bollinger_signal and "Перекупленность" in rsi_signal:
        return f"🚨 Сигнал на продажу! {bollinger_signal}, {rsi_signal}"

    if "Перепроданность" in bollinger_signal and "Перепроданность" in rsi_signal:
        return f"📈 Сигнал на покупку! {bollinger_signal}, {rsi_signal}"

    return f"{bollinger_signal}, {rsi_signal}"


def detect_crash_reversal(data: pd.DataFrame, drop_threshold=5, period=10, volume_multiplier=1.5):
    """
    Анализирует резкое падение и разворот цены.
    :param data: DataFrame с историческими данными (столбцы 'close' и 'volume').
    :param drop_threshold: Минимальный процент падения.
    :param period: Количество свечей для анализа.
    :param volume_multiplier: Во сколько раз должен увеличиться объем после падения.
    :return: True, если разворот обнаружен.
    """
    recent_data = data.iloc[-period:]

    # Рассчитываем изменение цены
    price_change = (recent_data["close"].iloc[-1] - recent_data["close"].iloc[0]) / recent_data["close"].iloc[0] * 100

    # Проверяем, что было падение на drop_threshold%
    if price_change < -drop_threshold:
        # Проверяем рост объёмов
        avg_volume_before = data["volume"].iloc[-(period * 2):-period].mean()
        avg_volume_after = recent_data["volume"].mean()

        if avg_volume_after > avg_volume_before * volume_multiplier:
            return True  # Разворот обнаружен

    return False
