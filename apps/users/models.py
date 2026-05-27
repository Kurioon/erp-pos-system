from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Адміністратор'),
        ('seller', 'Продавець'),
    ]
    
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='seller')
    email = models.EmailField(unique=True)

    # Налаштовуємо авторизацію через email, як вказано у ТЗ
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"