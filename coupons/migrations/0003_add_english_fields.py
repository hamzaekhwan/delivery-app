# Generated migration for adding English language fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupons', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='description_en',
            field=models.TextField(blank=True, verbose_name='الوصف (إنجليزي)'),
        ),
    ]
