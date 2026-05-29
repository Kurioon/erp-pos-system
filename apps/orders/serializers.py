from decimal import Decimal
from rest_framework import serializers
from .models import CashRegister, Order, Transaction


class CashRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashRegister
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
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
        total = data.get('total_amount', Decimal('0'))
        prepay = data.get('prepay_amount', Decimal('0'))

        if prepay > total:
            raise serializers.ValidationError(
                {'prepay_amount': 'Передоплата не може бути більшою за загальну суму.'}
            )

        # Рахуємо самі — ігноруємо те що передав фронтенд
        data['balance_due'] = total - prepay

        # Автоматичний статус
        if data['balance_due'] == 0 and prepay > 0:
            data['status'] = 'paid'
        elif prepay > 0:
            data['status'] = 'partial'
        else:
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
        # BUG-001: беремо юзера з request
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)