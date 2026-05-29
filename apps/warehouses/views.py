from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Warehouse, ServiceJob, WarehouseStock
from .serializers import WarehouseSerializer, ServiceJobSerializer, WarehouseStockSerializer


class WarehouseViewSet(viewsets.ModelViewSet):
    """
    Standard ModelViewSet for Warehouse model.
    Provides CRUD operations: list, create, retrieve, update, partial_update, destroy.
    
    Implements soft delete: destroy() sets is_archived=True instead of actual deletion.
    """
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        """
        Override queryset to return only non-archived warehouses (is_archived=False).
        """
        return Warehouse.objects.filter(is_archived=False)

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


class ServiceJobViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for ServiceJob model with custom create, partial_update, and soft delete.
    
    API Contracts:
    - POST /api/service-jobs: Returns {"job_id": id, "status": status} with HTTP 201
    - PATCH /api/service-jobs/:id: Returns {"job_id": id, "status": status, "updated_at": updated_at} with HTTP 200
    - DELETE /api/service-jobs/:id: Soft delete (is_archived=True), returns HTTP 204
    """
    serializer_class = ServiceJobSerializer

    def get_queryset(self):
        """
        Override queryset to return only non-archived service jobs (is_archived=False).
        """
        return ServiceJob.objects.filter(is_archived=False)

    def create(self, request, *args, **kwargs):
        """
        Override create to return strict API contract: {"job_id": id, "status": status}.
        Returns HTTP 201 on success.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        instance = serializer.instance
        
        # Повертаємо відповідь згідно з контрактом: { job_id, status } з HTTP 201
        return Response(
            {
                "job_id": instance.id,
                "status": instance.status
            },
            status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, *args, **kwargs):
        """
        Override partial_update to return strict API contract: {"job_id": id, "status": status, "updated_at": updated_at}.
        Returns HTTP 200 on success.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
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
        return Response(status=status.HTTP_204_NO_CONTENT)


class WarehouseStockViewSet(viewsets.ModelViewSet):
    """
    Standard ModelViewSet for WarehouseStock model.
    Provides CRUD operations: list, create, retrieve, update, partial_update, destroy.
    Includes related warehouse and nomenclature names for frontend readability.
    
    Implements soft delete: destroy() sets is_archived=True instead of actual deletion.
    """
    serializer_class = WarehouseStockSerializer

    def get_queryset(self):
        """
        Override queryset to return only non-archived warehouse stocks (is_archived=False).
        """
        return WarehouseStock.objects.filter(is_archived=False)

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