from django.db import transaction
from .models import WarehouseStock

@transaction.atomic
def add_stock(warehouse, nomenclature, quantity: int):
    if quantity <= 0:
        raise ValueError("Кількість для додавання має бути більшою за нуль.")
    
    # ВИПРАВЛЕНО: Додано фільтр is_archived=False перед get_or_create
    stock, created = WarehouseStock.objects.filter(is_archived=False).get_or_create(
        warehouse=warehouse, 
        nomenclature=nomenclature,
        defaults={'quantity': 0}
    )
    
    stock.quantity += quantity
    stock.save()
    
    return stock

@transaction.atomic
def remove_stock(warehouse, nomenclature, quantity: int):
    if quantity <= 0:
        raise ValueError("Кількість для списання має бути більшою за нуль.")
    
    # ВИПРАВЛЕНО: Додано is_archived=False до фільтра
    stock = WarehouseStock.objects.filter(
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
    
    return stock