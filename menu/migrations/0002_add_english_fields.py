# Generated migration for adding English language fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='menucategory',
            name='description_en',
            field=models.TextField(blank=True, verbose_name='الوصف (إنجليزي)'),
        ),
        migrations.AddField(
            model_name='product',
            name='description_en',
            field=models.TextField(blank=True, verbose_name='الوصف (إنجليزي)'),
        ),
    ]
