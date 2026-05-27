from django.db import models

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
    
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20)
    device_name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    storage_cell = models.CharField(max_length=10)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ремонт #{self.id} - {self.device_name} (Комірка: {self.storage_cell})"