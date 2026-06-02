import io
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import HttpResponse
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from users.permissions import IsAdminRole
from activity_log.models import ActivityLog
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

from activity_log.models import ActivityLog
from .models import Warehouse, ServiceJob, WarehouseStock
from .serializers import WarehouseSerializer, ServiceJobSerializer, WarehouseStockSerializer



class WarehouseViewSet(viewsets.ModelViewSet):
    """
    Standard ModelViewSet for Warehouse model.
    Provides CRUD operations: list, create, retrieve, update, partial_update, destroy.
    
    Implements soft delete: destroy() sets is_archived=True instead of actual deletion.
    """
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Warehouse.objects.filter(is_archived=False)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_archived = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def get_permissions(self):
        """
        Динамічні дозволи:
        - create, update, partial_update, destroy -> тільки Адмін.
        - list, retrieve -> всі авторизовані користувачі.
        """
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminRole()]
        return [IsAuthenticated()]


class ServiceJobViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for ServiceJob model with custom create, partial_update, and soft delete.
    
    API Contracts:
    - POST /api/service-jobs: Returns {"job_id": id, "status": status} with HTTP 201
    - PATCH /api/service-jobs/:id: Returns {"job_id": id, "status": status, "updated_at": updated_at} with HTTP 200
    - DELETE /api/service-jobs/:id: Soft delete (is_archived=True), returns HTTP 204
    """
    serializer_class = ServiceJobSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [IsAuthenticated]  # Базовий захист для всіх стандартних CRUD операцій

    def get_queryset(self):
        """
        Override queryset to return only non-archived service jobs (is_archived=False).
        """
        return ServiceJob.objects.filter(is_archived=False)

    def create(self, request, *args, **kwargs):
        """
        Override create to return strict API contract: {"job_id": id, "status": status}.
        Returns HTTP 201 on success.
        If storage_cell is occupied (conflict), returns HTTP 409 Conflict.
        """
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            # BUG-002: Check if the error is a storage_cell conflict
            if 'storage_cell' in serializer.errors:
                return Response(
                    {
                        "error": "Conflict",
                        "detail": serializer.errors['storage_cell']
                    },
                    status=status.HTTP_409_CONFLICT
                )
            # For other validation errors, return 400 Bad Request
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_create(serializer)
        instance = serializer.instance
        ActivityLog.log(self.request.user, 'create', instance)
        
        # Повертаємо відповідь згідно з контрактом: { job_id, status } з HTTP 201
        return Response(
            {
                "job_id": instance.id,
                "status": instance.status
            },
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'customer_name': {'type': 'string', 'nullable': True},
                    'customer_phone': {'type': 'string', 'nullable': True},
                    'device_name': {'type': 'string', 'nullable': True},
                    'description': {'type': 'string', 'nullable': True},
                    'comment': {'type': 'string', 'nullable': True},
                    'photo': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Photo file upload'
                    },
                    'status': {'type': 'string', 'nullable': True},
                    'storage_cell': {'type': 'string', 'nullable': True}
                }
            }
        }
    )
    def update(self, request, *args, **kwargs):
        """
        Override update to handle storage_cell conflicts with HTTP 409 Conflict.
        Returns HTTP 200 on success.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            # BUG-002: Check if the error is a storage_cell conflict
            if 'storage_cell' in serializer.errors:
                return Response(
                    {
                        "error": "Conflict",
                        "detail": serializer.errors['storage_cell']
                    },
                    status=status.HTTP_409_CONFLICT
                )
            # For other validation errors, return 400 Bad Request
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_update(serializer)
        ActivityLog.log(self.request.user, 'update', instance)
        
        # For full update (PUT), return standard API contract
        return Response(
            {
                "job_id": instance.id,
                "status": instance.status,
                "updated_at": instance.updated_at
            },
            status=status.HTTP_200_OK
        )
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'customer_name': {'type': 'string', 'nullable': True},
                    'customer_phone': {'type': 'string', 'nullable': True},
                    'device_name': {'type': 'string', 'nullable': True},
                    'description': {'type': 'string', 'nullable': True},
                    'comment': {'type': 'string', 'nullable': True},
                    'photo': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Photo file upload'
                    },
                    'status': {'type': 'string', 'nullable': True},
                    'storage_cell': {'type': 'string', 'nullable': True}
                }
            }
        }
    )

    def partial_update(self, request, *args, **kwargs):
        """
        Override partial_update to return strict API contract: {"job_id": id, "status": status, "updated_at": updated_at}.
        Returns HTTP 200 on success.
        If storage_cell is occupied (conflict), returns HTTP 409 Conflict.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        
        if not serializer.is_valid():
            # BUG-002: Check if the error is a storage_cell conflict
            if 'storage_cell' in serializer.errors:
                return Response(
                    {
                        "error": "Conflict",
                        "detail": serializer.errors['storage_cell']
                    },
                    status=status.HTTP_409_CONFLICT
                )
            # For other validation errors, return 400 Bad Request
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_update(serializer)
        ActivityLog.log(self.request.user, 'update', instance)
        
        # Повертаємо відповідь згідно з контрактом: { job_id, status, updated_at } з HTTP 200
        return Response(
            {
                "job_id": instance.id,
                "status": instance.status,
                "updated_at": instance.updated_at
            },
            status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to implement soft delete.
        Instead of deleting, set is_archived=True and save.
        Returns HTTP 204 NO CONTENT on success.
        """
        instance = self.get_object()
        instance.is_archived = True
        instance.save()
        ActivityLog.log(self.request.user, 'delete', instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- НОВІ ЕНДПОІНТИ ---

    @action(detail=False, methods=['get'], url_path='export/csv', permission_classes=[IsAuthenticated])
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="service_jobs.csv"'
        response.write('\ufeff'.encode('utf8'))

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['ID', 'Клієнт', 'Телефон', 'Пристрій', 'Статус', 'Комірка зберігання'])

        jobs = self.get_queryset()
        
        for job in jobs:
            writer.writerow([
                job.id,
                job.customer_name,
                job.customer_phone,
                job.device_name,
                job.get_status_display(),
                job.storage_cell or '—'
            ])

        return response

    @action(detail=True, methods=['get'], url_path='export/pdf', permission_classes=[IsAuthenticated])
    def export_pdf(self, request, pk=None):
        job = self.get_object()
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 800, f"Service Job Ticket #{job.id}")
        
        p.setFont("Helvetica", 12)
        p.drawString(100, 770, f"Customer: {job.customer_name}")
        p.drawString(100, 750, f"Phone: {job.customer_phone}")
        p.drawString(100, 730, f"Device: {job.device_name}")
        p.drawString(100, 710, f"Status: {job.get_status_display()}")
        
        if job.storage_cell:
            p.drawString(100, 690, f"Storage Cell: {job.storage_cell}")

        p.showPage()
        p.save()
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="service_job_{job.id}.pdf"'
        
        return response
    
    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'create', instance)

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'update', instance)

    def perform_destroy(self, instance):
        ActivityLog.log(self.request.user, 'delete', instance)
        instance.is_archived = True
        instance.save()


class WarehouseStockViewSet(viewsets.ModelViewSet):
    """
    Standard ModelViewSet for WarehouseStock model.
    Provides CRUD operations: list, create, retrieve, update, partial_update, destroy.
    Includes related warehouse and nomenclature names for frontend readability.
    
    Implements soft delete: destroy() sets is_archived=True instead of actual deletion.
    """
    serializer_class = WarehouseStockSerializer
    
    # ОНОВЛЕНО: Базовий захист для всіх стандартних CRUD операцій
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        """
        Override queryset to return only non-archived warehouse stocks (is_archived=False).
        ОНОВЛЕНО: Додано select_related для вирішення проблеми N+1 запитів!
        """
        return WarehouseStock.objects.filter(
            is_archived=False
        ).select_related(
            'warehouse', 
            'nomenclature'
        )

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to implement soft delete.
        Instead of deleting, set is_archived=True and save.
        Returns HTTP 204 NO CONTENT on success.
        """
        instance = self.get_object()
        instance.is_archived = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- НОВІ ЕНДПОІНТИ ---

    # ОНОВЛЕНО: Замінено AllowAny на IsAdminUser (або IsAuthenticated). Звіти мають качати тільки свої.
    @action(detail=False, methods=['get'], url_path='export/csv', permission_classes=[IsAdminUser])
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="warehouse_stock.csv"'
        response.write('\ufeff'.encode('utf8'))

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['ID', 'Назва Складу', 'Товар', 'Кількість', 'В архіві'])

        stocks = self.get_queryset()
        
        for stock in stocks:
            writer.writerow([
                stock.id,
                stock.warehouse.name if stock.warehouse else '—',
                stock.nomenclature.name if stock.nomenclature else '—', 
                stock.quantity,
                'Так' if stock.is_archived else 'Ні'
            ])

        return response

    # ОНОВЛЕНО: Прибрано зайвий декоратор @permission_classes. Права доступу передані в @action.
    @action(detail=False, methods=['post'], url_path='import/csv', permission_classes=[IsAdminUser])
    def import_csv(self, request):
        from products.models import Nomenclature

        file = request.FILES.get('file')
        
        if not file:
            return Response({"error": "Файл не знайдено. Передайте файл у полі 'file'."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if not file.name.endswith('.csv'):
            return Response({"error": "Формат файлу має бути CSV."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string, delimiter=';') 
        
        next(reader, None) # Пропускаємо заголовки

        errors = []
        valid_rows = []

        for row_num, row in enumerate(reader, start=2):
            if len(row) < 3:
                errors.append({"row": row_num, "error": "Недостатньо колонок. Потрібно: ID Складу, ID Товару, Кількість."})
                continue

            warehouse_id_str, nomenclature_id_str, quantity_str = row[0], row[1], row[2]

            try:
                warehouse = Warehouse.objects.get(id=warehouse_id_str)
            except Exception:
                errors.append({"row": row_num, "error": f"Склад з ID {warehouse_id_str} не знайдено."})
                continue

            try:
                nomenclature = Nomenclature.objects.get(id=nomenclature_id_str)
            except Nomenclature.DoesNotExist:
                errors.append({"row": row_num, "error": f"Товар з ID {nomenclature_id_str} не знайдено."})
                continue
                
            try:
                quantity = int(quantity_str)
                if quantity < 0:
                    raise ValueError
            except ValueError:
                errors.append({"row": row_num, "error": f"Некоректна кількість: '{quantity_str}'. Має бути додатним числом."})
                continue

            valid_rows.append({
                'warehouse': warehouse,
                'nomenclature': nomenclature,
                'quantity': quantity
            })

        if errors:
            return Response({"status": "error", "errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                for data in valid_rows:
                    stock, created = WarehouseStock.objects.get_or_create(
                        warehouse=data['warehouse'],
                        nomenclature=data['nomenclature'],
                        defaults={'quantity': 0}
                    )
                    
                    # Якщо запис існував, ми просто додаємо кількість. 
                    # Якщо створився новий - до нуля додасться кількість.
                    stock.quantity += data['quantity']
                    stock.is_archived = False 
                    stock.save()
                    
        except Exception as e:
            return Response({"error": f"Помилка бази даних: {str(e)}"}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "status": "success", 
            "message": f"Успішно імпортовано або оновлено {len(valid_rows)} записів."
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='low-stock', permission_classes=[IsAdminUser])
    def low_stock(self, request):
        low_stocks = self.get_queryset().filter(quantity__lte=2).order_by('quantity')
        serializer = self.get_serializer(low_stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)