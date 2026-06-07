from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

class CashRegister(models.Model):
    name = models.CharField(max_length=255)
    warehouse = models.ForeignKey(
        'warehouses.Warehouse',
        on_delete=models.CASCADE,
        related_name='cash_registers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Counterparty(models.Model):
    """Єдиний довідник контрагентів (Задача 9).

    Одна людина/компанія може бути водночас покупцем і постачальником (role='both').
    Покупець прив'язується до роздрібного замовлення при частковій оплаті та до ремонту;
    постачальник — до закупівлі.
    """
    ROLE_CHOICES = [
        ('buyer', 'Покупець'),
        ('supplier', 'Постачальник'),
        ('both', 'Обидва'),
    ]
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def mark_role(self, acted_as):
        """B9-1: авто-підвищення ролі до 'both'.

        Якщо контрагент виступив у протилежній до своєї ролі — стає 'both'.
        acted_as: 'buyer' (часткова оплата/ремонт) або 'supplier' (закупівля).
        Повертає True, якщо роль змінено.
        """
        if self.role == 'both':
            return False
        if acted_as == 'supplier' and self.role == 'buyer':
            self.role = 'both'
        elif acted_as == 'buyer' and self.role == 'supplier':
            self.role = 'both'
        else:
            return False
        self.save(update_fields=['role'])
        return True


class Order(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    ORDER_TYPE_CHOICES = [
        ('retail', 'Retail'),
        ('purchase', 'Purchase'),
    ]
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percent'),
        ('amount', 'Amount'),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    # Задача 9: єдиний контрагент. Для retail (часткова оплата) — покупець,
    # для purchase — постачальник. supplier лишаємо для зворотної сумісності.
    counterparty = models.ForeignKey(
        'Counterparty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )
    currency = models.CharField(max_length=3, choices=[('UAH', 'UAH'), ('USD', 'USD'), ('EUR', 'EUR')], default='UAH')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prepay_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    comment_ttn = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} — {self.status}"

    def recalc_total(self):
        """Перераховує total_amount як суму позицій (лише для чернетки).

        Якщо позицій немає — не чіпаємо введену вручну суму, щоб не зламати
        сценарій, де total задається без деталізації по OrderItem.
        """
        if self.status != 'draft':
            return
        agg = self.items.aggregate(
            total=models.Sum(models.F('quantity') * (models.F('price') - models.F('discount_amount')), output_field=models.DecimalField())
        )
        total = agg['total']
        if total is None:
            return
            
        if self.discount_type == 'percent':
            self.discount_amount = (total * (self.discount_value / Decimal('100'))).quantize(Decimal('0.01'))
        elif self.discount_type == 'amount':
            self.discount_amount = self.discount_value
        else:
            self.discount_amount = Decimal('0')
            
        final_total = total - self.discount_amount
        if final_total < 0:
            final_total = Decimal('0')

        self.total_amount = final_total
        self.balance_due = final_total - self.prepay_amount
        self.save(update_fields=['total_amount', 'balance_due', 'discount_amount', 'updated_at'])

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('prepay', 'Передоплата'),
        ('payment', 'Оплата'),
        ('refund', 'Повернення коштів'),
        ('sale', 'Продаж'),
        ('income', 'Внесення'),
        ('expense', 'Видача'),
        ('return', 'Повернення товару'),
        ('debt', 'Борг'),
    ]
    CURRENCY_CHOICES = [
        ('UAH', 'UAH'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='transactions',
        null=True,
        blank=True
    )
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='UAH')
    amount_uah = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    
    # --- New fields for Debt tracking ---
    status = models.CharField(max_length=20, choices=[('completed', 'Виконано'), ('pending', 'Очікує оплати')], default='completed')
    counterparty = models.ForeignKey(
        'Counterparty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    service_job = models.ForeignKey(
        'warehouses.ServiceJob',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='transactions'
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} — {self.amount} {self.currency}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Nomenclature',
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=12, decimal_places=2)
    
    discount_type = models.CharField(max_length=10, choices=Order.DISCOUNT_TYPE_CHOICES, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'


class ExchangeRate(models.Model):
    currency = models.CharField(max_length=3, unique=True)
    rate_to_uah = models.DecimalField(max_digits=10, decimal_places=4)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return f"{self.currency}: {self.rate_to_uah}"


@receiver([post_save, post_delete], sender=OrderItem)
def _recalc_order_total_on_item_change(sender, instance, **kwargs):
    """Тримає total_amount замовлення синхронним із сумою позицій.

    filter().first() замість instance.order — щоб не впасти на каскадному
    видаленні замовлення, коли сам Order вже видалено.
    """
    order = Order.objects.filter(pk=instance.order_id).first()
    if order is not None:
        order.recalc_total()
