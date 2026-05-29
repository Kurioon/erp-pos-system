from rest_framework import serializers
from .models import Warehouse, ServiceJob, WarehouseStock


class WarehouseSerializer(serializers.ModelSerializer):
    """Serializer for Warehouse model including address field."""
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'address', 'created_at']
        read_only_fields = ['id', 'created_at']


class ServiceJobSerializer(serializers.ModelSerializer):
    """Serializer for ServiceJob model including comment field."""
    class Meta:
        model = ServiceJob
        fields = [
            'id',
            'customer_name',
            'customer_phone',
            'device_name',
            'description',
            'comment',
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
        # ВИПРАВЛЕНО: Використовуємо нові статуси згідно з ТЗ
        active_statuses = ['pending', 'waiting_parts']
        
        job_id = self.instance.id if self.instance else None
        
        # ВИПРАВЛЕНО: Додано is_archived=False, щоб архівні ремонти не блокували комірку
        existing_job = ServiceJob.objects.filter(
            storage_cell=value, 
            status__in=active_statuses,
            is_archived=False
        ).exclude(id=job_id).first()

        if existing_job:
            raise serializers.ValidationError(
                f"Комірка {value} вже зайнята ремонтом #{existing_job.id}."
            )
        return value


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