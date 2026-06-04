from decimal import Decimal
from rest_framework import serializers
from .models import CashRegister, Order, Transaction, OrderItem, ExchangeRate, Supplier

class CashRegisterSerializer(serializers.ModelSerializer):
    # ЗАДАЧА 5 — Динамічний баланс
    balance = serializers.SerializerMethodField()

    class Meta:
        model = CashRegister
        fields = ['id', 'name', 'warehouse', 'created_at', 'balance']

    def get_balance(self, obj):
        income_types = ('prepay', 'payment', 'sale', 'income')
        expense_types = ('refund', 'return', 'expense')

        # Транзакції можуть бути в різних валютах — приводимо все до гривні
        rates = {er.currency: er.rate_to_uah for er in ExchangeRate.objects.all()}
        rates['UAH'] = Decimal('1')

        balance = Decimal('0.00')
        for t in obj.transactions.all():
            amount_uah = t.amount * rates.get(t.currency, Decimal('1'))
            if t.transaction_type in income_types:
                balance += amount_uah
            elif t.transaction_type in expense_types:
                balance -= amount_uah

        return balance.quantize(Decimal('0.01'))


# БАГ 3 — Серіалізатор постачальників
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
        # user проставляється автоматично з request (автор замовлення)
        read_only_fields = ['balance_due', 'status', 'user']

    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Загальна сума повинна бути більше нуля.')
        return value

    def validate_prepay_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Передоплата не може бути від\'ємною.')
        return value

    def validate(self, data):
        instance = self.instance
        total = data.get('total_amount', instance.total_amount if instance else Decimal('0'))
        prepay = data.get('prepay_amount', instance.prepay_amount if instance else Decimal('0'))

        # БАГ 3 — Валідація постачальника
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

        # БАГ 1 (вже був пофікшений тобою)
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

    def validate_transaction_type(self, value):
        # Прямо через API дозволені лише касові операції внесення/видачі.
        # prepay/payment/sale/refund/return формуються автоматично сервісами
        # замовлень (prepay/refund/cancel), щоб не накручувати баланс каси.
        allowed = ('income', 'expense')
        if value not in allowed:
            raise serializers.ValidationError(
                "Прямо створювати можна лише 'income' (внесення) або 'expense' (видача). "
                "Решта типів формуються через операції із замовленням."
            )
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)

# ЗАДАЧА 3 — Серіалізатор курсів
class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ['currency', 'rate_to_uah', 'updated_at', 'updated_by']
        read_only_fields = ['currency', 'updated_at', 'updated_by']