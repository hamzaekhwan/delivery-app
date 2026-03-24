# Generated migration for adding English language fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='banner',
            name='title_en',
            field=models.CharField(blank=True, max_length=200, verbose_name='العنوان (إنجليزي)'),
        ),
        migrations.AddField(
            model_name='banner',
            name='subtitle_en',
            field=models.CharField(blank=True, max_length=300, verbose_name='العنوان الفرعي (إنجليزي)'),
        ),
        migrations.AddField(
            model_name='appconfiguration',
            name='maintenance_message_en',
            field=models.TextField(blank=True, verbose_name='رسالة الصيانة (إنجليزي)'),
        ),
    ]
