# Generated manually for async processing fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0015_rename_queue_to_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='processing_status',
            field=models.CharField(
                choices=[
                    ('queue', 'В очереди'), 
                    ('processing', 'Обрабатывается'), 
                    ('completed', 'Завершено'), 
                    ('failed', 'Ошибка')
                ], 
                default='queue', 
                max_length=20, 
                verbose_name='Статус обработки'
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='processing_started_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Начало обработки'),
        ),
        migrations.AddField(
            model_name='document',
            name='processing_completed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Завершение обработки'),
        ),
        migrations.AddField(
            model_name='document',
            name='processing_error',
            field=models.TextField(blank=True, null=True, verbose_name='Ошибка обработки'),
        ),
        migrations.AddField(
            model_name='document',
            name='detailed_analysis',
            field=models.JSONField(blank=True, null=True, verbose_name='Детальный анализ плагиата'),
        ),
    ]
