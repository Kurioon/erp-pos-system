from decimal import Decimal
from .models import Order, Transaction
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


def process_prepay(order: Order, amount: Decimal, currency: str, cash_register, user) -> Transaction:
    _validate_transition(order, 'partial')

    if amount > order.total_amount:
        raise ValueError('Передоплата не може перевищувати загальну суму замовлення.')

    transaction = Transaction.objects.create(
        order=order,
        cash_register=cash_register,
        user=user,
        amount=amount,
        currency=currency,
        transaction_type='prepay',
    )

    order.prepay_amount = amount
    order.balance_due = order.total_amount - amount

    if order.balance_due <= 0:
        order.balance_due = Decimal('0.00')
        order.status = 'paid'
        _deduct_order_items(order)
    else:
        order.status = 'partial'

    order.sa