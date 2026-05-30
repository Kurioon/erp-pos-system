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

# Збираємо статичні файли (для адмінки та WhiteNoise)
# (Тут використовується фіктивний SECRET_KEY просто для того, щоб команда відпрацювала під час збірки)
# RUN SECRET_KEY="dummy_key_for_build" python manage.py collectstatic --noinput

# Вказуємо порт, який слухатиме контейнер (Render використовує 10000)
EXPOSE 10000

# Запускаємо Gunicorn. 
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-10000}"]