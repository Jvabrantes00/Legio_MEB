from django.db import migrations, models


def mark_existing_violeiro_functions(apps, schema_editor):
    FuncaoEncontro = apps.get_model('core', 'FuncaoEncontro')
    violeiro_ids = [
        funcao.pk
        for funcao in FuncaoEncontro.objects.only('pk', 'nome')
        if funcao.nome and funcao.nome.strip().casefold() == 'violeiro'
    ]
    FuncaoEncontro.objects.filter(pk__in=violeiro_ids).update(eh_violeiro=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_alpinista_sacramentos'),
    ]

    operations = [
        migrations.AddField(
            model_name='alpinista',
            name='canta',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='alpinista',
            name='eh_violeiro',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='funcaoencontro',
            name='eh_violeiro',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            mark_existing_violeiro_functions,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
