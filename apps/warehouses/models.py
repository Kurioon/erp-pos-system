from django.db import models
from django.db.models import Q, UniqueConstraint
from django.core.validators import RegexValidator, MinLengthValidator
from cloudinary.models import CloudinaryField

class Warehouse(models.Model):
    """Модель для зберігання інформації про фізичні склади."""
    name = models.CharField(max_length=255)
    
    # Додано згідно з ТЗ: поле для фізичної адреси складу
    address = models.TextField(blank=True, null=True)
    
    # Прапорець для "м'якого видалення" (щоб не видаляти записи з БД назавжди)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ServiceJob(models.Model):
    """Модель для відстеження пристроїв, які клієнти здають у ремонт."""
    STATUS_CHOICES = [
        ('pending', 'Прийнято'),
        ('waiting_parts', 'Очікує компонентів'),
        ('done', 'Відремонтовано'),
        ('returned', 'Видано'), # При цьому статусі storage_cell має ставати null
    ]
    
    # Створюємо правило для номера телефону (тільки цифри та опціональний + на початку)
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефону має бути у форматі: '+380991234567'. До 15 цифр."
    )

    # Дані клієнта та пристрою
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, validators=[phone_validator])
    device_name = models.CharField(max_length=255)
    description = models.TextField(validators=[MinLengthValidator(5)])
    
    # ДОДАНО згідно з US-06: Текстовий коментар або номер ТТН (необов'язкове поле)
    comment = models.TextField(blank=True, null=True)
    
    # ДОДАНО: Фото ремонту через Cloudinary (зберігається в хмарі, а не на сервері)
    photo = CloudinaryField('image', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Коли ремонт видано (returned), ми можемо очистити це поле, звільнивши фізичну комірку.
    storage_cell = models.CharField(max_length=10, null=True, blank=True)

    is_archived = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Обмеження на рівні БД: не можна покласти два пристрої в одну комірку, 
            # якщо хоча б один з них активний (pending або waiting_parts) і не в архіві.
            UniqueConstraint(
                fields=['storage_cell'],
                condition=Q(status__in=['pending', 'waiting_parts']) & Q(is_archived=False),
                name='unique_active_cell'
            )
        ]

    def __str__(self):
        # Оновлено для красивого виводу: якщо storage_cell порожнє (null), пишемо "Не призначена"
        cell = self.storage_cell if self.storage_cell else "Не призначена"
        return f"Ремонт #{self.id} - {self.device_name} (Комірка: {cell})"


class WarehouseStock(models.Model):
    """Модель для ведення залишків товарів (номенклатури) на конкретних складах."""
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    
    # Зв'язок із моделлю товарів (PROTECT гарантує, що товар не видалять, поки він є на складі)
    nomenclature = models.ForeignKey('products.Nomenclature', on_delete=models.PROTECT, related_name='warehouse_stocks')
    
    # Поточна кількість товару на цьому складі
    quantity = models.IntegerField(default=0)

    is_archived = models.BooleanField(default=False)

    class Meta:
        # Унікальний індекс: один і той самий товар не може дублюватися рядками на одному складі
        unique_together = ('warehouse', 'nomenclature')

    def __str__(self):
        return f"Склад {self.warehouse.name} | Товар: {self.nomenclature.name} | Залишок: {self.quantity} шт."