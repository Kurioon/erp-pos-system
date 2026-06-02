from django.urls import path
from .views import (
    CashRegisterListCreateView,
    CashRegisterDetailView,
    GlobalCashboxAnalyticsView,
    OrderListCreateView,
    OrderDetailView,
    OrderItemListCreateView,
    OrderItemDetailView,
    TransactionListCreateView,
    TransactionDetailView,
    OrderExportCSVView,
    TransactionExportCSVView,
    OrderExportPDFView,
    OrderRefundView,
    OrderPrepayView,
    OrderReceiptPDFView,
    ExchangeRateListView,       # Новий імпорт
    ExchangeRateUpdateView      # Новий імпорт
)

urlpatterns = [
    # Каси
    path('cash-registers/', CashRegisterListCreateView.as_view(), name='cashregister-list'),
    path('cash-registers/<int:pk>/', CashRegisterDetailView.as_view(), name='cashregister-detail'),
    path('cash-registers/analytics/', GlobalCashboxAnalyticsView.as_view(), name='cashregister-analytics'),

    # Курси валют (ЗАДАЧА 3)
    path('exchange-rates/', ExchangeRateListView.as_view(), name='exchangerate-list'),
    path('exchange-rates/<str:currency>/', ExchangeRateUpdateView.as_view(), name='exchangerate-detail'),

    # Замовлення
    path('orders/', OrderListCreateView.as_view(), name='order-list'),
    path('orders/export/csv/', OrderExportCSVView.as_view(), name='order-export-csv'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/export/pdf/', OrderExportPDFView.as_view(), name='order-export-pdf'),
    path('orders/<int:pk>/refund/', OrderRefundView.as_view(), name='order-refund'),
    path('orders/<int:pk>/prepay/', OrderPrepayView.as_view(), name='order-prepay'),
    path('orders/<int:pk>/receipt/', OrderReceiptPDFView.as_view(), name='order-receipt'),

    # Позиції замовлення
    path('orders/<int:order_id>/items/', OrderItemListCreateView.as_view(), name='orderitem-list'),
    path('orders/<int:order_id>/items/<int:pk>/', OrderItemDetailView.as_view(), name='orderitem-detail'),

    # Транзакції
    path('transactions/', TransactionListCreateView.as_view(), name='transaction-list'),
    path('transactions/export/csv/', TransactionExportCSVView.as_view(), name='transaction-export-csv'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
]