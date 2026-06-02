from decimal import Decimal
from rest_framework import serializers
from .models import CashRegister, Order, Transaction, OrderItem


class CashRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashRegister
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['balance_due', 'status']

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

        if prepay > total:
            raise serializers.ValidationError(
                {'prepay_amount': 'Передоплата не може бути більшою за загальну суму.'}
            )

        # БАГ 1 — при створенні забороняємо prepay_amount > 0
        # Оплата тільки через POST /api/orders/{id}/prepay/
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