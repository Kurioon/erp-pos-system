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
from users.permissions import IsAdminRole, IsAdminOrReadOnly
from .models import Nomenclature, Category
from .serializers import NomenclatureSerializer, CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """Довідник категорій товарів.

    Читання — всі авторизовані; створення/зміна/видалення — лише admin.
    Дубль назви відхиляється на рівні unique-валідації (HTTP 400, поле name).
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Nomenclature.objects.filter(is_archived=False).order_by('code')
    serializer_class = NomenclatureSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            from orders.models import ExchangeRate
            context['rates'] = {r.currency: r.rate_to_uah for r in ExchangeRate.objects.all()}
        except Exception:
            context['rates'] = {}
        return context

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

        if category_id := params.get('category'):
            try:
                queryset = queryset.filter(category_id=int(category_id))
            except (ValueError, TypeError):
                pass  # невалідне значення — ігноруємо, не падаємо

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
        columns = set(reader.fieldnames or [])
        if not reader.fieldnames or not REQUIRED.issubset(columns):
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

            # Опційні поля включаємо лише якщо їх колонка реально присутня в CSV,
            # щоб при оновленні не затирати наявні значення дефолтами (BUG-09).
            fields = {
                'code': code,
                'name': name,
                'purchase_price': purchase_price,
            }

            if 'unit' in columns:
                unit = row.get('unit', '').strip()
                if unit:
                    fields['unit'] = unit

            if 'barcode' in columns:
                fields['barcode'] = row.get('barcode', '').strip() or None

            if 'markup_percentage' in columns:
                markup_raw = row.get('markup_percentage', '').strip()
                if markup_raw:
                    try:
                        fields['markup_percentage'] = Decimal(markup_raw)
                    except InvalidOperation:
                        errors.append({'row': row_num, 'error': f'Некоректна націнка: "{markup_raw}".'})
                        continue

            if 'vat_rate' in columns:
                vat_raw = row.get('vat_rate', '').strip()
                if vat_raw:
                    try:
                        fields['vat_rate'] = Decimal(vat_raw)
                    except InvalidOperation:
                        errors.append({'row': row_num, 'error': f'Некоректний ПДВ: "{vat_raw}".'})
                        continue

            if 'description' in columns:
                fields['description'] = row.get('description', '').strip()

            valid_rows.append(fields)

        if errors:
            return Response({'status': 'error', 'errors': errors},
                            status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0

        try:
            with transaction.atomic():
                for data in valid_rows:
                    obj = Nomenclature.objects.filter(code=data['code']).first()
                    if obj is None:
                        # Новий товар — дефолти для полів, відсутніх у CSV
                        create_data = {
                            'unit': 'шт',
                            'markup_percentage': Decimal('20'),
                            'vat_rate': Decimal('0'),
                            'description': '',
                            'barcode': None,
                            **data,
                        }
                        obj = Nomenclature.objects.create(**create_data)
                        created_count += 1
                        ActivityLog.log(request.user, 'create', obj)
                    else:
                        # Оновлення — змінюємо лише поля, явно передані в CSV
                        for field, value in data.items():
                            setattr(obj, field, value)
                        obj.save()
                        updated_count += 1
                        ActivityLog.log(request.user, 'update', obj)
        except Exception as e:
            return Response({'error': f'Помилка бази даних: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'status': 'success',
            'created': created_count,
            'updated': updated_count,
            'total': created_count + updated_count,
        }, status=status.HTTP_201_CREATED)
