from django.db import migrations


def rename_review_to_defense(apps, schema_editor):
    Status = apps.get_model('documents', 'Status')
    try:
        s = Status.objects.get(id=1)
        # Используем unicode escape чтобы избежать проблем с кодировкой
        s.name = '\u041d\u0430 \u0437\u0430\u0449\u0438\u0442\u0435'  # "На защите"
        s.save()
    except Status.DoesNotExist:
        pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0016_add_processing_fields'),
    ]

    operations = [
        migrations.RunPython(rename_review_to_defense, noop),
    ]
