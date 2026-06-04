from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F


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


class Order(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    ORDER_TYPE_CHOICES = [
        ('retail', 'Retail'),
        ('purchase', 'Purchase'),
    ]

    supplier = models.ForeignKey(
        Supplier,
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prepay_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comment_ttn = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} — {self.status}"


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('prepay', 'Передоплата'),
        ('payment', 'Оплата'),
        ('refund', 'Повернення коштів'),
        ('sale', 'Продаж'),
        ('income', 'Внесення'),
        ('expense', 'Видача'),
        ('return', 'Повернення товару'),
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
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
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
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)

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


# BUG-06 — сигнал для перерахунку total_amount при зміні OrderItem
@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    order = instance.order
    total = order.items.aggregate(
        total=Sum(F('quantity') * F('price'))
    )['total'] or Decimal('0.00')
    order.total_amount = total
    order.balance_due = total - order.prepay_amount
    Order.objects.filter(pk=order.pk).update(
        total_amount=total,
        balance_due=order.balance_due
    )