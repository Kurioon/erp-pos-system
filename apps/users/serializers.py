from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'role')

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Стандартна валідація simplejwt перевіряє пароль та email
        data = super().validate(attrs)
        
        # Перейменовуємо ключі під очікуваний формат фронтенду
        data['access_token'] = data.pop('access')
        data['refresh_token'] = data.pop('refresh')
        
        # Додаємо дані користувача в тіло відповіді
        data['user'] = UserSerializer(self.user).data
        
        return data