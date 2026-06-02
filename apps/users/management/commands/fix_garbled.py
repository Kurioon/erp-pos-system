# -*- coding: utf-8 -*-
"""
Видаляє записи CashRegister і Warehouse з нечитабельними іменами
(залишки від старого некоректного кодування бази).
Зберігає лише записи, де ім'я містить нормальний кириличний текст.
"""
from django.core.management.base import BaseCommand
from orders.models import CashRegister
from warehouses.models import Warehouse


class Command(BaseCommand):
    help = 'Видаляє всі дублікати CashRegister/Warehouse (seed відтворить їх заново)'

    def handle(self, *args, **kwargs):
        count = CashRegister.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f'✓ Видалено {count} кас'))

        count = Warehouse.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f'✓ Видалено {count} складів'))

        self.stdout.write(self.style.SUCCESS('=== Тепер запускай: python manage.py seed ==='))
