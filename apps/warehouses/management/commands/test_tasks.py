from django.core.management.base import BaseCommand
from rest_framework.test import APIClient
from users.models import CustomUser
from products.models import Nomenclature, Category
from orders.models import Order, OrderItem, Supplier
from warehouses.models import ServiceJob

class Command(BaseCommand):
    help = 'Test Task 4.1 and 6.1 logic'

    def handle(self, *args, **options):
        self.stdout.write("=== STARTING TESTS ===")
        admin = CustomUser.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write("No admin user found")
            return
            
        client = APIClient()
        client.force_authenticate(user=admin)
        
        # 1. Test 4.1: Supplier Name logic
        self.stdout.write("\n--- TEST 4.1: Supplier Logic ---")
        from decimal import Decimal
        cat, _ = Category.objects.get_or_create(name="Test Cat")
        prod, _ = Nomenclature.objects.get_or_create(name="Test Supplier Product", category=cat, defaults={'barcode':'1234', 'code':'1234', 'purchase_price': Decimal('100.0'), 'markup_percentage': Decimal('1.0')})
        
        # Check without order
        res = client.get(f'/api/products/{prod.id}/', HTTP_HOST='localhost')
        self.stdout.write(f"Product without purchase (should be None): {res.json().get('supplier_name') == None}")
        
        # Add a purchase order
        from orders.models import CashRegister
        from warehouses.models import Warehouse
        wh, _ = Warehouse.objects.get_or_create(name="Test Warehouse")
        cr, _ = CashRegister.objects.get_or_create(id=1, defaults={'name': 'Test Register', 'warehouse': wh})
        supp, _ = Supplier.objects.get_or_create(name="Mega Supplier")
        order = Order.objects.create(cash_register=cr, user=admin, order_type='purchase', supplier=supp)
        OrderItem.objects.create(order=order, product=prod, quantity=1, price=100)
        
        # Check with order
        res2 = client.get(f'/api/products/{prod.id}/', HTTP_HOST='localhost')
        self.stdout.write(f"Product with purchase (should be Mega Supplier): {res2.json().get('supplier_name') == 'Mega Supplier'}")
        
        # Test 4.1: Warehouse filter
        self.stdout.write("\n--- TEST 4.1: Warehouse filter ---")
        res_stock = client.get(f'/api/warehouse-stocks/?nomenclature={prod.id}', HTTP_HOST='localhost')
        self.stdout.write(f"Warehouse stock filter status (should be 200): {res_stock.status_code}")
        
        # 2. Test 6.1: Service Job logic
        self.stdout.write("\n--- TEST 6.1: ServiceJob Logic ---")
        
        # Test 6.1.1: Missing both
        res3 = client.post('/api/service-jobs/', {
            "customer_name": "Test Customer",
            "customer_phone": "+380501234567",
            "description": "Test description"
        }, format='json', HTTP_HOST='localhost')
        self.stdout.write(f"Missing device validation works (should be True): {'device_name' in res3.json()}")
        
        # Test 6.1.2: Only device_name
        res4 = client.post('/api/service-jobs/', {
            "customer_name": "Test Customer",
            "customer_phone": "+380501234567",
            "description": "Test description",
            "device_name": "Manual Device Name"
        }, format='json', HTTP_HOST='localhost')
        self.stdout.write(f"Manual device_name works (should be True): {res4.status_code == 201}")
        
        # Test 6.1.3: Only device ID
        res5 = client.post('/api/service-jobs/', {
            "customer_name": "Test Customer",
            "customer_phone": "+380501234567",
            "description": "Test description",
            "device": prod.id
        }, format='json', HTTP_HOST='localhost')
        if res5.status_code == 201:
            data = res5.json()
            # It returns {"job_id": id, "status": status}
            job_id = data.get('job_id')
            self.stdout.write(f"Job created with ID: {job_id}")
            
            # Since the API doesn't return device_name, let's fetch it to verify
            res5_get = client.get(f'/api/service-jobs/{job_id}/', HTTP_HOST='localhost')
            if res5_get.status_code == 200:
                fetched_device_name = res5_get.json().get('device_name')
                self.stdout.write(f"Device auto-fills device_name: {fetched_device_name} == {prod.name}")
        else:
            self.stdout.write(f"Failed to create with device ID: {res5.json()}")
            job_id = None
            
        # Test 6.1.4: Update to returned with storage cell
        if job_id:
            res6 = client.patch(f'/api/service-jobs/{job_id}/', {
                "status": "returned",
                "storage_cell": "A1"
            }, format='json', HTTP_HOST='localhost')
            self.stdout.write(f"Returned with storage_cell validation works (should be True): {'storage_cell' in res6.json()}")
            
            res7 = client.patch(f'/api/service-jobs/{job_id}/', {
                "status": "returned"
            }, format='json', HTTP_HOST='localhost')
            self.stdout.write(f"Returned without storage_cell works (should be True): {res7.status_code == 200}")
        
        self.stdout.write("\n=== TESTS COMPLETED ===")
