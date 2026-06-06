import sys
sys.stdout.reconfigure(encoding='utf-8')

from django.db import transaction
from warehouses.models import Warehouse, WarehouseStock

print("=== Склади ===")
for w in Warehouse.objects.all().order_by('id'):
    cnt = WarehouseStock.objects.filter(warehouse_id=w.id).count()
    print(w.id, "|", w.name, "| archived=", w.is_archived, "| stocks=", cnt)

wh1 = Warehouse.objects.filter(name="Магазин №1", is_archived=False).first()
src = list(WarehouseStock.objects.filter(warehouse_id=7))
print("\nНа складі 7 позицій:", len(src))

if wh1 is None:
    print("ПОМИЛКА: активний «Магазин №1» не знайдено — нічого не роблю")
elif not src:
    print("Склад 7 порожній — переносити нічого")
else:
    moved = 0
    with transaction.atomic():
        for s in src:
            d, _ = WarehouseStock.objects.get_or_create(
                warehouse=wh1, nomenclature=s.nomenclature,
                defaults={"quantity": 0, "is_archived": False})
            d.quantity += s.quantity
            d.is_archived = False
            d.save()
            s.delete()
            moved += 1
    print("Перенесено позицій:", moved, "-> Магазин №1 (id", wh1.id, ")")

print("Залишок на складі 7 після:", WarehouseStock.objects.filter(warehouse_id=7).count())
print("Товарів на Магазин №1 тепер:", WarehouseStock.objects.filter(warehouse=wh1).count() if wh1 else "-")
