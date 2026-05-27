from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import ServiceJob
from .serializers import ServiceJobSerializer

class ServiceJobViewSet(viewsets.ModelViewSet):
    queryset = ServiceJob.objects.all()
    serializer_class = ServiceJobSerializer

    # Перевизначаємо метод часткового оновлення (PATCH)
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Повертаємо відповідь згідно з контрактом: { job_id, status, updated_at }
        return Response({
            "job_id": instance.id,
            "status": instance.status,
            "updated_at": instance.updated_at
        }, status=status.HTTP_200_OK)