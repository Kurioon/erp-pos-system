# -*- coding: utf-8 -*-
from decimal import Decimal
from django.core.management.base import BaseCommand
from users.models import CustomUser
from products.models import Nomenclature
from warehouses.models import Warehouse, WarehouseStock
from orders.models import CashRegister, ExchangeRate


class Command(BaseCommand):
    help = 'Заповнює базу тестовими даними'

    def handle(self, *args, **kwargs):
        self.stdout.write('=== Запуск seed ===')

        # Користувачі
        if not CustomUser.objects.filter(email='admin@erp.com').exists():
            admin = CustomUser.objects.create_superuser(
                email='admin@erp.com',
                password='admin123',
                name='Адмін'
            )
            admin.role = 'admin'
            admin.save()
            self.stdout.write('✓ Адмін створений')
        else:
            self.stdout.write('– Адмін вже існує')

        if not CustomUser.objects.filter(email='seller@erp.com').exists():
            seller = CustomUser.objects.create_user(
                email='seller@erp.com',
                password='seller123',
                name='Продавець Іван'
            )
            seller.role = 'seller'
            seller.save()
            self.stdout.write('✓ Продавець створений')
        else:
            self.stdout.write('– Продавець вже існує')

        # Склади
        wh1, _ = Warehouse.objects.get_or_create(
            name='Магазин №1',
            defaults={'address': 'вул. Хрещатик, 1'}
        )
        wh2, _ = Warehouse.objects.get_or_create(
            name='Магазин №2',
            defaults={'address': 'вул. Василя Стуса, 22'}
        )
        self.stdout.write('✓ Склади створені')

        # Каси
        CashRegister.objects.get_or_create(
            name='Каса Магазин №1',
            defaults={'warehouse': wh1}
        )
        CashRegister.objects.get_or_create(
            name='Каса Магазин №2',
            defaults={'warehouse': wh2}
        )
        self.stdout.write('✓ Каси створені')

        # Курси валют
        ExchangeRate.objects.get_or_create(currency='USD', defaults={'rate_to_uah': Decimal('40.5000')})
        ExchangeRate.objects.get_or_create(currency='EUR', defaults={'rate_to_uah': Decimal('43.2000')})
        self.stdout.write('✓ Курси валют створені')

        # Номенклатура
        products_data = [
            ('NB001', 'Ноутбук Lenovo IdeaPad 15', 'шт', '4820001000001', '18000.00', '15.00', '20.00'),
            ('NB002', 'Ноутбук HP Pavilion 14', 'шт', '4820001000002', '22000.00', '12.00', '20.00'),
            ('PC001', 'Монітор Samsung 27"', 'шт', '4820001000003', '8500.00', '18.00', '20.00'),
            ('KB001', 'Клавіатура Logitech K380', 'шт', '4820001000004', '1200.00', '25.00', '20.00'),
            ('MS001', 'Миша Logitech MX Master 3', 'шт', '4820001000005', '2800.00', '20.00', '20.00'),
            ('HDD001', 'SSD Samsung 1TB', 'шт', '4820001000006', '3200.00', '15.00', '20.00'),
            ('RAM001', 'RAM DDR4 16GB Kingston', 'шт', '4820001000007', '1800.00', '20.00', '20.00'),
            ('PSU001', 'Зарядний пристрій USB-C 65W', 'шт', '4820001000008', '950.00', '30.00', '20.00'),
            ('CBL001', 'Кабель HDMI 2м', 'шт', '4820001000009', '150.00', '50.00', '20.00'),
            ('BG001', 'Сумка для ноутбука 15.6"', 'шт', '4820001000010', '650.00', '35.00', '20.00'),
            ('PHN001', 'Смартфон Samsung Galaxy A55', 'шт', '4820001000011', '14000.00', '10.00', '20.00'),
            ('PHN002', 'Смартфон iPhone 15', 'шт', '4820001000012', '38000.00', '8.00', '20.00'),
            ('TAB001', 'Планшет iPad Air 11"', 'шт', '4820001000013', '28000.00', '10.00', '20.00'),
            ('SPK001', 'Bluetooth колонка JBL Charge 5', 'шт', '4820001000014', '3500.00', '22.00', '20.00'),
            ('HP001', 'Навушники Sony WH-1000XM5', 'шт', '4820001000015', '9800.00', '15.00', '20.00'),
            ('THERM001', 'Термопаста Arctic MX-4', 'шт', '4820001000016', '120.00', '60.00', '20.00'),
            ('SCRW001', 'Набір викруток для ноутбуків', 'шт', '4820001000017', '280.00', '40.00', '20.00'),
            ('USB001', 'USB-хаб 4 порти 3.0', 'шт', '4820001000018', '380.00', '35.00', '20.00'),
            ('WC001', 'Веб-камера Logitech C920', 'шт', '4820001000019', '2200.00', '20.00', '20.00'),
            ('ANTV001', 'Антивірус ESET 1 рік', 'ліц', '4820001000020', '450.00', '30.00', '20.00'),
        ]

        created_products = []
        for code, name, unit, barcode, purchase, markup, vat in products_data:
            p, _ = Nomenclature.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'unit': unit,
                    'barcode': barcode,
                    'purchase_price': Decimal(purchase),
                    'markup_percentage': Decimal(markup),
                    'vat_rate': Decimal(vat),
                }
            )
            # Уявна опт-ціна для демо: закупівельна + 10%.
            # Дозаповнюємо лише якщо ще не задано (ідемпотентність seed).
            if p.wholesale_price is None:
                p.wholesale_price = (Decimal(purchase) * Decimal('1.10')).quantize(Decimal('0.01'))
                p.save()
            created_products.append(p)

        self.stdout.write(f'✓ {len(created_products)} товарів створено/знайдено')

        # Залишки
        stock_data = [
            (wh1, 0, 5), (wh1, 1, 3), (wh1, 2, 8), (wh1, 3, 20), (wh1, 4, 15),
            (wh1, 5, 10), (wh1, 6, 12), (wh1, 7, 25), (wh1, 8, 30), (wh1, 9, 7),
            (wh2, 10, 4), (wh2, 11, 2), (wh2, 12, 3), (wh2, 13, 6), (wh2, 14, 8),
            (wh2, 15, 50), (wh2, 16, 15), (wh2, 17, 20), (wh2, 18, 10), (wh2, 19, 5),
        ]

        for wh, idx, qty in stock_data:
            WarehouseStock.objects.get_or_create(
                warehouse=wh,
                nomenclature=created_products[idx],
                defaults={'quantity': qty}
            )

        self.stdout.write('✓ Залишки заповнені')
        self.stdout.write('')
        self.stdout.write('=== Seed завершено ===')
        self.stdout.write('admin@erp.com / admin123')
        self.stdout.write('seller@erp.com / seller123')
