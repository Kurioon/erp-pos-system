from django.contrib import admin
from .models import Warehouse, ServiceJob, WarehouseStock

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'is_archived', 'created_at')
    list_filter = ('is_archived', 'created_at')
    search_fields = ('name', 'address')

@admin.register(ServiceJob)
class ServiceJobAdmin(admin.ModelAdmin):
    # ВИПРАВЛЕНО: Додано is_archived
    list_display = ('id', 'customer_name', 'device_name', 'status', 'storage_cell', 'is_archived', 'created_at')
    list_filter = ('status', 'is_archived', 'created_at')
    search_fields = ('customer_name', 'customer_phone', 'device_name', 'storage_cell')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    # ВИПРАВЛЕНО: Додано is_archived
    list_display = ('warehouse', 'nomenclature', 'quantity', 'is_archived')
    list_filter = ('warehouse', 'is_archived')
    search_fields = ('nomenclature__name', 'nomenclature__code')