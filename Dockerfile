# Використовуємо офіційний легкий образ Python
FROM python:3.12-slim

# Встановлюємо робочу директорію всередині контейнера
WORKDIR /app

# Забороняємо Python створювати кеш-файли та буферизувати вивід
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Копіюємо список залежностей і встановлюємо їх
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь наш код у контейнер
COPY . /app/