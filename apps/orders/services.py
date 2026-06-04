from decimal import Decimal
from django.db import transaction
from .models import Order, Transaction, ExchangeRate
from warehouses.services import add_stock, remove_stock


ALLOWED_TRANSITIONS = {
    'draft': ['partial', 'paid', 'cancelled'],
    'partial': ['paid', 'cancelled'],
    'paid': ['returned'],
    'cancelled': [],
    'returned': [],
}


def _validate_transition(order: Order, new_status: str):
    allowed = ALLOWED_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Неможливо перевести замовлення зі статусу '{order.status}' в '{new_status}'."
        )


def _convert_to_uah(amount: Decimal, currency: str) -> Decimal:
    """BUG-01 — конвертація суми в UAH через ExchangeRate"""
    if currency == 'UAH':
        return amount
    try:
        rate = ExchangeRate.objects.get(currency=currency)
        return amount * rate.rate_to_uah
    except ExchangeRate.DoesNotExist:
        raise ValueError(f'Курс валюти {currency} не знайдено. Зверніться до адміністратора.')


@transaction.atomic
def process_prepay(order: Order, amount: Decimal, currency: str, cash_register, user) -> Transaction:
    if order.status not in ('draft', 'partial'):
        raise ValueError(f"Неможливо прийняти оплату для замовлення зі статусом '{order.status}'.")

    if amount <= 0:
        raise ValueError('Сума оплати має бути більшою за нуль.')

    # BUG-01 — конвертуємо в UAH перед розрахунком
    amount_uah = _convert_to_uah(amount, currency)

    if amount_uah > order.balance_due:
        raise ValueError(f'Сума перевищує залишок боргу: {order.balance_due}.')

    is_first_payment = order.status == 'draft'

    t = Transaction.objects.create(
        order=order,
        cash_register=cash_register,
        user=user,
        amount=amount,
        currency=currency,
        transaction_type='prepay',
    )

    order.prepay_amount += amount_uah
    order.balance_due = order.total_amount - order.prepay_amount

    if order.balance_due <= 0:
        order.balance_due = Decimal('0.00')
        order.status = 'paid'
    else:
        order.status = 'partial'

    if is_first_payment:
        _deduct_order_items(order)

    order.save()
    return t


@transaction.atomic
def process_payment(order: Order, amount: Decimal, currency: str, cash_register, user) -> Transaction:
    _validate_transition(order, 'paid')

    # BUG-01 — конвертуємо в UAH
    amount_uah = _convert_to_uah(amount, currency)

    t = Transaction.objects.create(
        order=order,
        cash_register=cash_register,
        user=user,
        amount=amount,
        currency=currency,
        transaction_type='payment',
    )

    order.prepay_amount += amount_uah
    order.balance_due = order.total_amount - order.prepay_amount

    if order.balance_due <= 0:
        order.balance_due = Decimal('0.00')
        order.status = 'paid'

    order.save()
    return t


@transaction.atomic
def process_cancellation(order: Order, currency: str, cash_register, user):
    _validate_transition(order, 'cancelled')

    t = None

    if order.prepay_amount > 0:
        t = Transaction.objects.create(
            order=order,
            cash_register=cash_register,
            user=user,
            amount=order.prepay_amount,
            currency=currency,
            transaction_type='refund',
        )
        _return_order_items(order)

    order.status = 'cancelled'
    order.balance_due = Decimal('0.00')
    order.prepay_amount = Decimal('0.00')
    order.save()

    return t


@transaction.atomic
def process_refund(order: Order, currency: str, cash_register, user) -> Transaction:
    _validate_transition(order, 'returned')

    t = Transaction.objects.create(
        order=order,
        cash_register=cash_register,
        user=user,
        amount=order.prepay_amount,
        currency=currency,
        transaction_type='refund',
    )

    _return_order_items(order)

    order.status = 'returned'
    order.balance_due = Decimal('0.00')
    order.prepay_amount = Decimal('0.00')
    order.save()

    return t


def _deduct_order_items(order: Order):
    for item in order.items.all():
        remove_stock(warehouse=order.cash_register.warehouse, nomenclature=item.product, quantity=item.quantity)


def _return_order_items(order: Order):
    for item in order.items.all():
        add_stock(warehouse=order.cash_register.warehouse, nomenclature=item.product, quantity=item.quantity)