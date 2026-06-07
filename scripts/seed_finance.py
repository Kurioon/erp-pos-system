import os
import django
import sys
from decimal import Decimal

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.warehouses.models import Warehouse
from apps.orders.models import CashRegister, Counterparty, Order, Transaction
from apps.warehouses.models import ServiceJob

def run_seeder():
    print("Starting finance seeder...")

    # 1. Ensure at least one Warehouse exists
    warehouse, _ = Warehouse.objects.get_or_create(
        name="Головний склад",
        defaults={"address": "Київ, Хрещатик 1"}
    )
    print(f"Warehouse: {warehouse.name}")

    # 2. Ensure CashRegisters exist
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
            print(f"Created CashRegister: {cb.name}")
            # Add initial balance
            Transaction.objects.create(
                cash_register=cb,
                transaction_type="income",
                amount=Decimal("10000.00"),
                currency="UAH",
                comment="Початковий залишок"
            )

    main_cashbox = CashRegister.objects.filter(name="Головна каса").first()

    # 3. Create Counterparties
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
            print(f"Created Counterparty: {cp.name} ({cp.role})")

    buyer = Counterparty.objects.filter(role="buyer").first()

    # 4. Create an Order with a Debt (Pending Transaction)
    if not Order.objects.filter(counterparty=buyer, order_type="retail").exists():
        order = Order.objects.create(
            order_type="retail",
            status="partial",
            counterparty=buyer,
            total_amount=Decimal("5000.00"),
            currency="UAH",
            warehouse=warehouse
        )
        # 2000 paid, 3000 debt
        Transaction.objects.create(
            cash_register=main_cashbox,
            transaction_type="sale",
            amount=Decimal("2000.00"),
            currency="UAH",
            order=order,
            counterparty=buyer,
            comment="Часткова оплата замовлення"
        )
        # Create debt transaction
        Transaction.objects.create(
            cash_register=main_cashbox, # the intended cash register for debt
            transaction_type="sale",
            amount=Decimal("3000.00"),
            currency="UAH",
            order=order,
            counterparty=buyer,
            status="pending",
            comment="Заборгованість"
        )
        print(f"Created retail order with debt for {buyer.name}")

    # 5. Create a ServiceJob with Debt
    if not ServiceJob.objects.filter(counterparty=buyer).exists():
        job = ServiceJob.objects.create(
            warehouse=warehouse,
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
        # Paid portion
        Transaction.objects.create(
            cash_register=main_cashbox,
            transaction_type="repair_payment",
            amount=Decimal("1500.00"),
            currency="UAH",
            service_job=job,
            counterparty=buyer,
            comment="Передоплата за ремонт"
        )
        # Debt portion
        Transaction.objects.create(
            cash_register=main_cashbox,
            transaction_type="repair_payment",
            amount=Decimal("3000.00"),
            currency="UAH",
            service_job=job,
            counterparty=buyer,
            status="pending",
            comment="Борг за ремонт"
        )
        print(f"Created ServiceJob with debt for {buyer.name}")

    print("Finance seeder completed successfully!")

if __name__ == '__main__':
    run_seeder()
