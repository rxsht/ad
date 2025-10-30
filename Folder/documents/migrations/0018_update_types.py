from django.db import migrations


def update_types(apps, schema_editor):
    Type = apps.get_model('documents', 'Type')
    # Очистить текущие типы и задать новые значения
    Type.objects.all().delete()
    Type.objects.create(name='Курсовая работа')
    Type.objects.create(name='Дипломная работа')


def reverse_update_types(apps, schema_editor):
    # Откат – оставим пустым, так как предыдущие значения неизвестны
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0017_rename_review_to_defense'),
    ]

    operations = [
        migrations.RunPython(update_types, reverse_update_types),
    ]


