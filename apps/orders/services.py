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


def _to_uah(amount: Decimal, currency: str) -> Decimal:
    """Конвертує суму у гривні за поточним курсом ExchangeRate.

    Облік замовлень (total_amount, prepay_amount, balance_due) ведеться в UAH,
    тому будь-яку оплату в іншій валюті треба привести до гривні.
    """
    if not currency or currency == 'UAH':
        return amount
    try:
        rate = ExchangeRate.objects.get(currency=currency).rate_to_uah
    except ExchangeRate.DoesNotExist:
        raise ValueError(f"Немає курсу для валюти '{currency}'. Спершу оновіть курси валют.")
    return (amount * rate).quantize(Decimal('0.01'))


@transaction.atomic
def process_prepay(order: Order, amount: Decimal, currency: str, cash_register, user) -> Transaction:
    if order.status not in ('draft', 'partial'):
        raise ValueError(f"Неможливо прийняти оплату для замовлення зі статусом '{order.status}'.")

    if amount <= 0:
        raise ValueError('Сума оплати має бути більшою за нуль.')

    # Сума оплати може бути в USD/EUR — приводимо до гривні для обліку боргу
    amount_uah = _to_uah(amount, currency)

    if amount_uah > order.balance_due:
        raise ValueError(f'Сума перевищує залишок боргу: {order.balance_due} грн.')

    is_first_payment = order.status == 'draft'

    # Transaction зберігає фактичну валюту та суму оплати (як пройшло через касу)
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
def process_cancellation(order: Order, currency: str, cash_register, user):
    _validate_transition(order, 'cancelled')

    t = None

    if order.prepay_amount > 0:
        # prepay_amount накопичено в гривні, тому повернення фіксуємо в UAH
        t = Transaction.objects.create(
            order=order,
            cash_register=cash_register,
            user=user,
            amount=order.prepay_amount,
            currency='UAH',
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

    # prepay_amount накопичено в гривні, тому повернення фіксуємо в UAH
    # (параметр currency лишено для сумісності виклику з view).
    t = Transaction.objects.create(
        order=order,
        cash_register=cash_register,
        user=user,
        amount=order.prepay_amount,
        currency='UAH',
        transaction_type='refund',
    )

    _return_order_items(order)

    order.status = 'returned'
    order.balance_due = Decimal('0.00')
    order.prepay_amount = Decimal('0.00')
    order.save()

    return t


@transaction.atomic
def process_receive(order: Order, warehouse, user) -> Order:
    """Оприходування закупівлі: товар надходить на вказаний склад.

    Закупівля не прив'язана до каси/складу, тому склад призначення
    передається явно. Після оприходування статус стає 'paid' (оброблено).
    """
    if order.order_type != 'purchase':
        raise ValueError('Оприходувати можна лише замовлення-закупівлі (purchase).')
    if order.status != 'draft':
        raise ValueError(f"Оприходувати можна лише чернетку. Поточний статус: '{order.status}'.")
    if not order.items.exists():
        raise ValueError('У закупівлі немає позицій для оприходування.')

    for item in order.items.all():
        add_stock(
            warehouse=warehouse,
            nomenclature=item.product,
            quantity=item.quantity,
            reason='purchase',
            order=order,
        )

    order.status = 'paid'
    order.balance_due = Decimal('0.00')
    order.save()
    return order


def _deduct_order_items(order: Order):
    for item in order.items.all():
        if order.order_type == 'retail':
            # Для продажу клієнту — списуємо товар
            remove_stock(
                warehouse=order.cash_register.warehouse,
                nomenclature=item.product,
                quantity=item.quantity,
                reason='sale',
                order=order,
            )
        elif order.order_type == 'purchase':
            # Для закупівлі у постачальника — ДОДАЄМО товар на склад
            add_stock(
                warehouse=order.cash_register.warehouse,
                nomenclature=item.product,
                quantity=item.quantity,
                reason='purchase',
                order=order,
            )


def _return_order_items(order: Order):
    for item in order.items.all():
        if order.order_type == 'retail':
            # Клієнт повернув товар — додаємо назад на склад
            add_stock(
                warehouse=order.cash_register.warehouse,
                nomenclature=item.product,
                quantity=item.quantity,
                reason='return',
                order=order,
            )
        elif order.order_type == 'purchase':
            # Повернення браку постачальнику — списуємо зі складу
            remove_stock(
                warehouse=order.cash_register.warehouse,
                nomenclature=item.product,
                quantity=item.quantity,
                reason='return_to_supplier',
                order=order,
            )