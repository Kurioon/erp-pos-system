from django.db import migrations, models
import cloudinary.models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='nomenclature',
            name='image',
            field=cloudinary.models.CloudinaryField(blank=True, null=True, verbose_name='image'),
        ),
        migrations.AddField(
            model_name='nomenclature',
            name='markup_percentage',
            field=models.DecimalField(decimal_places=2, default=20, max_digits=5),
        ),
        migrations.AlterField(
            model_name='nomenclature',
            name='sale_price',
            field=models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=12),
        ),
    ]
