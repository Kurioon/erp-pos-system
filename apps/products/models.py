from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Nomenclature(models.Model):
    # Base fields
    # code, name, unit_id
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, default='шт')
    image = CloudinaryField('image', blank=True, null=True)
    
    # Description fields
    # description, barcode, manufactured
    description = models.TextField(blank=True, null=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    manufactured = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial fields
    # purchase_price, sale_price, vat_rate
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message='Ціна не може бути меншою або дорівнювати 0')]
    )
    markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'), message='Ціна не може бути меншою або дорівнювати 0')]
    )
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # State fields
    # is_archived, created_at, updated_at
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Номенклатура'
        verbose_name_plural = 'Номенклатури'

    def __str__(self):
        return f'{self.code} - {self.name}'

    def clean(self):
        if self.purchase_price is not None and self.purchase_price <= Decimal('0.00'):
            raise ValidationError({'purchase_price': 'Ціна не може бути меншою або дорівнювати 0'})
        if self.sale_price is not None and self.sale_price <= Decimal('0.00'):
            raise ValidationError({'sale_price': 'Ціна не може бути меншою або дорівнювати 0'})

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.purchase_price is not None and self.sale_price is not None and self.sale_price != Decimal('0.00'):
            self.markup_percentage = (
                (self.sale_price / self.purchase_price - Decimal('1.00'))
                * Decimal('100.00')
            ).quantize(Decimal('0.01'))
        elif self.purchase_price is not None and (self.sale_price is None or self.sale_price == Decimal('0.00')):
            self.sale_price = (self.purchase_price * (Decimal('1.00') + self.markup_percentage / Decimal('100.00'))).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
