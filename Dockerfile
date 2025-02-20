# Используем Python 3.9
FROM python:3.9

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt отдельно
COPY requirements.txt /app/requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем ВСЕ файлы проекта
COPY . /app

# Запускаем бота
CMD ["python", "/app/bot.py"]
# # Копируем ВСЮ папку /app внутрь контейнера
# COPY app /app
