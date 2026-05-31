import csv
from django.http import HttpResponse
from rest_framework.views import APIView


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

        # Фільтрація по даті якщо передано
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
        import io

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