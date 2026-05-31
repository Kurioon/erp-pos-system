from django.contrib import admin

from .models import Nomenclature


@admin.register(Nomenclature)
class NomenclatureAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'unit', 'purchase_price', 'sale_price', 'markup_percentage', 'is_archived')
    list_filter = ('unit', 'is_archived')
    search_fields = ('code', 'name', 'barcode', 'manufactured')
    readonly_fields = ('created_at', 'updated_at')
