from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    # parent — закладено під ієрархію (дерево категорій реалізуємо пізніше)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'

    def __str__(self):
        return self.name

TYPE_CHOICES = (
    ('product', 'Товар'),
    ('service', 'Послуга'),
)

CURRENCY_CHOICES = [
    ('UAH', 'UAH'),
    ('USD', 'USD'),
    ('EUR', 'EUR'),
]


class Nomenclature(models.Model):
    # Base fields
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='product')
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, default='шт')
    image = CloudinaryField('image', blank=True, null=True)

    # Description fields
    description = models.TextField(blank=True, null=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    manufactured = models.CharField(max_length=100, blank=True, null=True)
    # Категорія/тип товару (Телефон, Ноутбук, Чохол…). Необов'язкова.
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
    )

    # --- Мультивалютна ціна (Задача 3) ---
    # Введена сума у вибраній валюті (base_currency). null — для старих товарів.
    base_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    # Валюта введеної ціни. UAH — фіксована, USD/EUR — плаває за курсом.
    base_currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOICES, default='USD'
    )

    # Financial fields
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message='Ціна не може бути меншою або дорівнювати 0')]
    )
    markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    # sale_price — збережений снепшот price_uah (для сумісності з POS).
    # Оновлюється при кожному save() якщо base_price заданий.
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'), message='Ціна не може бути меншою або дорівнювати 0')]
    )
    # Оптова ціна — заповнюється/редагується вручну (без авторозрахунку)
    wholesale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'), message='Ціна не може бути меншою або дорівнювати 0')]
    )
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # State fields
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Номенклатура'
        verbose_name_plural = 'Номенклатури'

    def __str__(self):
        return f'{self.code} - {self.name}'

    # ------------------------------------------------------------------
    # Мультивалютний хелпер (Задача 3)
    # ------------------------------------------------------------------
    def get_price_uah(self, rates: dict) -> Decimal:
        """
        Повертає ціну товару в гривні динамічно.
        rates = {'USD': Decimal('40.00'), 'EUR': Decimal('43.00')}

        UAH  → base_price (фіксована, не залежить від курсу)
        USD/EUR → round(base_price × rate, 2)
        Якщо base_price не заданий → повертає збережений sale_price (fallback)
        """
        if not self.base_price:
            return self.sale_price or Decimal('0')
        if self.base_currency == 'UAH':
            return self.base_price
        rate = rates.get(self.base_currency)
        if rate is None:
            raise ValueError(f'Немає курсу для валюти {self.base_currency}')
        return (self.base_price * rate).quantize(Decimal('0.01'))

    def clean(self):
        if self.purchase_price is not None and self.purchase_price <= Decimal('0.00'):
            raise ValidationError({'purchase_price': 'Ціна не може бути меншою або дорівнювати 0'})
        if self.sale_price is not None and self.sale_price <= Decimal('0.00'):
            raise ValidationError({'sale_price': 'Ціна не може бути меншою або дорівнювати 0'})
        if self.wholesale_price is not None and self.wholesale_price <= Decimal('0.00'):
            raise ValidationError({'wholesale_price': 'Ціна не може бути меншою або дорівнювати 0'})
        if self.base_price is not None and self.base_price <= Decimal('0.00'):
            raise ValidationError({'base_price': 'base_price має бути більше 0'})

    def save(self, *args, **kwargs):
        # --- Якщо задано base_price: sale_price синхронізується з price_uah ---
        # markup_percentage НЕ перебиває sale_price коли є base_price
        if self.base_price and self.base_price > 0:
            try:
                from orders.models import ExchangeRate
                rates = {r.currency: r.rate_to_uah for r in ExchangeRate.objects.all()}
                self.sale_price = self.get_price_uah(rates)
            except Exception:
                # Якщо курс недоступний при збереженні — лишаємо поточний sale_price
                pass
            super().save(*args, **kwargs)
            return

        # --- Стара логіка (без base_price) ---
        if self.purchase_price is None or self.purchase_price <= 0:
            super().save(*args, **kwargs)
            return

        if self.pk:
            try:
                old = Nomenclature.objects.get(pk=self.pk)

                if self.sale_price and self.sale_price > 0 and old.sale_price != self.sale_price:
                    # Адмін вручну змінив sale_price → перераховуємо markup_percentage
                    self.markup_percentage = (
                        (self.sale_price / self.purchase_price - Decimal('1.00'))
                        * Decimal('100.00')
                    ).quantize(Decimal('0.01'))

                elif (old.purchase_price != self.purchase_price
                      or old.markup_percentage != self.markup_percentage
                      or not self.sale_price):
                    # Змінився purchase_price або markup → перераховуємо sale_price
                    self.sale_price = (
                        self.purchase_price
                        * (Decimal('1.00') + self.markup_percentage / Decimal('100.00'))
                    ).quantize(Decimal('0.01'))

            except Nomenclature.DoesNotExist:
                self.sale_price = (
                    self.purchase_price
                    * (Decimal('1.00') + self.markup_percentage / Decimal('100.00'))
                ).quantize(Decimal('0.01'))
        else:
            # Новий товар без base_price — рахуємо sale_price з markup
            self.sale_price = (
                self.purchase_price
                * (Decimal('1.00') + self.markup_percentage / Decimal('100.00'))
            ).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

