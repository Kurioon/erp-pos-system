from django.contrib import admin
from .models import CashRegister, Order, Transaction


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'warehouse_name', 'created_at')
    search_fields = ('name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'order_type', 'total_amount', 'prepay_amount', 'balance_due', 'created_at')
    list_filter = ('status', 'order_type')
    search_fields = ('id', 'comment_ttn')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'cash_register', 'transaction_type', 'amount', 'currency', 'timestamp')
    list_filter = ('transaction_type', 'currency')
    search_fields = ('order__id',)