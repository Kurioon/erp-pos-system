from rest_framework.test import APIClient
from users.models import CustomUser

try:
    admin = CustomUser.objects.get(email='admin@erp.com')
    client = APIClient()
    client.force_authenticate(user=admin)
    
    res = client.get('/api/products/', HTTP_HOST='localhost')
    products = res.json().get('results', [])
    
    if not products:
        print("❌ Немає товарів.")
    else:
        p = products[0]
        print('\n✅ ТОВАР:', p['name'])
        print('   - Ціна:', p['price_uah'], 'UAH')
        print('   - Постачальник:', p.get('supplier_name', 'null'))
        
        res2 = client.get(f'/api/warehouse-stocks/?nomenclature={p["id"]}', HTTP_HOST='localhost')
        stocks = res2.json().get('results', [])
        
        print('\n✅ ЗАЛИШКИ:')
        if stocks:
            for s in stocks:
                print(f'   - Склад: {s.get("warehouse_name", "Невідомо")} | Кількість: {s.get("quantity", 0)} шт')
        else:
            print('   - Залишків немає')
            
        print('\n🎉 УСЕ ПРАЦЮЄ!')
except Exception as e:
    print("Error:", e)
