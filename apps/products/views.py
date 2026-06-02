import csv
import io
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from activity_log.models import ActivityLog
from users.permissions import IsAdminRole
from .models import Nomenclature
from .serializers import NomenclatureSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Nomenclature.objects.filter(is_archived=False).order_by('code')
    serializer_class = NomenclatureSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        if search := params.get('search'):
            queryset = queryset.filter(
                Q(code__icontains=search)
                | Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(barcode__icontains=search)
                | Q(manufactured__icontains=search)
            )

        if unit := params.get('unit'):
            queryset = queryset.filter(unit__iexact=unit)

        if barcode := params.get('barcode'):
            queryset = queryset.filter(barcode__iexact=barcode)

        if manufactured := params.get('manufactured'):
            queryset = queryset.filter(manufactured__icontains=manufactured)

        if is_archived := params.get('is_archived'):
            if is_archived.lower() in ('true', '1', 'yes'):
                queryset = queryset.filter(is_archived=True)
            elif is_archived.lower() in ('false', '0', 'no'):
                queryset = queryset.filter(is_archived=False)

        if min_price := params.get('min_price'):
            queryset = queryset.filter(sale_price__gte=min_price)
        if max_price := params.get('max_price'):
            queryset = queryset.filter(sale_price__lte=max_price)

        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'create', instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'update', instance)

    def perform_destroy(self, instance):
        ActivityLog.log(self.request.user, 'delete', instance)
        instance.is_archived = True
        instance.save()

    @action(detail=False, methods=['get'], url_path='import/csv/template',
            permission_classes=[IsAdminRole])
    def import_csv_template(self, request):
        """Завантажити шаблон CSV для імпорту номенклатури."""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="nomenclature_template.csv"'
        response.write('﻿'.encode('utf-8'))
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['code', 'name', 'unit', 'barcode', 'purchase_price', 'markup_percentage', 'vat_rate', 'description'])
        writer.writerow(['NB999', 'Приклад товару', 'шт', '4820001000099', '1000.00', '20.00', '20.00', 'Опис товару'])
        return response

    @action(detail=False, methods=['post'], url_path='import/csv',
            permission_classes=[IsAdminRole])
    def import_csv(self, request):
        """
        POST /api/products/import/csv/
        Масовий імпорт номенклатури з CSV файлу.
        Обов'язкові колонки: code, name, purchase_price
        Необов'язкові: unit, barcode, markup_percentage, vat_rate, description
        Якщо товар з таким code вже існує — оновлюється.
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'error': "Файл не знайдено. Передайте файл у полі 'file'."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not file.name.endswith('.csv'):
            return Response({'error': 'Формат файлу має бути CSV.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded = file.read().decode('utf-8-sig')  # utf-8-sig знімає BOM якщо є
        except UnicodeDecodeError:
            return Response({'error': 'Не вдалося декодувати файл. Збережіть CSV у кодуванні UTF-8.'},
                            status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(decoded), delimiter=';')

        REQUIRED = {'code', 'name', 'purchase_price'}
        if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
            return Response(
                {'error': 'CSV має містити обов\'язкові колонки: ' + ', '.join(REQUIRED)},
                status=status.HTTP_400_BAD_REQUEST
            )

        errors = []
        valid_rows = []

        for row_num, row in enumerate(reader, start=2):
            code = row.get('code', '').strip()
            name = row.get('name', '').strip()
            purchase_price_raw = row.get('purchase_price', '').strip()

            if not code:
                errors.append({'row': row_num, 'error': 'Поле code порожнє.'})
                continue
            if not name:
                errors.append({'row': row_num, 'error': 'Поле name порожнє.'})
                continue
            try:
                purchase_price = Decimal(purchase_price_raw)
                if purchase_price <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                errors.append({'row': row_num, 'error': f'Некоректна ціна: "{purchase_price_raw}".'})
                continue

            try:
                markup = Decimal(row.get('markup_percentage', '20').strip() or '20')
            except InvalidOperation:
                markup = Decimal('20')

            try:
                vat = Decimal(row.get('vat_rate', '0').strip() or '0')
            except InvalidOperation:
                vat = Decimal('0')

            valid_rows.append({
                'code': code,
                'name': name,
                'unit': row.get('unit', 'шт').strip() or 'шт',
                'barcode': row.get('barcode', '').strip() or None,
                'purchase_price': purchase_price,
                'markup_percentage': markup,
                'vat_rate': vat,
                'description': row.get('description', '').strip() or '',
            })

        if errors:
            return Response({'status': 'error', 'errors': errors},
                            status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0

        try:
            with transaction.atomic():
                for data in valid_rows:
                    barcode = data.pop('barcode')
                    obj, created = Nomenclature.objects.get_or_create(
                        code=data['code'],
                        defaults={**data, 'barcode': barcode}
                    )
                    if not created:
                        for field, value in data.items():
                            setattr(obj, field, value)
                        if barcode:
                            obj.barcode = barcode
                        obj.save()
                        updated_count += 1
                        ActivityLog.log(request.user, 'update', obj)
                    else:
                        created_count += 1
                        ActivityLog.log(request.user, 'create', obj)
        except Exception as e:
            return Response({'error': f'Помилка бази даних: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'status': 'success',
            'created': created_count,
            'updated': updated_count,
            'total': created_count + updated_count,
        }, status=status.HTTP_201_CREATED)
