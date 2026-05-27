from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceJobViewSet

# DRF Router автоматично генерує маршрути для GET, POST, PATCH, DELETE
router = DefaultRouter()
router.register(r'service-jobs', ServiceJobViewSet, basename='service-job')

urlpatterns = [
    path('', include(router.urls)),
]