# Generated migration for adding English language fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('addresses', '0002_remove_address_district_alter_address_street'),
    ]

    operations = [
        migrations.AddField(
            model_name='governorate',
            name='name_en',
            field=models.CharField(blank=True, max_length=100, verbose_name='الاسم (إنجليزي)'),
        ),
        migrations.AddField(
            model_name='area',
            name='name_en',
            field=models.CharField(blank=True, max_length=100, verbose_name='الاسم (إنجليزي)'),
        ),
    ]
