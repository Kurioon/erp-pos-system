from django.urls import path
from .views import (
    CashRegisterListCreateView,
    CashRegisterDetailView,
    GlobalCashboxAnalyticsView,
    OrderListCreateView,
    OrderDetailView,
    TransactionListCreateView,
    TransactionDetailView,
)

urlpatterns = [
    path('cash-registers/', CashRegisterListCreateView.as_view(), name='cashregister-list'),
    path('cash-registers/<int:pk>/', CashRegisterDetailView.as_view(), name='cashregister-detail'),
    path('cash-registers/analytics/', GlobalCashboxAnalyticsView.as_view(), name='cashregister-analytics'),
    path('orders/', OrderListCreateView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('transactions/', TransactionListCreateView.as_view(), name='transaction-list'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
]