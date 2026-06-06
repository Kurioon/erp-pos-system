import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient
from users.models import CustomUser
from apps.products.models import Nomenclature, Category
from apps.orders.models import Order, OrderItem, Supplier
from apps.warehouses.models import ServiceJob

def run_tests():
    print("=== STARTING TESTS ===")
    admin = CustomUser.objects.filter(is_superuser=True).first()
    if not admin:
        print("No admin user found")
        return
        
    client = APIClient()
    client.force_authenticate(user=admin)
    
    # 1. Test 4.1: Supplier Name logic
    print("\n--- TEST 4.1: Supplier Logic ---")
    cat, _ = Category.objects.get_or_create(name="Test Cat")
    prod, _ = Nomenclature.objects.get_or_create(name="Test Supplier Product", category=cat, defaults={'barcode':'1234', 'code':'1234'})
    
    # Check without order
    res = client.get(f'/api/products/{prod.id}/', HTTP_HOST='localhost')
    print("Product without purchase:", res.json().get('supplier_name') == None)
    
    # Add a purchase order
    supp, _ = Supplier.objects.get_or_create(name="Mega Supplier")
    order = Order.objects.create(cash_register_id=1, user=admin, order_type='purchase', supplier=supp)
    OrderItem.objects.create(order=order, product=prod, quantity=1, price=100)
    
    # Check with order
    res2 = client.get(f'/api/products/{prod.id}/', HTTP_HOST='localhost')
    print("Product with purchase:", res2.json().get('supplier_name') == "Mega Supplier")
    
    # Test 4.1: Warehouse filter
    print("\n--- TEST 4.1: Warehouse filter ---")
    res_stock = client.get(f'/api/warehouse-stocks/?nomenclature={prod.id}', HTTP_HOST='localhost')
    print("Warehouse stock filter status:", res_stock.status_code)
    
    # 2. Test 6.1: Service Job logic
    print("\n--- TEST 6.1: ServiceJob Logic ---")
    
    # Test 6.1.1: Missing both
    res3 = client.post('/api/service-jobs/', {
        "customer_name": "Test Customer",
        "customer_phone": "+380501234567",
        "description": "Test description"
    }, format='json', HTTP_HOST='localhost')
    print("Missing device validation works:", 'device_name' in res3.json())
    
    # Test 6.1.2: Only device_name
    res4 = client.post('/api/service-jobs/', {
        "customer_name": "Test Customer",
        "customer_phone": "+380501234567",
        "description": "Test description",
        "device_name": "Manual Device Name"
    }, format='json', HTTP_HOST='localhost')
    print("Manual device_name works:", res4.status_code == 201)
    
    # Test 6.1.3: Only device ID
    res5 = client.post('/api/service-jobs/', {
        "customer_name": "Test Customer",
        "customer_phone": "+380501234567",
        "description": "Test description",
        "device": prod.id
    }, format='json', HTTP_HOST='localhost')
    if res5.status_code == 201:
        data = res5.json()
        print("Device auto-fills device_name:", data.get('device_name') == prod.name)
        job_id = data['id']
    else:
        print("Failed to create with device ID", res5.json())
        job_id = None
        
    # Test 6.1.4: Update to returned with storage cell
    if job_id:
        res6 = client.patch(f'/api/service-jobs/{job_id}/', {
            "status": "returned",
            "storage_cell": "A1"
        }, format='json', HTTP_HOST='localhost')
        print("Returned with storage_cell validation works:", 'storage_cell' in res6.json())
        
        res7 = client.patch(f'/api/service-jobs/{job_id}/', {
            "status": "returned"
        }, format='json', HTTP_HOST='localhost')
        print("Returned without storage_cell works:", res7.status_code == 200)
    
    print("\n=== TESTS COMPLETED ===")

if __name__ == '__main__':
    run_tests()
