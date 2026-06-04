from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes
from .models import StockMovement, Warehouse, ServiceJob, WarehouseStock


class WarehouseSerializer(serializers.ModelSerializer):
    """Serializer for Warehouse model including address field."""
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'address', 'created_at']
        read_only_fields = ['id', 'created_at']


class ServiceJobSerializer(serializers.ModelSerializer):
    """Serializer for ServiceJob model including comment and photo fields."""
    photo = serializers.ImageField(required=False, allow_null=True)
    
    # ВИДАЛЕНО @extend_schema_field, щоб не було SyntaxError

    class Meta:
        model = ServiceJob
        fields = [
            'id',
            'customer_name',
            'customer_phone',
            'device_name',
            'description',
            'comment',
            'photo',
            'status',
            'storage_cell',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_storage_cell(self, value):
        """
        Реалізація Acceptance Criteria US-02: Комірка блокується.
        Перевіряємо, чи немає вже активного ремонту в цій комірці.
        """
        # Якщо комірка не передана, пропускаємо валідацію
        if not value:
            return value

        active_statuses = ['pending', 'waiting_parts']
        job_id = self.instance.id if self.instance else None
        
        # ВИПРАВЛЕНО: Використовуємо .exists() для оптимізації швидкодії
        is_occupied = ServiceJob.objects.filter(
            storage_cell=value, 
            status__in=active_statuses,
            is_archived=False
        ).exclude(id=job_id).exists()

        if is_occupied:
            raise serializers.ValidationError(
                f"Комірка {value} вже зайнята іншим активним ремонтом."
            )
        return value
    
    def validate_status(self, new_status):
        """
        Валідація машини станів (FSM) для ремонтів.
        Блокує нелогічні переходи (наприклад, з 'done' у 'pending').
        """
        if not self.instance:
            return new_status

        current_status = self.instance.status
        
        ALLOWED_TRANSITIONS = {
            'pending': ['waiting_parts', 'done', 'returned'],
            'waiting_parts': ['pending', 'done', 'returned'],
            'done': ['returned'],
            'returned': [], # Кінцевий статус
        }

        if new_status == current_status:
            return new_status

        allowed_next_states = ALLOWED_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_next_states:
            raise serializers.ValidationError(
                f"Неможливо перевести ремонт зі статусу '{current_status}' у '{new_status}'."
            )

        return new_status

    def validate(self, data):
        """
        Глобальна валідація об'єкта. 
        Перевіряє, щоб при статусі 'returned' комірка не заповнювалась, і очищає її.
        """
        if not self.instance:
            return data

        new_status = data.get('status', self.instance.status)
        
        if new_status == 'returned':
            # Замість "мовчазного" очищення, сваримося, якщо юзер передав комірку
            if data.get('storage_cell'):
                raise serializers.ValidationError(
                    {"storage_cell": "При видачі пристрою (статус 'returned') комірка має бути порожньою."}
                )
            data['storage_cell'] = None 
            
        return data


class WarehouseStockSerializer(serializers.ModelSerializer):
    """
    Serializer for WarehouseStock model.
    Includes related warehouse name and nomenclature name for frontend readability.
    """
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    nomenclature_name = serializers.CharField(source='nomenclature.name', read_only=True)

    class Meta:
        model = WarehouseStock
        fields = ['id', 'warehouse', 'warehouse_name', 'nomenclature', 'nomenclature_name', 'quantity']
        read_only_fields = ['id', 'warehouse_name', 'nomenclature_name']

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Кількість не може бути від'ємною.")
        return value
    
class StockMovementSerializer(serializers.ModelSerializer):
    warehouse = serializers.CharField(source='warehouse.name', read_only=True)
    nomenclature = serializers.CharField(source='nomenclature.name', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'warehouse', 'nomenclature', 'quantity_change', 
            'quantity_before', 'quantity_after', 'reason', 'order', 'created_at'
        ]