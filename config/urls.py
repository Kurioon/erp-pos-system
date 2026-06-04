"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from users.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),

    # Health-check для Uptime Robot (без авторизації) -> /api/health/
    path('api/health/', health_check, name='health_check'),

    path('api/auth/', include('users.urls', namespace='auth')),

    # Підключаємо твої маршрути під префіксом /api/
    path('api/', include('orders.urls')),
    path('api/', include('warehouses.urls')),
    path('api/', include('products.urls')),
    path('api/', include('activity_log.urls')),
        # --- ЕНДПОІНТИ ДЛЯ ДОКУМЕНТАЦІЇ ---
    
    # 1. Цей шлях генерує саму схему у форматі YAML/JSON (його читає комп'ютер)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # 2. Цей шлях малює красивий інтерфейс Swagger (його читають люди)
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
