from django.contrib import admin

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'model_name', 'object_repr', 'user')
    list_filter = ('action', 'model_name', 'user')
    search_fields = ('model_name', 'object_repr', 'user__username')
