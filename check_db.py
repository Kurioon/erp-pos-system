import django
django.setup()

from apps.products.models import Nomenclature
from apps.orders.models import OrderItem

p = Nomenclature.objects.filter(name__icontains='ESET').first()
if p:
    print(f'Product: {p.name}')
    items = OrderItem.objects.filter(product=p, order__order_type='purchase')
    print(f'Purchase items count: {items.count()}')
    for i in items:
        print(f'Order {i.order.id} Supplier: {i.order.supplier}')
    
    # Let's also check if ANY product has a supplier, to see if the DB has any
    all_purchases = OrderItem.objects.filter(order__order_type='purchase', order__supplier__isnull=False)
    print(f'Total purchase items with supplier in DB: {all_purchases.count()}')
else:
    print('Product ESET not found')
