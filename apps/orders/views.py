import csv
import io
from decimal import Decimal
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from users.permissions import IsAdminRole
from activity_log.models import ActivityLog
from .models import CashRegister, Order, Transaction, OrderItem, ExchangeRate, Supplier
from .serializers import CashRegisterSerializer, OrderSerializer, TransactionSerializer, OrderItemSerializer, ExchangeRateSerializer, SupplierSerializer
from .services import process_refund, process_prepay, process_cancellation


# Типи транзакцій які продавець НЕ може створювати вручну
ADMIN_ONLY_TRANSACTION_TYPES = ('income', 'expense')
SYSTEM_ONLY_TRANSACTION_TYPES = ('prepay', 'payment', 'refund', 'sale', 'return')


class SupplierListCreateView(generics.ListCreateAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


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

    # BUG-05 — зберігаємо user при створенні
    def perform_create(self, serializer):
        # Прив'язуємо замовлення до автора, щоб продавець бачив свої замовлення
        instance = serializer.save(user=self.request.user)
        ActivityLog.log(self.request.user, 'create', instance)

    def get_queryset(self):
        user = self.request.user
        # BUG-11 — однакова фільтрація для списку і деталей
        if hasattr(user, 'role') and user.role == 'admin':
            queryset = Order.objects.filter(is_archived=False)
        else:
            queryset = Order.objects.filter(is_archived=False, user=user)

        # Продавець бачить лише свої замовлення, адмін — усі
        request_user = self.request.user
        if not (hasattr(request_user, 'role') and request_user.role == 'admin'):
            queryset = queryset.filter(user=request_user)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # order_type=retail|purchase — щоб «Закупівлі» не змішувались із роздрібними
        order_type = self.request.query_params.get('order_type')
        if order_type:
            queryset = queryset.filter(order_type=order_type)

        cash_register = self.request.query_params.get('cash_register')
        if cash_register:
            queryset = queryset.filter(cash_register_id=cash_register)

        user_filter = self.request.query_params.get('user')
        if user_filter:
            queryset = queryset.filter(user_id=user_filter)

        # Стабільне сортування — обов'язкове для коректної пагінації
        # (без ORDER BY PostgreSQL може дублювати/пропускати записи між сторінками).
        # Підтримуємо ?ordering= з фронту, дефолт — найновіші першими.
        ordering = self.request.query_params.get('ordering', '-created_at')
        allowed_ordering = {'created_at', '-created_at', 'id', '-id'}
        if ordering not in allowed_ordering:
            ordering = '-created_at'
        queryset = queryset.order_by(ordering)

        return queryset


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'admin':
            return Order.objects.all()
        # Продавець має доступ лише до власних замовлень
        return Order.objects.filter(user=user)

    def perform_update(self, serializer):
        # Редагувати можна лише чернетку; статус змінюється через prepay/refund/cancel
        if serializer.instance.status != 'draft':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Замовлення можна редагувати тільки зі статусом draft.')
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'update', instance)

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
        qs = OrderItem.objects.filter(order_id=order_id)
        user = self.request.user
        if not (hasattr(user, 'role') and user.role == 'admin'):
            qs = qs.filter(order__user=user)
        return qs

    def perform_create(self, serializer):
        order_id = self.kwargs.get('order_id')
        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Замовлення не знайдено.')
        # Продавець може додавати позиції лише до власних замовлень
        user = self.request.user
        if not (hasattr(user, 'role') and user.role == 'admin') and order.user_id != user.id:
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
        qs = OrderItem.objects.filter(order_id=order_id)
        user = self.request.user
        if not (hasattr(user, 'role') and user.role == 'admin'):
            qs = qs.filter(order__user=user)
        return qs


class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Найновіші транзакції першими — щоб свіжа оплата одразу була зверху
        # у «Фінансах» (раніше йшли в кінці пагінації й здавалися «зниклими»).
        queryset = Transaction.objects.all().order_by('-timestamp')

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

    # BUG-03 — обмеження на створення транзакцій
    def perform_create(self, serializer):
        user = self.request.user
        transaction_type = serializer.validated_data.get('transaction_type')

        if transaction_type in SYSTEM_ONLY_TRANSACTION_TYPES:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                f'Тип транзакції {transaction_type} створюється автоматично через відповідний ендпоінт.'
            )

        if transaction_type in ADMIN_ONLY_TRANSACTION_TYPES:
            if not (hasattr(user, 'role') and user.role == 'admin'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Тільки адміністратор може створювати транзакції типу income/expense.')

        serializer.save(user=user)


class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]


class OrderExportCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        response.write('\ufeff'.encode('utf-8'))

        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'ID', 'Статус', 'Тип', 'Сума', 'Передоплата',
            'Борг', 'Коментар/ТТН', 'Дата створення'
        ])

        user = request.user
        if hasattr(user, 'role') and user.role == 'admin':
            orders = Order.objects.filter(is_archived=False)
        else:
            orders = Order.objects.filter(is_archived=False, user=user)

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)

        for order in orders:
            writer.writerow([
                order.id, order.status, order.order_type,
                order.total_amount, order.prepay_amount,
                order.balance_due, order.comment_ttn,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
            ])

        return response


class TransactionExportCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        response.write('\ufeff'.encode('utf-8'))

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['ID', 'Замовлення', 'Каса', 'Тип', 'Сума', 'Валюта', 'Дата'])

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
                t.order.id if t.order else '',
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

        # BUG-07 — перевірка власника
        user = request.user
        try:
            if hasattr(user, 'role') and user.role == 'admin':
                order = Order.objects.get(pk=pk)
            else:
                order = Order.objects.get(pk=pk, user=user)
        except Order.DoesNotExist:
            return Response({'error': 'Замовлення не знайдено'}, status=404)

        # Продавець може отримати PDF лише власних замовлень
        user = request.user
        if not (hasattr(user, 'role') and user.role == 'admin') and order.user_id != user.id:
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

    # Додаємо схему для Swagger, щоб з'явилося поле Request body
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'amount': {'type': 'string', 'example': '500.00'},
                    'currency': {'type': 'string', 'example': 'UAH'},
                    'cash_register': {'type': 'integer', 'example': 2},
                },
                'required': ['amount', 'cash_register'],
            }
        },
        description='Оплата або передоплата замовлення',
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

        order.refresh_from_db()
        return Response({
            'order_id': order.id,
            'status': order.status,
            'balance_due': order.balance_due,
            'transaction_id': t.id,
        }, status=status.HTTP_201_CREATED)


class OrderCancelView(APIView):
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
        description='Скасування замовлення (draft/partial → cancelled). Повертає передоплату та товар на склад, якщо була.',
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
            t = process_cancellation(order, currency, cash_register, request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        return Response({
            'order_id': order.id,
            'status': order.status,
            'transaction_id': t.id if t else None,
        }, status=status.HTTP_201_CREATED)


class OrderReceiptPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

        # BUG-07 — перевірка власника
        user = request.user
        try:
            if hasattr(user, 'role') and user.role == 'admin':
                order = Order.objects.get(pk=pk, status='paid')
            else:
                order = Order.objects.get(pk=pk, status='paid', user=user)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Оплачене замовлення не знайдено або доступ заборонено.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Продавець може отримати чек лише власних замовлень
        user = request.user
        if not (hasattr(user, 'role') and user.role == 'admin') and order.user_id != user.id:
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


class ExchangeRateListView(generics.ListAPIView):
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]


class ExchangeRateUpdateView(generics.RetrieveUpdateAPIView):
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAdminRole]
    lookup_field = 'currency'

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)