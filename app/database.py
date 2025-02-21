import mysql.connector
import os

DB_CONFIG = {
    "host": "mysql",
    "user": os.getenv("MYSQL_USER", "user"),
    "password": os.getenv("MYSQL_PASSWORD", "password"),
    "database": os.getenv("MYSQL_DATABASE", "bot"),
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

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

# Создаём таблицу при запуске контейнера
init_db()