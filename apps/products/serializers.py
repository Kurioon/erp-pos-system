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
    
    # --- Мультивалютні обчислювані поля (Задача 3) ---
    price_uah = serializers.SerializerMethodField()
    price_usd = serializers.SerializerMethodField()
    price_eur = serializers.SerializerMethodField()

    purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    markup_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)

    def get_category_name(self, obj):
        return obj.category.name if obj.category_id else None

    def get_price_uah(self, obj):
        rates = self.context.get('rates', {})
        try:
            return str(obj.get_price_uah(rates))
        except ValueError:
            return str(obj.sale_price or Decimal('0.00'))

    def get_price_usd(self, obj):
        rates = self.context.get('rates', {})
        rate_usd = rates.get('USD')
        if not rate_usd:
            return None
        try:
            price_uah = obj.get_price_uah(rates)
            return str((price_uah / rate_usd).quantize(Decimal('0.01')))
        except ValueError:
            return None

    def get_price_eur(self, obj):
        rates = self.context.get('rates', {})
        rate_eur = rates.get('EUR')
        if not rate_eur:
            return None
        try:
            price_uah = obj.get_price_uah(rates)
            return str((price_uah / rate_eur).quantize(Decimal('0.01')))
        except ValueError:
            return None

    supplier_name = serializers.SerializerMethodField()
    # Задача 9: контрагент-постачальник з останньої закупівлі (для переходу в профіль)
    supplier_counterparty = serializers.SerializerMethodField()

    def get_supplier_name(self, obj):
        from orders.models import OrderItem
        last_item = OrderItem.objects.filter(
            product=obj,
            order__order_type='purchase',
            order__supplier__isnull=False
        ).order_by('-order__created_at').first()

        if last_item:
            return last_item.order.supplier.name

        # Задача 9: фолбек на контрагента-постачальника
        cp_item = OrderItem.objects.filter(
            product=obj,
            order__order_type='purchase',
            order__counterparty__isnull=False
        ).order_by('-order__created_at').first()
        if cp_item:
            return cp_item.order.counterparty.name
        return None

    def get_supplier_counterparty(self, obj):
        from orders.models import OrderItem
        cp_item = OrderItem.objects.filter(
            product=obj,
            order__order_type='purchase',
            order__counterparty__isnull=False
        ).order_by('-order__created_at').first()
        if cp_item and cp_item.order.counterparty:
            cp = cp_item.order.counterparty
            return {'id': cp.id, 'name': cp.name, 'role': cp.role}
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # sale_price у відповіді завжди дорівнює price_uah (для сумісності з POS)
        data['sale_price'] = data.get('price_uah')
        return data

    def validate_code(self, value):
        # Задача 5: дубль code → 400 з ясним повідомленням
        qs = Nomenclature.objects.filter(code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f'Товар з артикулом "{value}" вже існує.')
        return value

    def validate_base_price(self, value):
        if value is not None and value <= Decimal('0.00'):
            raise serializers.ValidationError('base_price має бути більше 0')
        return value

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

    def validate(self, data):
        # Якщо purchase_price відсутнє (як буває коли фронтенд надсилає лише base_price),
        # ставимо заглушку 1.00, щоб не впала база даних (бо поле обов'язкове)
        if 'purchase_price' not in data and not self.instance:
            data['purchase_price'] = Decimal('1.00')
        return data

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
            'base_price',
            'base_currency',
            'price_uah',
            'price_usd',
            'price_eur',
            'purchase_price',
            'markup_percentage',
            'sale_price',
            'wholesale_price',
            'supplier_name',
            'supplier_counterparty',
            'vat_rate',
            'is_archived',
            'created_at',
            'updated_at',
        ]
