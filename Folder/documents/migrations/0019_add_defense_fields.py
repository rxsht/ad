from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0018_update_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='on_defense',
            field=models.BooleanField(default=False, verbose_name='На защите'),
        ),
        migrations.AddField(
            model_name='document',
            name='sent_to_defense_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата отправки на защиту'),
        ),
    ]

