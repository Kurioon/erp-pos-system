from django.contrib import admin

from .models import Nomenclature, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'parent')
    search_fields = ('name',)


@admin.register(Nomenclature)
class NomenclatureAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'unit', 'purchase_price', 'sale_price', 'wholesale_price', 'markup_percentage', 'is_archived')
    list_filter = ('unit', 'category', 'is_archived')
    search_fields = ('code', 'name', 'barcode', 'manufactured')
    readonly_fields = ('created_at', 'updated_at')
