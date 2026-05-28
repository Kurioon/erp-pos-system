from rest_framework import serializers
from .models import ServiceJob

class ServiceJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceJob
        fields = ['id', 'customer_name', 'customer_phone', 'device_name', 'description', 'status', 'storage_cell', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_storage_cell(self, value):
        # Реалізація Acceptance Criteria US-02: Комірка блокується
        # Перевіряємо, чи немає вже активного ремонту в цій комірці
        active_statuses = ['pending', 'in_progress']
        
        # Якщо ми оновлюємо існуючий ремонт (PATCH), ігноруємо його власну комірку
        job_id = self.instance.id if self.instance else None
        
        existing_job = ServiceJob.objects.filter(
            storage_cell=value, 
            status__in=active_statuses
        ).exclude(id=job_id).first()

        if existing_job:
            raise serializers.ValidationError(f"Комірка {value} вже зайнята ремонтом #{existing_job.id}.")
        return value