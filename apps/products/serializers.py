from decimal import Decimal

from rest_framework import serializers

from .models import Nomenclature, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent']


class NomenclatureSerializer(serializers.ModelSerializer):
    # Назва категорії для відображення (read-only)
    category_name = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return obj.category.name if obj.category_id else None

    def validate_purchase_price(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError('Ціна не може бути меншою або дорівнювати 0')
        return value

    def validate_sale_price(self, value):
        if value is not None and value <= Decimal('0.00'):
            raise serializers.ValidationError('Ціна не може бути меншою або дорівнювати 0')
        return value

    def validate_wholesale_price(self, value):
        if value is not None and value <= Decimal('0.00'):
            raise serializers.ValidationError('Ціна не може бути меншою або дорівнювати 0')
        return value

    def validate_markup_percentage(self, value):
        if value is not None and value < Decimal('0.00'):
            raise serializers.ValidationError('Націнка не може бути від\'ємною.')
        return value

    class Meta:
        model = Nomenclature
        fields = [
            'id',
            'code',
            'name',
            'category',
            'category_name',
            'unit',
            'image',
            'description',
            'barcode',
            'manufactured',
            'purchase_price',
            'markup_percentage',
            'sale_price',
            'wholesale_price',
            'vat_rate',
            'is_archived',
            'created_at',
            'updated_at',
        ]
