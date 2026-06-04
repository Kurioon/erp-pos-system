from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    """
    Кастомний менеджер користувачів, який використовує email як унікальний ідентифікатор
    замість стандартного username.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email є обов\'язковим полем')
        email = self.normalize_email(email)
        
        # Автоматично генеруємо username з email для сумісності з БД
        if 'username' not in extra_fields:
            extra_fields['username'] = email

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперкористувач повинен мати is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперкористувач повинен мати is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Адміністратор'),
        ('seller', 'Продавець'),
    ]
    
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='seller')
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name'] 

    # ПІДКЛЮЧАЄМО НАШ НОВИЙ МЕНЕДЖЕР
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"