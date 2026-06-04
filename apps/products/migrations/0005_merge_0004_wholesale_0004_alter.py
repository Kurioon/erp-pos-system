from django.db import migrations


class Migration(migrations.Migration):
    """Об'єднує два паралельні вузли 0004 у products:
    - 0004_alter_nomenclature_purchase_price_and_more (валідатори purchase/sale)
    - 0004_nomenclature_wholesale_price_and_more (опт-ціна + ті самі валідатори)
    Операцій не містить — лише зводить граф міграцій в один leaf.
    """

    dependencies = [
        ('products', '0004_alter_nomenclature_purchase_price_and_more'),
        ('products', '0004_nomenclature_wholesale_price_and_more'),
    ]

    operations = []
