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
    OrderCancelView,
    OrderReceiveView,
    OrderReceiptPDFView,
    ExchangeRateListView,
    ExchangeRateUpdateView,
    SupplierListCreateView,
    SupplierDetailView,
    CounterpartyListCreateView,
    CounterpartyDetailView,
    CounterpartyOrdersView,
    CounterpartyServiceJobsView,
    CounterpartyBalanceView,
    CounterpartyCreateOrderView,
)

urlpatterns = [
    path('suppliers/', SupplierListCreateView.as_view(), name='supplier-list'),
    path('suppliers/<int:pk>/', SupplierDetailView.as_view(), name='supplier-detail'),

    # Задача 9 — контрагенти
    path('counterparties/', CounterpartyListCreateView.as_view(), name='counterparty-list'),
    path('counterparties/<int:pk>/', CounterpartyDetailView.as_view(), name='counterparty-detail'),
    path('counterparties/<int:pk>/orders/', CounterpartyOrdersView.as_view(), name='counterparty-orders'),
    path('counterparties/<int:pk>/service-jobs/', CounterpartyServiceJobsView.as_view(), name='counterparty-service-jobs'),
    path('counterparties/<int:pk>/balance/', CounterpartyBalanceView.as_view(), name='counterparty-balance'),
    path('counterparties/<int:pk>/create-order/', CounterpartyCreateOrderView.as_view(), name='counterparty-create-order'),

    path('cash-registers/', CashRegisterListCreateView.as_view(), name='cashregister-list'),
    path('cash-registers/analytics/', GlobalCashboxAnalyticsView.as_view(), name='cashregister-analytics'),
    path('cash-registers/<int:pk>/', CashRegisterDetailView.as_view(), name='cashregister-detail'),

    path('exchange-rates/', ExchangeRateListView.as_view(), name='exchangerate-list'),
    path('exchange-rates/<str:currency>/', ExchangeRateUpdateView.as_view(), name='exchangerate-detail'),

    path('orders/', OrderListCreateView.as_view(), name='order-list'),
    path('orders/export/csv/', OrderExportCSVView.as_view(), name='order-export-csv'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/export/pdf/', OrderExportPDFView.as_view(), name='order-export-pdf'),
    path('orders/<int:pk>/refund/', OrderRefundView.as_view(), name='order-refund'),
    path('orders/<int:pk>/prepay/', OrderPrepayView.as_view(), name='order-prepay'),
    path('orders/<int:pk>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
    path('orders/<int:pk>/receive/', OrderReceiveView.as_view(), name='order-receive'),
    path('orders/<int:pk>/receipt/', OrderReceiptPDFView.as_view(), name='order-receipt'),

    path('orders/<int:order_id>/items/', OrderItemListCreateView.as_view(), name='orderitem-list'),
    path('orders/<int:order_id>/items/<int:pk>/', OrderItemDetailView.as_view(), name='orderitem-detail'),

    path('transactions/', TransactionListCreateView.as_view(), name='transaction-list'),
    path('transactions/export/csv/', TransactionExportCSVView.as_view(), name='transaction-export-csv'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
]