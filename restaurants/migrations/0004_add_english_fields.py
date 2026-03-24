# Generated migration for adding English language fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurants', '0003_alter_restaurant_restaurant_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurant',
            name='description_en',
            field=models.TextField(blank=True, verbose_name='الوصف (إنجليزي)'),
        ),
    ]
