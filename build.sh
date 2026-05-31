#!/usr/bin/env bash
# Зупиняємо скрипт, якщо виникає помилка
set -o errexit

echo "Встановлюємо залежності..."
pip install -r requirements.txt

echo "Збираємо статику..."
python manage.py collectstatic --no-input

echo "Запускаємо міграції бази даних..."
python manage.py migrate