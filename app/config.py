import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Настройки бота
SYMBOL = "BTCUSDT"  # Торговая пара
AMOUNT = 0.001      # Количество для ордера