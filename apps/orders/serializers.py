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

    def validate(self, data):
        total = data.get('total_amount', 0)
        prepay = data.get('prepay_amount', 0)

        if prepay > total:
            raise serializers.ValidationError(
                {'prepay_amount': 'Передоплата не може бути більшою за загальну суму.'}
            )

        data['balance_due'] = total - prepay

        if data['balance_due'] == 0 and prepay > 0:
            data['status'] = 'paid'
        elif prepay > 0:
            data['status'] = 'partial'

        return data


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Сума транзакції повинна бути більше нуля.')
        return value