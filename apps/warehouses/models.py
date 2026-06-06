from django.db import models
from django.db.models import Q, UniqueConstraint
from django.core.validators import RegexValidator, MinLengthValidator
from cloudinary.models import CloudinaryField

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    # Додано згідно з ТЗ: поле для фізичної адреси складу
    address = models.TextField(blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ServiceJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Прийнято'),
        ('waiting_parts', 'Очікує компонентів'),
        ('done', 'Відремонтовано'),
        ('returned', 'Видано'),
    ]
    
    # Створюємо правило для номера телефону (тільки цифри та опціональний + на початку)
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефону має бути у форматі: '+380991234567'. До 15 цифр."
    )

    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, validators=[phone_validator])
    device_name = models.CharField(max_length=255)
    description = models.TextField(validators=[MinLengthValidator(5)])
    
    # ДОДАНО згідно з US-06: Текстовий коментар або номер ТТН (необов'язкове поле)
    comment = models.TextField(blank=True, null=True)
    
    # ДОДАНО: Фото ремонту через Cloudinary
    photo = CloudinaryField('image', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    storage_cell = models.CharField(max_length=10, null=True, blank=True)

    is_archived = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['storage_cell'],
                condition=Q(status__in=['pending', 'waiting_parts']) & Q(is_archived=False),
                name='unique_active_cell'
            )
        ]

    def __str__(self):
        cell = self.storage_cell if self.storage_cell else "Не призначена"
        return f"Ремонт #{self.id} - {self.device_name} (Комірка: {cell})"

class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    
    # Зв'язок із моделлю товарів 
    nomenclature = models.ForeignKey('products.Nomenclature', on_delete=models.PROTECT, related_name='warehouse_stocks')
    
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)

    is_archived = models.BooleanField(default=False)

    class Meta:
        unique_together = ('warehouse', 'nomenclature')

    def __str__(self):
        return f"Склад {self.warehouse.name} | Товар: {self.nomenclature.name} | Залишок: {self.quantity} шт."
    
class StockMovement(models.Model):
    REASON_CHOICES = [
        ('sale', 'Продаж'),
        ('purchase', 'Закупівля'),
        ('return', 'Повернення'),
        ('correction', 'Коригування'),
        ('transfer', 'Переміщення'),
    ]

    warehouse = models.ForeignKey('Warehouse', on_delete=models.CASCADE, related_name='movements')
    nomenclature = models.ForeignKey('products.Nomenclature', on_delete=models.PROTECT, related_name='movements')
    quantity_change = models.IntegerField()  # додатне = прихід, від'ємне = витрата
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Для переміщень між складами зберігаємо другий склад (звідки або куди)
    transfer_warehouse = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='transfer_movements')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.warehouse} | {self.nomenclature} | {self.quantity_change} ({self.reason})"