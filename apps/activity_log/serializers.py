from rest_framework import serializers

from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = ['timestamp', 'model_name', 'object_id', 'object_repr']
