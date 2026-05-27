from django.db import models
from django.db.models import Q, UniqueConstraint
from django.core.validators import RegexValidator, MinLengthValidator

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ServiceJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Очікує'),
        ('in_progress', 'В роботі'),
        ('done', 'Готово'),
        ('returned', 'Видано клієнту'),
    ]
    
    # Створюємо правило для номера телефону (тільки цифри та опціональний + на початку)
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефону має бути у форматі: '+380991234567'. До 15 цифр."
    )

    customer_name = models.CharField(max_length=255)
    # Застосовуємо валідатор до поля
    customer_phone = models.CharField(max_length=20, validators=[phone_validator])
    device_name = models.CharField(max_length=255)
    # Додаємо мінімальну довжину опису (щоб не писали просто "1")
    description = models.TextField(validators=[MinLengthValidator(5)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    storage_cell = models.CharField(max_length=10)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['storage_cell'],
                condition=Q(status__in=['pending', 'in_progress']),
                name='unique_active_cell'
            )
        ]

    def __str__(self):
        return f"Ремонт #{self.id} - {self.device_name} (Комірка: {self.storage_cell})"