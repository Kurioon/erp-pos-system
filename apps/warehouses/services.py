from django.db import transaction
from .models import StockMovement, WarehouseStock

@transaction.atomic
def add_stock(warehouse, nomenclature, quantity: int):
    if quantity <= 0:
        raise ValueError("Кількість для додавання має бути більшою за нуль.")
    
    stock, _ = WarehouseStock.objects.get_or_create(
        warehouse=warehouse,
        nomenclature=nomenclature,
        defaults={'quantity': 0, 'is_archived': False}
    )
    stock.is_archived = False
    stock.quantity += quantity
    stock.save()

    quantity_before = stock.quantity
    stock.quantity -= quantity
    stock.save()

    # Записуємо історію руху
    StockMovement.objects.create(
        warehouse=warehouse,
        nomenclature=nomenclature,
        quantity_change=-quantity,
        quantity_before=quantity_before,
        quantity_after=stock.quantity,
        reason='sale',
        order=order
    )
    
    return stock

@transaction.atomic
def remove_stock(warehouse, nomenclature, quantity: int):
    if quantity <= 0:
        raise ValueError("Кількість для списання має бути більшою за нуль.")
    
    # ДОДАНО select_for_update(): 
    # Блокує цей конкретний рядок у базі даних до кінця транзакції. 
    # Якщо два касири одночасно спробують продати останній товар, 
    # другий зачекає, поки перший не завершить дію, і отримає помилку нестачі.
    stock = WarehouseStock.objects.select_for_update().filter(
        warehouse=warehouse, 
        nomenclature=nomenclature,
        is_archived=False
    ).first()
    
    if not stock:
        raise ValueError("Цього товару немає на вказаному складі.")
    
    if stock.quantity < quantity:
        raise ValueError(f"Недостатньо товару. В наявності лише: {stock.quantity} шт.")
    
    stock.quantity -= quantity
    stock.save()

    quantity_before = stock.quantity
    stock.quantity += quantity
    stock.save()

    # Записуємо історію руху
    StockMovement.objects.create(
        warehouse=warehouse,
        nomenclature=nomenclature,
        quantity_change=quantity,
        quantity_before=quantity_before,
        quantity_after=stock.quantity,
        reason='purchase'
    )
    
    return stock