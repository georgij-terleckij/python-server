import mysql.connector
import os
import time

DB_CONFIG = {
    "host": "mysql",
    "user": os.getenv("MYSQL_USER", "user"),
    "password": os.getenv("MYSQL_PASSWORD", "password"),
    "database": os.getenv("MYSQL_DATABASE", "bot"),
}


def get_db_connection():
    """Пытаемся подключиться к MySQL с повторными попытками"""
    retries = 10  # Увеличиваем количество попыток
    for i in range(retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except mysql.connector.Error as e:
            print(f"⚠️ MySQ не доступен, попытка {i+1}/{retries}... Ждём 5 сек")
            time.sleep(5)
    raise Exception("❌ Не удалось подключиться к MySQL! Проверь настройки.")

def log_to_db(level, message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (level, message) VALUES (%s, %s)", (level, message))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Ошибка логирования: {e}")

def init_db():
    """Создаёт таблицу логов, если её нет"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            level VARCHAR(10),
            message TEXT
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Инициализируем БД при запуске
init_db()