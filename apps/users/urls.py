from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = 'users'

urlpatterns = [
    # Ендпоінт для логіну (отримання токенів)
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # Ендпоінт для оновлення протухлого токена
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]