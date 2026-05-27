from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import CashRegister, Order, Transaction
from .serializers import CashRegisterSerializer, OrderSerializer, TransactionSerializer


class CashRegisterListCreateView(generics.ListCreateAPIView):
    queryset = CashRegister.objects.all()
    serializer_class = CashRegisterSerializer


class CashRegisterDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CashRegister.objects.all()
    serializer_class = CashRegisterSerializer


class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class TransactionListCreateView(generics.ListCreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer