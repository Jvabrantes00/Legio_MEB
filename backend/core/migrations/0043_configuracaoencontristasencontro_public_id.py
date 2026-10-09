import uuid

from django.db import migrations, models


def preencher_public_ids(apps, schema_editor):
    ConfiguracaoEncontristasEncontro = apps.get_model(
        'core',
        'ConfiguracaoEncontristasEncontro',
    )
    public_ids_usados = set(
        ConfiguracaoEncontristasEncontro.objects
        .exclude(public_id__isnull=True)
        .values_list('public_id', flat=True)
    )
    for configuracao in (
        ConfiguracaoEncontristasEncontro.objects
        .filter(public_id__isnull=True)
        .iterator()
    ):
        public_id = uuid.uuid4()
        while public_id in public_ids_usados:
            public_id = uuid.uuid4()
        configuracao.public_id = public_id
        configuracao.save(update_fields=['public_id'])
        public_ids_usados.add(public_id)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0042_alter_responsaveldeclaradoinscricao_cpf'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaoencontristasencontro',
            name='public_id',
            field=models.UUIDField(
                editable=False,
                null=True,
            ),
        ),
        migrations.RunPython(
            preencher_public_ids,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='configuracaoencontristasencontro',
            name='public_id',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]
