from django.urls import path
from rest_framework_simplejwt.views import  TokenRefreshView
from .views import CustomTokenObtainPairView, UserMeView

app_name = 'users'

urlpatterns = [
    # Ендпоінт для логіну (отримання токенів)
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),          # -> /api/auth/login/
    # Ендпоінт для оновлення протухлого токена
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),        # -> /api/auth/refresh/
    # Ендпоінт для отримання даних авторизованого користувача (Ім'я, роль)
    path('me/', UserMeView.as_view(), name='user_me'),                          # -> /api/auth/me/
]