from django.db import migrations


def add_default_types(apps, schema_editor):
    Type = apps.get_model('documents', 'Type')
    for name in [
        'курсач',
        'диплом',
        'эссе',
    ]:
        Type.objects.get_or_create(name=name)


def remove_default_types(apps, schema_editor):
    Type = apps.get_model('documents', 'Type')
    Type.objects.filter(name__in=['курсач', 'диплом', 'эссе']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0012_documentbatch_documentvector_documentsimilarity_and_more'),
    ]

    operations = [
        migrations.RunPython(add_default_types, remove_default_types),
    ]


