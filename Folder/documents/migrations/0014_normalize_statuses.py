from django.db import migrations


def normalize_statuses(apps, schema_editor):
    Status = apps.get_model('documents', 'Status')
    # Ensure four statuses with fixed IDs
    desired = [
        (1, 'В очереди', 'queue'),
        (2, 'Проверен', 'success'),
        (3, 'Зачтен', 'accepted'),
        (4, 'Не зачтен', 'rejected'),
    ]

    for pk, name, css in desired:
        try:
            s = Status.objects.get(pk=pk)
            changed = False
            if s.name != name:
                s.name = name
                changed = True
            if s.html_clase != css:
                s.html_clase = css
                changed = True
            if changed:
                s.save()
        except Status.DoesNotExist:
            Status.objects.create(id=pk, name=name, html_clase=css)

    # Optionally map common legacy names to the new IDs
    # 'Готово' -> 'Проверен'
    try:
        legacy_ready = Status.objects.get(name='Готово')
        if legacy_ready.id != 2:
            # Repoint documents with legacy_ready to ID 2
            Document = apps.get_model('documents', 'Document')
            Document.objects.filter(status_id=legacy_ready.id).update(status_id=2)
    except Status.DoesNotExist:
        pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0013_add_default_types'),
    ]

    operations = [
        migrations.RunPython(normalize_statuses, noop),
    ]


