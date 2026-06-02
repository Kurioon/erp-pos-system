from django.db.models import Q
from rest_framework import viewsets

from activity_log.models import ActivityLog
from .models import Nomenclature
from .serializers import NomenclatureSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Nomenclature.objects.filter(is_archived=False).order_by('code')
    serializer_class = NomenclatureSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        if search := params.get('search'):
            queryset = queryset.filter(
                Q(code__icontains=search)
                | Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(barcode__icontains=search)
                | Q(manufactured__icontains=search)
            )

        if unit := params.get('unit'):
            queryset = queryset.filter(unit__iexact=unit)

        if barcode := params.get('barcode'):
            queryset = queryset.filter(barcode__iexact=barcode)

        if manufactured := params.get('manufactured'):
            queryset = queryset.filter(manufactured__icontains=manufactured)

        if is_archived := params.get('is_archived'):
            if is_archived.lower() in ('true', '1', 'yes'):
                queryset = queryset.filter(is_archived=True)
            elif is_archived.lower() in ('false', '0', 'no'):
                queryset = queryset.filter(is_archived=False)

        if min_price := params.get('min_price'):
            queryset = queryset.filter(sale_price__gte=min_price)
        if max_price := params.get('max_price'):
            queryset = queryset.filter(sale_price__lte=max_price)

        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'create', instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        ActivityLog.log(self.request.user, 'update', instance)

    def perform_destroy(self, instance):
        ActivityLog.log(self.request.user, 'delete', instance)
        instance.is_archived = True
        instance.save()
