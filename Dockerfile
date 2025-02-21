# Используем Python 3.9
FROM python:3.9

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем ВСЕ файлы проекта
COPY . /app

# Копируем requirements.txt отдельно
# COPY requirements.txt /app/requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем бота
# CMD ["python", "/app/bot.py"]
# CMD ["sh", "-c", "python app/bot.py & python app/flask_app.py"]
CMD ["sh", "-c", "PYTHONPATH=/app python app/bot.py & PYTHONPATH=/app python app/flask_app.py"]