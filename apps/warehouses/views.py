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
        
        # Повертаємо відповідь згідно з контрактом: { job_id, status } з HTTP 201
        return Response(
            {
                "job_id": instance.id,
                "status": instance.status
            },
            status=status.HTTP_201_CREATED
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
        
        # For full update (PUT), return standard API contract
        return Response(
            {
                "job_id": instance.id,
                "status": instance.status,
                "updated_at": instance.updated_at
            },
            status=status.HTTP_200_OK
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