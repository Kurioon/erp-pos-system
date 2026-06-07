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
    # Задача 9: дані контрагента-покупця для переходу в профіль
    counterparty_data = serializers.SerializerMethodField()
    # Сценарій 2 (Backordering): остання закупівля запчастини під цей ремонт
    backorder_purchase = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.apps import apps
        Nomenclature = apps.get_model('products', 'Nomenclature')
        Counterparty = apps.get_model('orders', 'Counterparty')
        self.fields['device'] = serializers.PrimaryKeyRelatedField(
            queryset=Nomenclature.objects.all(),
            required=False,
            allow_null=True
        )
        self.fields['counterparty'] = serializers.PrimaryKeyRelatedField(
            queryset=Counterparty.objects.all(),
            required=False,
            allow_null=True
        )

    def get_counterparty_data(self, obj):
        cp = obj.counterparty
        if not cp:
            return None
        return {'id': cp.id, 'name': cp.name, 'phone': cp.phone, 'role': cp.role}

    def get_backorder_purchase(self, obj):
        po = obj.backorder_purchases.order_by('-created_at').first()
        if not po:
            return None
        return {'id': po.id, 'status': po.status}

    class Meta:
        model = ServiceJob
        fields = [
            'id',
            'customer_name',
            'customer_phone',
            'counterparty',
            'counterparty_data',
            'backorder_purchase',
            'device',
            'device_name',
            'description',
            'price',
            'payment_status',
            'paid_amount',
            'balance_due',
            'payment_currency',
            'cash_register',
            'comment',
            'photo',
            'status',
            'storage_cell',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'payment_status', 'paid_amount', 'balance_due', 'payment_currency', 'cash_register']
        extra_kwargs = {
            'device_name': {'required': False}
        }

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

    def validate_price(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Орієнтовна вартість повинна бути більшою за нуль.")
        return value

    def validate(self, data):
        """
        Глобальна валідація об'єкту. 
        Наприклад, щоб при статусі 'returned' комірка була очищена, а девайс видано.
        """
        # Правило (зверху 6.1): заповнювати device_name
        if data.get('device'):
            data['device_name'] = data['device'].name
        elif not data.get('device_name') and (not self.instance or not self.instance.device_name):
            raise serializers.ValidationError({"device_name": "Необхідно обрати пристрій із бази або ввести вручну."})

        if not self.instance:
            return data

        new_status = data.get('status', self.instance.status)
        
        if new_status == 'returned':
            # Перевіряємо чи оплачений ремонт
            payment_status = data.get('payment_status', self.instance.payment_status)
            if payment_status in ['unpaid', 'partial']:
                raise serializers.ValidationError({"status": "Не можна видати пристрій (статус 'returned'), якщо ремонт не оплачений повністю."})

            # Логіка очищення комірки
            if data.get('storage_cell'):
                raise serializers.ValidationError(
                    {"storage_cell": "При видачі девайсу (статус 'returned') комірка має бути порожньою."}
                )
            data['storage_cell'] = None

        return data

    def create(self, validated_data):
        instance = super().create(validated_data)
        # B9-1: ремонт → контрагент виступає покупцем (supplier → both)
        if instance.counterparty:
            instance.counterparty.mark_role('buyer')
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        # B9-1: ремонт → контрагент виступає покупцем (supplier → both)
        if instance.counterparty:
            instance.counterparty.mark_role('buyer')
        return instance


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
    transfer_warehouse = serializers.CharField(source='transfer_warehouse.name', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'warehouse', 'nomenclature', 'quantity_change', 
            'quantity_before', 'quantity_after', 'reason', 'order', 'transfer_warehouse', 'created_at'
        ]