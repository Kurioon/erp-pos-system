from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.permissions import IsAdminRole
from .models import CashRegister, Order, Transaction
from .serializers import CashRegisterSerializer, OrderSerializer, TransactionSerializer


class CashRegisterListCreateView(generics.ListCreateAPIView):
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CashRegister.objects.filter(warehouse__is_archived=False)


class CashRegisterDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CashRegister.objects.filter(warehouse__is_archived=False)


class GlobalCashboxAnalyticsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        cash_registers = CashRegister.objects.filter(warehouse__is_archived=False)
        serializer = CashRegisterSerializer(cash_registers, many=True)
        return Response(serializer.data)


class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Order.objects.filter(is_archived=False)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        cash_register = self.request.query_params.get('cash_register')
        if cash_register:
            queryset = queryset.filter(cash_register_id=cash_register)

        user = self.request.query_params.get('user')
        if user:
            queryset = queryset.filter(user_id=user)

        return queryset


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        if order.status != 'draft':
            return Response(
                {'error': 'Замовлення можна редагувати тільки зі статусом draft.'},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        order.is_archived = True
        order.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Transaction.objects.all()

        order = self.request.query_params.get('order')
        if order:
            queryset = queryset.filter(order_id=order)

        cash_register = self.request.query_params.get('cash_register')
        if cash_register:
            queryset = queryset.filter(cash_register_id=cash_register)

        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        return queryset


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]