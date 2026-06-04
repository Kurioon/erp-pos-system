from decimal import Decimal
from rest_framework import serializers
from django.db.models import Sum, F
from .models import CashRegister, Order, Transaction, OrderItem, ExchangeRate, Supplier


class CashRegisterSerializer(serializers.ModelSerializer):
    # BUG-02 — баланс окремо по валютах
    balance = serializers.SerializerMethodField()

    class Meta:
        model = CashRegister
        fields = ['id', 'name', 'warehouse', 'created_at', 'balance']

    def get_balance(self, obj):
        income_types = ('prepay', 'payment', 'sale', 'income')
        expense_types = ('refund', 'return', 'expense')

        # Групуємо по валютах окремо
        income_by_currency = obj.transactions.filter(
            transaction_type__in=income_types
        ).values('currency').annotate(total=Sum('amount'))

        expense_by_currency = obj.transactions.filter(
            transaction_type__in=expense_types
        ).values('currency').annotate(total=Sum('amount'))

        income_map = {item['currency']: item['total'] for item in income_by_currency}
        expense_map = {item['currency']: item['total'] for item in expense_by_currency}

        all_currencies = set(income_map.keys()) | set(expense_map.keys())

        balance = {}
        for currency in all_currencies:
            income = income_map.get(currency, Decimal('0'))
            expense = expense_map.get(currency, Decimal('0'))
            balance[currency] = income - expense

        return balance


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ['order']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        # BUG-05 — user read_only
        read_only_fields = ['balance_due', 'status', 'user', 'total_amount']

    def validate_prepay_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Передоплата не може бути від\'ємною.')
        return value

    def validate(self, data):
        instance = self.instance
        total = data.get('total_amount', instance.total_amount if instance else Decimal('0'))
        prepay = data.get('prepay_amount', instance.prepay_amount if instance else Decimal('0'))

        order_type = data.get('order_type', instance.order_type if instance else None)
        supplier = data.get('supplier', instance.supplier if instance else None)

        if order_type == 'retail' and supplier is not None:
            raise serializers.ValidationError(
                {'supplier': 'Роздрібне замовлення (retail) не може мати постачальника.'}
            )

        if prepay > total:
            raise serializers.ValidationError(
                {'prepay_amount': 'Передоплата не може бути більшою за загальну суму.'}
            )

        if not instance and prepay > 0:
            raise serializers.ValidationError(
                {'prepay_amount': 'При створенні замовлення передоплата має бути 0. Використовуйте POST /api/orders/{id}/prepay/'}
            )

        if not instance:
            data['balance_due'] = total
            data['status'] = 'draft'

        return data


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['user']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Сума транзакції повинна бути більше нуля.')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ['currency', 'rate_to_uah', 'updated_at', 'updated_by']
        read_only_fields = ['currency', 'updated_at', 'updated_by']