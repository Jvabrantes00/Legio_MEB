from django.db import migrations


CANONICAL_STATUSES = (
    'pendente',
    'ativo',
    'confirmado',
    'inativo',
)


def normalize_alpinista_status(apps, schema_editor):
    Alpinista = apps.get_model('core', 'Alpinista')

    for canonical_status in CANONICAL_STATUSES:
        (
            Alpinista.objects
            .filter(status__iexact=canonical_status)
            .exclude(status=canonical_status)
            .update(status=canonical_status)
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_alter_alpinista_status'),
    ]

    operations = [
        migrations.RunPython(
            normalize_alpinista_status,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
