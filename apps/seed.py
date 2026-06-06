"""
Seed-скрипт для заповнення бази тестовими даними.
Запуск: python manage.py shell < apps/seed.py
або: python manage.py runscript seed (якщо встановлено django-extensions)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from users.models import CustomUser
from products.models import Nomenclature, Category
from warehouses.models import Warehouse, WarehouseStock
from orders.models import CashRegister, Supplier, Order, OrderItem

print("=== Запуск seed скрипту ===")

# Користувачі
admin, _ = CustomUser.objects.get_or_create(
    email='admin@erp.com',
    defaults={'name': 'Адмін', 'role': 'admin', 'is_staff': True, 'is_superuser': True}
)
admin.set_password('admin123')
admin.save()

seller, _ = CustomUser.objects.get_or_create(
    email='seller@erp.com',
    defaults={'name': 'Продавець Іван', 'role': 'seller'}
)
seller.set_password('seller123')
seller.save()
print("✓ Користувачі створені: admin@erp.com / admin123, seller@erp.com / seller123")

# Склади
wh1, _ = Warehouse.objects.get_or_create(name='Магазин №1', defaults={'address': 'вул. Хрещатик, 1'})
wh2, _ = Warehouse.objects.get_or_create(name='Магазин №2', defaults={'address': 'вул. Василя Стуса, 22'})
print("✓ Склади створені")

# Каси
cr1, _ = CashRegister.objects.get_or_create(name='Каса Магазин №1', defaults={'warehouse': wh1})
cr2, _ = CashRegister.objects.get_or_create(name='Каса Магазин №2', defaults={'warehouse': wh2})
print("✓ Каси створені")

# Категорії
cat_phones, _ = Category.objects.get_or_create(name='Смартфони')
cat_laptops, _ = Category.objects.get_or_create(name='Ноутбуки')
cat_tablets, _ = Category.objects.get_or_create(name='Планшети')
cat_accessories, _ = Category.objects.get_or_create(name='Аксесуари')
cat_audio, _ = Category.objects.get_or_create(name='Аудіо')
cat_components, _ = Category.objects.get_or_create(name='Комплектуючі')
cat_software, _ = Category.objects.get_or_create(name='Програмне забезпечення')
print("✓ Категорії створені")

# Номенклатура
products_data = [
    {'code': 'NB001', 'name': 'Ноутбук Lenovo IdeaPad 15', 'unit': 'шт', 'barcode': '4820001000001',
     'purchase_price': '18000.00', 'markup_percentage': '15.00', 'vat_rate': '20.00', 'category': cat_laptops},
    {'code': 'NB002', 'name': 'Ноутбук HP Pavilion 14', 'unit': 'шт', 'barcode': '4820001000002',
     'purchase_price': '22000.00', 'markup_percentage': '12.00', 'vat_rate': '20.00', 'category': cat_laptops},
    {'code': 'PC001', 'name': 'Монітор Samsung 27"', 'unit': 'шт', 'barcode': '4820001000003',
     'purchase_price': '8500.00', 'markup_percentage': '18.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'KB001', 'name': 'Клавіатура Logitech K380', 'unit': 'шт', 'barcode': '4820001000004',
     'purchase_price': '1200.00', 'markup_percentage': '25.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'MS001', 'name': 'Миша Logitech MX Master 3', 'unit': 'шт', 'barcode': '4820001000005',
     'purchase_price': '2800.00', 'markup_percentage': '20.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'HDD001', 'name': 'SSD Samsung 1TB', 'unit': 'шт', 'barcode': '4820001000006',
     'purchase_price': '3200.00', 'markup_percentage': '15.00', 'vat_rate': '20.00', 'category': cat_components},
    {'code': 'RAM001', 'name': 'RAM DDR4 16GB Kingston', 'unit': 'шт', 'barcode': '4820001000007',
     'purchase_price': '1800.00', 'markup_percentage': '20.00', 'vat_rate': '20.00', 'category': cat_components},
    {'code': 'PSU001', 'name': 'Зарядний пристрій USB-C 65W', 'unit': 'шт', 'barcode': '4820001000008',
     'purchase_price': '950.00', 'markup_percentage': '30.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'CBL001', 'name': 'Кабель HDMI 2м', 'unit': 'шт', 'barcode': '4820001000009',
     'purchase_price': '150.00', 'markup_percentage': '50.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'BG001', 'name': 'Сумка для ноутбука 15.6"', 'unit': 'шт', 'barcode': '4820001000010',
     'purchase_price': '650.00', 'markup_percentage': '35.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'PHN001', 'name': 'Смартфон Samsung Galaxy A55', 'unit': 'шт', 'barcode': '4820001000011',
     'purchase_price': '14000.00', 'markup_percentage': '10.00', 'vat_rate': '20.00', 'category': cat_phones},
    {'code': 'PHN002', 'name': 'Смартфон iPhone 15', 'unit': 'шт', 'barcode': '4820001000012',
     'purchase_price': '38000.00', 'markup_percentage': '8.00', 'vat_rate': '20.00', 'category': cat_phones},
    {'code': 'TAB001', 'name': 'Планшет iPad Air 11"', 'unit': 'шт', 'barcode': '4820001000013',
     'purchase_price': '28000.00', 'markup_percentage': '10.00', 'vat_rate': '20.00', 'category': cat_tablets},
    {'code': 'SPK001', 'name': 'Bluetooth колонка JBL Charge 5', 'unit': 'шт', 'barcode': '4820001000014',
     'purchase_price': '3500.00', 'markup_percentage': '22.00', 'vat_rate': '20.00', 'category': cat_audio},
    {'code': 'HP001', 'name': 'Навушники Sony WH-1000XM5', 'unit': 'шт', 'barcode': '4820001000015',
     'purchase_price': '9800.00', 'markup_percentage': '15.00', 'vat_rate': '20.00', 'category': cat_audio},
    {'code': 'THERM001', 'name': 'Термопаста Arctic MX-4', 'unit': 'шт', 'barcode': '4820001000016',
     'purchase_price': '120.00', 'markup_percentage': '60.00', 'vat_rate': '20.00', 'category': cat_components},
    {'code': 'SCRW001', 'name': 'Набір викруток для ноутбуків', 'unit': 'шт', 'barcode': '4820001000017',
     'purchase_price': '280.00', 'markup_percentage': '40.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'USB001', 'name': 'USB-хаб 4 порти 3.0', 'unit': 'шт', 'barcode': '4820001000018',
     'purchase_price': '380.00', 'markup_percentage': '35.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'WC001', 'name': 'Веб-камера Logitech C920', 'unit': 'шт', 'barcode': '4820001000019',
     'purchase_price': '2200.00', 'markup_percentage': '20.00', 'vat_rate': '20.00', 'category': cat_accessories},
    {'code': 'ANTV001', 'name': 'Антивірус ESET 1 рік', 'unit': 'ліц', 'barcode': '4820001000020',
     'purchase_price': '450.00', 'markup_percentage': '30.00', 'vat_rate': '20.00', 'category': cat_software},
]

created_products = []
for data in products_data:
    from decimal import Decimal
    category = data.pop('category', None)
    p, created = Nomenclature.objects.update_or_create(
        code=data['code'],
        defaults={
            'name': data['name'],
            'unit': data['unit'],
            'barcode': data['barcode'],
            'purchase_price': Decimal(data['purchase_price']),
            'markup_percentage': Decimal(data['markup_percentage']),
            'vat_rate': Decimal(data['vat_rate']),
            'type': 'product',
            'category': category,
        }
    )
    created_products.append(p)

print(f"✓ {len(created_products)} товарів створено/знайдено")

# Залишки на складах
stock_data = [
    (wh1, 0, 5), (wh1, 1, 3), (wh1, 2, 8), (wh1, 3, 20), (wh1, 4, 15),
    (wh1, 5, 10), (wh1, 6, 12), (wh1, 7, 25), (wh1, 8, 30), (wh1, 9, 7),
    (wh2, 10, 4), (wh2, 11, 2), (wh2, 12, 3), (wh2, 13, 6), (wh2, 14, 8),
    (wh2, 15, 50), (wh2, 16, 15), (wh2, 17, 20), (wh2, 18, 10), (wh2, 19, 5),
]

for wh, prod_idx, qty in stock_data:
    WarehouseStock.objects.get_or_create(
        warehouse=wh,
        nomenclature=created_products[prod_idx],
        defaults={'quantity': qty}
    )

print("✓ Залишки на складах заповнені")

# Постачальники
supplier1, _ = Supplier.objects.get_or_create(name='Apple Distribution Ukraine', defaults={'phone': '+380441234567'})
supplier2, _ = Supplier.objects.get_or_create(name='Samsung Electronics Ukraine', defaults={'phone': '+380447654321'})
print("✓ Постачальники створені")

# Закупівлі
order1, _ = Order.objects.get_or_create(
    comment_ttn='Закупівля Apple',
    order_type='purchase',
    defaults={
        'supplier': supplier1,
        'user': admin,
        'status': 'draft',
        'total_amount': Decimal('66000.00'),
    }
)
if not order1.items.exists():
    OrderItem.objects.create(order=order1, product=created_products[11], quantity=1, price=Decimal('38000.00'))
    OrderItem.objects.create(order=order1, product=created_products[12], quantity=1, price=Decimal('28000.00'))

order2, _ = Order.objects.get_or_create(
    comment_ttn='Закупівля Samsung',
    order_type='purchase',
    defaults={
        'supplier': supplier2,
        'user': admin,
        'status': 'draft',
        'total_amount': Decimal('22500.00'),
    }
)
if not order2.items.exists():
    OrderItem.objects.create(order=order2, product=created_products[10], quantity=1, price=Decimal('14000.00'))
    OrderItem.objects.create(order=order2, product=created_products[2], quantity=1, price=Decimal('8500.00'))

print("✓ Закупівлі створені")

print()
print("=== Seed завершено успішно ===")
print()
print("Облікові дані для входу:")
print("  Адмін:    admin@erp.com    / admin123")
print("  Продавець: seller@erp.com  / seller123")
