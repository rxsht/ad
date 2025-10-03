from django.db import migrations


def rename_queue(apps, schema_editor):
    Status = apps.get_model('documents', 'Status')
    try:
        s = Status.objects.get(id=1)
        s.name = 'На проверке'
        s.save()
    except Status.DoesNotExist:
        pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0014_normalize_statuses'),
    ]

    operations = [
        migrations.RunPython(rename_queue, noop),
    ]


