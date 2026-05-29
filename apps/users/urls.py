from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserMeView

app_name = 'users'

urlpatterns = [
    # Ендпоінт для логіну (отримання токенів)
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # Ендпоінт для оновлення протухлого токена
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Ендпоінт для отримання даних авторизованого користувача (Ім'я, роль)
    path('me/', UserMeView.as_view(), name='user_me'),
]