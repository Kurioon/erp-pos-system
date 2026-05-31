from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, ServiceJobViewSet, WarehouseStockViewSet

# DRF Router автоматично генерує маршрути для CRUD операцій
router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'service-jobs', ServiceJobViewSet, basename='service-job')
router.register(r'warehouse-stocks', WarehouseStockViewSet, basename='warehouse-stock')

urlpatterns = [
    path('', include(router.urls)),
]