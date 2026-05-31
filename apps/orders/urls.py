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
)

urlpatterns = [
    path('cash-registers/', CashRegisterListCreateView.as_view(), name='cashregister-list'),
    path('cash-registers/<int:pk>/', CashRegisterDetailView.as_view(), name='cashregister-detail'),
    path('cash-registers/analytics/', GlobalCashboxAnalyticsView.as_view(), name='cashregister-analytics'),
    path('orders/', OrderListCreateView.as_view(), name='order-list'),
    path('orders/export/csv/', OrderExportCSVView.as_view(), name='order-export-csv'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/export/pdf/', OrderExportPDFView.as_view(), name='order-export-pdf'),
    path('orders/<int:order_id>/items/', OrderItemListCreateView.as_view(), name='orderitem-list'),
    path('orders/<int:order_id>/items/<int:pk>/', OrderItemDetailView.as_view(), name='orderitem-detail'),
    path('transactions/', TransactionListCreateView.as_view(), name='transaction-list'),
    path('transactions/export/csv/', TransactionExportCSVView.as_view(), name='transaction-export-csv'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
]