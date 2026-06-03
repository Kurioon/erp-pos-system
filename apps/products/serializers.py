from rest_framework import serializers

from .models import Nomenclature


class NomenclatureSerializer(serializers.ModelSerializer):
    retail_price = serializers.DecimalField(
        source='sale_price',
        max_digits=12,
        decimal_places=2,
        write_only=True,
        required=False
    )

    class Meta:
        model = Nomenclature
        fields = [
            'id',
            'code',
            'name',
            'unit',
            'image',
            'description',
            'barcode',
            'manufactured',
            'purchase_price',
            'markup_percentage',
            'sale_price',
            'retail_price',
            'vat_rate',
            'is_archived',
            'created_at',
            'updated_at'
        ]
