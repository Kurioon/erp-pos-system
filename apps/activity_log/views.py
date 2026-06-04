from django.db.models import Q
from rest_framework import viewsets

from users.permissions import IsAdminRole
from .models import ActivityLog
from .serializers import ActivityLogSerializer


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if action := params.get('action'):
            queryset = queryset.filter(action=action)
        if model_name := params.get('model_name'):
            queryset = queryset.filter(model_name__iexact=model_name)
        if user := params.get('user'):
            queryset = queryset.filter(user__email__iexact=user)
        if search := params.get('search'):
            queryset = queryset.filter(
                Q(model_name__icontains=search)
                | Q(object_repr__icontains=search)
                | Q(action__icontains=search)
            )
        return queryset
