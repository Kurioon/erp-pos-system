from decimal import Decimal
from rest_framework import serializers
from .models import CashRegister, Order, Transaction, OrderItem, ExchangeRate, Supplier, Counterparty


class CashRegisterSerializer(serializers.ModelSerializer):
    # BUG-02 — баланс окремо по валютах
    balance = serializers.SerializerMethodField()

    class Meta:
        model = CashRegister
        fields = ['id', 'name', 'warehouse', 'created_at', 'balance']

    def get_balance(self, obj):
        income_types = ('prepay', 'payment', 'sale', 'income')
        expense_types = ('refund', 'return', 'expense')

        balance = Decimal('0.00')
        for t in obj.transactions.all():
            amount_uah = t.amount_uah
            if t.transaction_type in income_types:
                balance += amount_uah
            elif t.transaction_type in expense_types:
                balance -= amount_uah

        return balance.quantize(Decimal('0.01'))


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class CounterpartySerializer(serializers.ModelSerializer):
    """Повний серіалізатор контрагента (Задача 9)."""
    class Meta:
        model = Counterparty
        fields = ['id', 'name', 'phone', 'email', 'role', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Ім'я обов'язкове.")
        return value.strip()

    def validate_phone(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Телефон обов\'язковий.')
        return value.strip()


class CounterpartyShortSerializer(serializers.ModelSerializer):
    """Стислий серіалізатор для вбудовування в Order/ServiceJob."""
    class Meta:
        model = Counterparty
        fields = ['id', 'name', 'phone', 'role']


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ['order']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.SerializerMethodField()
    supplier_name_input = serializers.CharField(write_only=True, required=False, allow_null=True)
    can_refund = serializers.SerializerMethodField()
    can_view_receipt = serializers.SerializerMethodField()
    # Задача 9: дані контрагента (покупця/постачальника) для переходу в профіль
    counterparty_data = CounterpartyShortSerializer(source='counterparty', read_only=True)
    # Сценарій 2 (Backordering): дані прив'язаного джерела закупівлі
    related_retail_order_data = serializers.SerializerMethodField()
    related_service_job_data = serializers.SerializerMethodField()
    # Зворотній зв'язок: остання backorder-закупівля під це джерело
    backorder_purchase = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        # user проставляється автоматично з request (автор замовлення)
        read_only_fields = ['balance_due', 'status', 'user']

    def get_can_refund(self, obj):
        return obj.status == 'paid'

    def get_can_view_receipt(self, obj):
        return obj.status in ('partial', 'paid', 'returned')

    def get_related_retail_order_data(self, obj):
        ro = obj.related_retail_order
        if not ro:
            return None
        cp = ro.counterparty
        return {
            'id': ro.id,
            'status': ro.status,
            'counterparty_data': (
                {'id': cp.id, 'name': cp.name, 'phone': cp.phone} if cp else None
            ),
        }

    def get_related_service_job_data(self, obj):
        sj = obj.related_service_job
        if not sj:
            return None
        return {
            'id': sj.id,
            'customer_name': sj.customer_name,
            'customer_phone': sj.customer_phone,
            'device_name': sj.device_name,
            'status': sj.status,
        }

    def get_backorder_purchase(self, obj):
        # Лише для retail-замовлень: остання закупівля, зроблена під нього
        if obj.order_type != 'retail':
            return None
        po = obj.backorder_purchases.order_by('-created_at').first()
        if not po:
            return None
        return {'id': po.id, 'status': po.status}

    def get_supplier_name(self, obj):
        # Назва постачальника для фронту (щоб не показував «Невідомий» при наявному supplier)
        if obj.supplier:
            return obj.supplier.name
        # Задача 9: для закупівлі підхоплюємо назву з контрагента
        if obj.order_type == 'purchase' and obj.counterparty:
            return obj.counterparty.name
        return None

    def validate_total_amount(self, value):
        instance = self.instance
        order_type = self.initial_data.get('order_type', instance.order_type if instance else None)
        
        # Дозволяємо суму 0 для порожніх чернеток закупівель
        if order_type == 'purchase' and value == 0:
            return value
            
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

        order_type = data.get('order_type', instance.order_type if instance else None)
        supplier_name_input = data.pop('supplier_name_input', None)
        supplier = data.get('supplier', instance.supplier if instance else None)

        if supplier_name_input:
            from .models import Supplier
            supplier, _ = Supplier.objects.get_or_create(name=supplier_name_input)
            data['supplier'] = supplier

        if order_type == 'retail' and supplier is not None:
            raise serializers.ValidationError(
                {'supplier': 'Роздрібне замовлення (retail) не може мати постачальника.'}
            )

        # Сценарій 2: зв'язок backorder лише для закупівель, і одне з двох джерел
        related_ro = data.get('related_retail_order', instance.related_retail_order if instance else None)
        related_sj = data.get('related_service_job', instance.related_service_job if instance else None)
        if (related_ro or related_sj) and order_type != 'purchase':
            raise serializers.ValidationError(
                {'related_retail_order': 'Прив\'язка до джерела можлива лише для закупівлі (purchase).'}
            )
        if related_ro and related_sj:
            raise serializers.ValidationError(
                {'related_service_job': 'Закупівля може бути прив\'язана лише до одного джерела (замовлення АБО ремонт).'}
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

    # ------------------------------------------------------------------
    # НОВИЙ МЕТОД: Обробка збереження товарів при створенні замовлення
    # ------------------------------------------------------------------
    def create(self, validated_data):
        # 1. Отримуємо масив 'items' напряму з сирих даних запиту
        items_data = self.initial_data.get('items', [])
        
        # 2. Створюємо саме замовлення
        order = super().create(validated_data)

        # B9-1: закупівля → контрагент виступає постачальником (buyer → both)
        if order.order_type == 'purchase' and order.counterparty:
            order.counterparty.mark_role('supplier')

        # 3. Імпортуємо модель Nomenclature локально для отримання ціни
        from products.models import Nomenclature
        
        # 4. Створюємо позиції замовлення (OrderItem)
        for item in items_data:
            product_id = item.get('product')
            quantity = item.get('quantity')
            discount_type = item.get('discount_type')
            discount_value = item.get('discount_value', Decimal('0'))
            discount_amount = item.get('discount_amount', Decimal('0'))
            
            if product_id and quantity:
                try:
                    product = Nomenclature.objects.get(pk=product_id)
                    # Визначаємо ціну: роздрібна чи закупівельна залежно від типу замовлення
                    if order.order_type == 'retail':
                        from orders.models import ExchangeRate
                        rates = {r.currency: r.rate_to_uah for r in ExchangeRate.objects.all()}
                        try:
                            # Задача 7: Снепшот ціни у валюті замовлення
                            if order.currency == 'UAH':
                                price = product.get_price_uah(rates)
                            elif order.currency == 'USD':
                                price_uah = product.get_price_uah(rates)
                                rate_usd = rates.get('USD')
                                price = (price_uah / rate_usd).quantize(Decimal('0.01')) if rate_usd else Decimal('0.00')
                            elif order.currency == 'EUR':
                                price_uah = product.get_price_uah(rates)
                                rate_eur = rates.get('EUR')
                                price = (price_uah / rate_eur).quantize(Decimal('0.01')) if rate_eur else Decimal('0.00')
                            else:
                                price = product.get_price_uah(rates)
                        except Exception:
                            price = product.sale_price or Decimal('0.00')
                    else:
                        price = product.purchase_price
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=price,
                        discount_type=discount_type,
                        discount_value=discount_value,
                        discount_amount=discount_amount
                    )
                except Nomenclature.DoesNotExist:
                    # Якщо товар з таким ID раптом не знайдено, просто пропускаємо
                    pass
                
        return order


class TransactionSerializer(serializers.ModelSerializer):
    counterparty = CounterpartyShortSerializer(read_only=True)
    source_document = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['user']

    def get_source_document(self, obj):
        if obj.order:
            return {'id': obj.order.id, 'type': obj.order.order_type, 'total_amount': obj.order.total_amount}
        if obj.service_job:
            return {'id': obj.service_job.id, 'type': 'repair', 'total_amount': obj.service_job.price}
        return None

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
            
        from orders.services import _to_uah
        amount = validated_data.get('amount', Decimal('0'))
        currency = validated_data.get('currency', 'UAH')
        validated_data['amount_uah'] = _to_uah(amount, currency)
        
        return super().create(validated_data)


class TransactionDetailSerializer(TransactionSerializer):
    """Деталь транзакції: для джерела-замовлення додає склад (позиції)."""

    def get_source_document(self, obj):
        data = super().get_source_document(obj)
        # Позиції додаємо лише для замовлень (retail/purchase); ремонт — без позицій
        if data and obj.order_id:
            data['items'] = [
                {
                    'product_name': item.product.name if item.product else None,
                    'quantity': item.quantity,
                    'price': str(item.price),
                }
                for item in obj.order.items.select_related('product').all()
            ]
        return data


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ['currency', 'rate_to_uah', 'updated_at', 'updated_by']
        read_only_fields = ['currency', 'updated_at', 'updated_by']