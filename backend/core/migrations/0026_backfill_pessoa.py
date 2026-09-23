from django.core.management.color import no_style
from django.db import migrations, models


def _has_text(value):
    return value is not None and str(value).strip() != ''


def _reset_pessoa_sequence(Pessoa, schema_editor):
    connection = schema_editor.connection
    statements = connection.ops.sequence_reset_sql(no_style(), [Pessoa])
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def backfill_pessoas(apps, schema_editor):
    Alpinista = apps.get_model('core', 'Alpinista')
    DadosSaudePessoa = apps.get_model('core', 'DadosSaudePessoa')
    Pessoa = apps.get_model('core', 'Pessoa')
    ResponsavelPessoa = apps.get_model('core', 'ResponsavelPessoa')
    TelefonePessoa = apps.get_model('core', 'TelefonePessoa')
    db_alias = schema_editor.connection.alias

    alpinistas = (
        Alpinista.objects.using(db_alias)
        .all()
        .order_by('pk')
        .iterator()
    )
    for alpinista in alpinistas:
        if alpinista.pessoa_id is not None:
            continue

        if Pessoa.objects.using(db_alias).filter(pk=alpinista.pk).exists():
            raise RuntimeError(
                'Pessoa preexistente conflita com o ID de Alpinista '
                f'{alpinista.pk}; backfill interrompido sem vincular registros.'
            )

        foto_name = alpinista.foto.name if alpinista.foto else None
        pessoa = Pessoa(
            id=alpinista.pk,
            nome=alpinista.nome,
            data_nascimento=alpinista.dataNascimento,
            cpf=alpinista.cpf or None,
            email=alpinista.email or None,
            foto=foto_name,
            batismo=alpinista.batizado,
            primeira_comunhao=alpinista.primeira_comunhao,
            crisma=alpinista.crismado,
        )
        pessoa.save(force_insert=True, using=db_alias)

        if _has_text(alpinista.telefone):
            TelefonePessoa.objects.using(db_alias).create(
                pessoa_id=pessoa.pk,
                numero=alpinista.telefone,
            )

        for nome, telefone, parentesco in (
            (alpinista.nomePai, alpinista.telefonePai, 'pai'),
            (alpinista.nomeMae, alpinista.telefoneMae, 'mãe'),
        ):
            if _has_text(nome):
                ResponsavelPessoa.objects.using(db_alias).create(
                    pessoa_id=pessoa.pk,
                    nome=nome,
                    parentesco=parentesco,
                    telefone=telefone if _has_text(telefone) else '',
                )

        medicamentos = (
            alpinista.medicacao if _has_text(alpinista.medicacao) else ''
        )
        neurodivergencia = (
            alpinista.tipo_neurodivergente
            if (
                alpinista.is_neurodivergente
                and _has_text(alpinista.tipo_neurodivergente)
            )
            else ''
        )
        if medicamentos or neurodivergencia:
            DadosSaudePessoa.objects.using(db_alias).create(
                pessoa_id=pessoa.pk,
                medicamentos=medicamentos,
                neurodivergencia=neurodivergencia,
            )

        Alpinista.objects.using(db_alias).filter(
            pk=alpinista.pk,
            pessoa_id__isnull=True,
        ).update(pessoa_id=pessoa.pk)

    _reset_pessoa_sequence(Pessoa, schema_editor)


def reverse_backfill_pessoas(apps, schema_editor):
    Alpinista = apps.get_model('core', 'Alpinista')
    DadosSaudePessoa = apps.get_model('core', 'DadosSaudePessoa')
    EnderecoPessoa = apps.get_model('core', 'EnderecoPessoa')
    PerfilAlpinista = apps.get_model('core', 'PerfilAlpinista')
    Pessoa = apps.get_model('core', 'Pessoa')
    ResponsavelPessoa = apps.get_model('core', 'ResponsavelPessoa')
    TelefonePessoa = apps.get_model('core', 'TelefonePessoa')
    VinculoConjugal = apps.get_model('core', 'VinculoConjugal')
    db_alias = schema_editor.connection.alias

    pessoa_ids = list(
        Alpinista.objects.using(db_alias)
        .exclude(pessoa_id=None)
        .values_list('pessoa_id', flat=True)
    )
    if not pessoa_ids:
        return

    Alpinista.objects.using(db_alias).filter(
        pessoa_id__in=pessoa_ids
    ).update(pessoa_id=None)

    VinculoConjugal.objects.using(db_alias).filter(
        models.Q(pessoa_a_id__in=pessoa_ids)
        | models.Q(pessoa_b_id__in=pessoa_ids)
    ).delete()
    PerfilAlpinista.objects.using(db_alias).filter(
        pessoa_id__in=pessoa_ids
    ).delete()
    DadosSaudePessoa.objects.using(db_alias).filter(
        pessoa_id__in=pessoa_ids
    ).delete()
    EnderecoPessoa.objects.using(db_alias).filter(
        pessoa_id__in=pessoa_ids
    ).delete()
    ResponsavelPessoa.objects.using(db_alias).filter(
        pessoa_id__in=pessoa_ids
    ).delete()
    TelefonePessoa.objects.using(db_alias).filter(
        pessoa_id__in=pessoa_ids
    ).delete()
    Pessoa.objects.using(db_alias).filter(pk__in=pessoa_ids).delete()

    _reset_pessoa_sequence(Pessoa, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_expand_pessoa'),
    ]

    operations = [
        migrations.RunPython(
            backfill_pessoas,
            reverse_backfill_pessoas,
        ),
    ]
