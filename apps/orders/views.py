import csv
import io
from decimal import Decimal
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from users.permissions import IsAdminRole
from activity_log.models import ActivityLog
from .models import CashRegister, Order, Transaction, OrderItem
from .serializers import CashRegisterSerializer, OrderSerializer, TransactionSerializer, OrderItemSerializer
from .services import process_refund, process_prepay


class CashRegisterListCreateView(generics.ListCreateAPIView):
    serializer_class = CashRegisterSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return CashRegister.objects.filter(warehouse__is_archived=False)


class CashRegisterDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CashRegisterSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminRole()]
        return [IsAuthenticated()]

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

    def perform_create(self, serializer):
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'create', instance)

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

    def perform_update(self, serializer):
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'update', instance)

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
        ActivityLog.log(self.request.user, 'delete', order)
        order.is_archived = True
        order.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderItemListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        order_id = self.kwargs.get('order_id')
        return OrderItem.objects.filter(order_id=order_id)

    def perform_create(self, serializer):
        order_id = self.kwargs.get('order_id')
        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Замовлення не знайдено.')
        if order.status != 'draft':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Додавати позиції можна лише до замовлення зі статусом draft.')
        serializer.save(order=order)


class OrderItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        order_id = self.kwargs.get('order_id')
        return OrderItem.objects.filter(order_id=order_id)


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


class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]


class OrderExportCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        response.write('﻿'.encode('utf-8'))

        writer = csv.writer(response, delimiter=';')
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
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        response.write('﻿'.encode('utf-8'))

        writer = csv.writer(response, delimiter=';')
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


class OrderRefundView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'cash_register': {'type': 'integer', 'example': 1},
                    'currency': {'type': 'string', 'example': 'UAH', 'enum': ['UAH', 'USD', 'EUR']},
                },
                'required': ['cash_register'],
            }
        },
        description='Повернення оплаченого замовлення. Статус: paid → returned.',
    )
    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Замовлення не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

        cash_register_id = request.data.get('cash_register')
        currency = request.data.get('currency', 'UAH')

        if not cash_register_id:
            return Response({'error': 'Поле cash_register є обовʼязковим.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cash_register = CashRegister.objects.get(pk=cash_register_id)
        except CashRegister.DoesNotExist:
            return Response({'error': 'Касу не знайдено.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            t = process_refund(order, currency, cash_register, request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        return Response({
            'order_id': order.id,
            'status': order.status,
            'transaction_id': t.id,
        }, status=status.HTTP_201_CREATED)


class OrderPrepayView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'amount': {'type': 'string', 'example': '500.00'},
                    'cash_register': {'type': 'integer', 'example': 1},
                    'currency': {'type': 'string', 'example': 'UAH', 'enum': ['UAH', 'USD', 'EUR']},
                },
                'required': ['amount', 'cash_register'],
            }
        },
        description='Передоплата замовлення. Статус: draft → partial або paid залежно від суми.',
    )
    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Замовлення не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

        amount_raw = request.data.get('amount')
        currency = request.data.get('currency', 'UAH')
        cash_register_id = request.data.get('cash_register')

        if not amount_raw:
            return Response({'error': 'Поле amount є обовʼязковим.'}, status=status.HTTP_400_BAD_REQUEST)

        if not cash_register_id:
            return Response({'error': 'Поле cash_register є обовʼязковим.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount_raw))
        except Exception:
            return Response({'error': 'Некоректне значення amount.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cash_register = CashRegister.objects.get(pk=cash_register_id)
        except CashRegister.DoesNotExist:
            return Response({'error': 'Касу не знайдено.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            t = process_prepay(order, amount, currency, cash_register, request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'order_id': order.id,
            'status': order.status,
            'balance_due': order.balance_due,
            'transaction_id': t.id,
        }, status=status.HTTP_201_CREATED)


class OrderReceiptPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

        try:
            order = Order.objects.get(pk=pk, status='paid')
        except Order.DoesNotExist:
            return Response(
                {'error': 'Оплачене замовлення не знайдено. Чек доступний лише для статусу paid.'},
                status=status.HTTP_404_NOT_FOUND
            )

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        p.setFont('Helvetica-Bold', 16)
        p.drawString(50, 800, f'Receipt — Order #{order.id}')

        p.setFont('Helvetica', 12)
        p.drawString(50, 770, f'Status: {order.status}')
        p.drawString(50, 750, f'Type: {order.order_type}')
        p.drawString(50, 730, f'Total: {order.total_amount} UAH')
        p.drawString(50, 710, f'Paid: {order.prepay_amount} UAH')
        p.drawString(50, 690, f'Balance due: {order.balance_due} UAH')
        p.drawString(50, 670, f'Date: {order.created_at.strftime("%Y-%m-%d %H:%M")}')

        p.setFont('Helvetica-Bold', 12)
        p.drawString(50, 640, 'Items:')

        y = 620
        p.setFont('Helvetica', 11)
        for item in order.items.select_related('product').all():
            line = f'{item.product.name}  x{item.quantity}  @ {item.price} UAH  = {item.quantity * item.price} UAH'
            p.drawString(60, y, line)
            y -= 20
            if y < 50:
                p.showPage()
                y = 800
                p.setFont('Helvetica', 11)

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{order.id}.pdf"'
        return response

from .models import ExchangeRate
from .serializers import ExchangeRateSerializer

# ЗАДАЧА 3 — Ендпоінти курсів валют
class ExchangeRateListView(generics.ListAPIView):
    """ GET /api/exchange-rates/ — всі курси (доступно всім авторизованим) """
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]

class ExchangeRateUpdateView(generics.RetrieveUpdateAPIView):
    """ PUT /api/exchange-rates/{currency}/ — оновити курс (тільки адмін) """
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAdminRole]
    lookup_field = 'currency' # Дозволяє шукати по 'USD' замість ID

    def perform_update(self, serializer):
        # Записуємо, хто саме оновив курс
        serializer.save(updated_by=self.request.user)