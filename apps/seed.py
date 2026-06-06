"""
Seed-скрипт для заповнення бази тестовими даними.

Запуск (будь-який варіант):
    python manage.py seed                 # канонічний спосіб (рекомендовано)
    python manage.py shell < apps/seed.py # legacy-спосіб через shell

Щоб уникнути двох розбіжних реалізацій (саме вони раніше призвели до
NameError через cat_laptops), цей файл лише делегує до єдиного джерела
правди — management-команди `seed`.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# При запуску через `manage.py shell <` Django вже налаштований; виклик
# django.setup() повторно — безпечний (ідемпотентний).
try:
    django.setup()
except Exception:
    pass

from django.core.management import call_command

call_command('seed')
