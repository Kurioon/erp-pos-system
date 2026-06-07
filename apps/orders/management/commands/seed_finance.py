from django.core.management.base import BaseCommand
from decimal import Decimal
from warehouses.models import Warehouse
from orders.models import CashRegister, Counterparty, Order, Transaction
from warehouses.models import ServiceJob

class Command(BaseCommand):
    help = 'Seed finance module data'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting finance seeder...")

        warehouse, _ = Warehouse.objects.get_or_create(
            name="Головний склад",
            defaults={"address": "Київ, Хрещатик 1"}
        )
        self.stdout.write(f"Warehouse: {warehouse.name}")

        cashboxes = [
            {"name": "Головна каса"},
            {"name": "Сейф (Резерв)"},
            {"name": "Термінал ПриватБанк"}
        ]
        for cb_data in cashboxes:
            cb, created = CashRegister.objects.get_or_create(
                name=cb_data["name"],
                defaults={"warehouse": warehouse}
            )
            if created:
                self.stdout.write(f"Created CashRegister: {cb.name}")
                Transaction.objects.create(
                    cash_register=cb,
                    transaction_type="income",
                    amount=Decimal("10000.00"),
                    currency="UAH",
                )

        main_cashbox = CashRegister.objects.filter(name="Головна каса").first()

        counterparties = [
            {"name": "Іван Клієнт", "phone": "+380501234567", "role": "buyer"},
            {"name": "ТОВ ПостачГруп", "phone": "+380671234567", "role": "supplier"},
            {"name": "Універсал-Партнер", "phone": "+380931234567", "role": "both"},
        ]
        for cp_data in counterparties:
            cp, created = Counterparty.objects.get_or_create(
                phone=cp_data["phone"],
                defaults={"name": cp_data["name"], "role": cp_data["role"]}
            )
            if created:
                self.stdout.write(f"Created Counterparty: {cp.name}")

        buyer = Counterparty.objects.filter(role="buyer").first()

        order = Order.objects.create(
            order_type="retail",
            status="partial",
            counterparty=buyer,
            total_amount=Decimal("5000.00"),
            currency="UAH",
        )
        Transaction.objects.create(
            cash_register=main_cashbox,
            transaction_type="sale",
            amount=Decimal("2000.00"),
            currency="UAH",
            order=order,
            counterparty=buyer,
        )
        Transaction.objects.create(
            cash_register=main_cashbox,
            transaction_type="sale",
            amount=Decimal("3000.00"),
            currency="UAH",
            order=order,
            counterparty=buyer,
            status="pending",
        )
        self.stdout.write(f"Created retail order with debt for {buyer.name}")

        job = ServiceJob.objects.create(
            counterparty=buyer,
            customer_name=buyer.name,
            customer_phone=buyer.phone,
            device_name="iPhone 13 Pro",
            description="Заміна екрану",
            price=Decimal("4500.00"),
            paid_amount=Decimal("1500.00"),
            payment_status="partial",
            status="in_progress"
        )
        Transaction.objects.create(
            cash_register=main_cashbox,
            transaction_type="payment",
            amount=Decimal("1500.00"),
            currency="UAH",
            service_job=job,
            counterparty=buyer,
        )
        Transaction.objects.create(
            cash_register=main_cashbox,
            transaction_type="payment",
            amount=Decimal("3000.00"),
            currency="UAH",
            service_job=job,
            counterparty=buyer,
            status="pending",
        )
        self.stdout.write(f"Created ServiceJob with debt for {buyer.name}")

        self.stdout.write("Finance seeder completed successfully!")
