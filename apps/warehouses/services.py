from django.db import transaction
from .models import StockMovement, WarehouseStock


@transaction.atomic
def add_stock(warehouse, nomenclature, quantity: int, reason='return', order=None, transfer_warehouse=None):
    if quantity <= 0:
        raise ValueError("Кількість для додавання має бути більшою за нуль.")

    stock, _ = WarehouseStock.objects.get_or_create(
        warehouse=warehouse,
        nomenclature=nomenclature,
        defaults={'quantity': 0, 'is_archived': False}
    )
    stock.is_archived = False

    quantity_before = stock.quantity
    stock.quantity += quantity
    stock.save()

    StockMovement.objects.create(
        warehouse=warehouse,
        nomenclature=nomenclature,
        quantity_change=quantity,
        quantity_before=quantity_before,
        quantity_after=stock.quantity,
        reason=reason,
        order=order,
        transfer_warehouse=transfer_warehouse
    )

    return stock


@transaction.atomic
def remove_stock(warehouse, nomenclature, quantity: int, reason='sale', order=None, transfer_warehouse=None):
    if quantity <= 0:
        raise ValueError("Кількість для списання має бути більшою за нуль.")

    # select_for_update блокує рядок до кінця транзакції —
    # захист від race condition при одночасному продажу одного товару.
    stock = WarehouseStock.objects.select_for_update().filter(
        warehouse=warehouse,
        nomenclature=nomenclature,
        is_archived=False
    ).first()

    if not stock:
        raise ValueError("Цього товару немає на вказаному складі.")

    if stock.quantity < quantity:
        raise ValueError(f"Недостатньо товару. В наявності лише: {stock.quantity} шт.")

    quantity_before = stock.quantity
    stock.quantity -= quantity
    stock.save()

    StockMovement.objects.create(
        warehouse=warehouse,
        nomenclature=nomenclature,
        quantity_change=-quantity,
        quantity_before=quantity_before,
        quantity_after=stock.quantity,
        reason=reason,
        order=order,
        transfer_warehouse=transfer_warehouse
    )

    return stock
