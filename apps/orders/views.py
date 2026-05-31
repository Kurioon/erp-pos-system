import csv
import io
from django.http import HttpResponse
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
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'admin':
            return Order.objects.all()
        return Order.objects.filter(
            cash_register__in=CashRegister.objects.filter(
                warehouse__is_archived=False
            ),
            user=user
        )

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


class OrderExportCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Статус', 'Тип', 'Сума', 'Передоплата',
            'Борг', 'Коментар/ТТН', 'Дата створення'
        ])

        orders = Order.objects.filter(is_archived=False)

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)

        for order in orders:
            writer.writerow([
                order.id,
                order.status,
                order.order_type,
                order.total_amount,
                order.prepay_amount,
                order.balance_due,
                order.comment_ttn,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
            ])

        return response


class TransactionExportCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Замовлення', 'Каса', 'Тип', 'Сума', 'Валюта', 'Дата'
        ])

        transactions = Transaction.objects.all()

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            transactions = transactions.filter(timestamp__date__gte=date_from)
        if date_to:
            transactions = transactions.filter(timestamp__date__lte=date_to)

        for t in transactions:
            writer.writerow([
                t.id,
                t.order.id,
                t.cash_register.name,
                t.transaction_type,
                t.amount,
                t.currency,
                t.timestamp.strftime('%Y-%m-%d %H:%M'),
            ])

        return response


class OrderExportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Замовлення не знайдено'}, status=404)

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        p.setFont('Helvetica-Bold', 16)
        p.drawString(50, 800, f'Order #{order.id}')

        p.setFont('Helvetica', 12)
        p.drawString(50, 770, f'Status: {order.status}')
        p.drawString(50, 750, f'Type: {order.order_type}')
        p.drawString(50, 730, f'Total: {order.total_amount}')
        p.drawString(50, 710, f'Prepay: {order.prepay_amount}')
        p.drawString(50, 690, f'Balance due: {order.balance_due}')
        p.drawString(50, 670, f'Comment/TTN: {order.comment_ttn}')
        p.drawString(50, 650, f'Created: {order.created_at.strftime("%Y-%m-%d %H:%M")}')

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="order_{order.id}.pdf"'
        return response