from django.db import models


class Nomenclature(models.Model):
    # Base fields
    # code, name, unit_id
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, default='шт')
    
    # Description fields
    # description, barcode, manufactured
    description = models.TextField(blank=True, null=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    manufactured = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial fields
    # purchase_price, sale_price, vat_rate
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # State fields
    # is_active, created_at, updated_at
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Номенклатура'
        verbose_name_plural = 'Номенклатури'

    def __str__(self):
        return f'{self.code} - {self.name}'
