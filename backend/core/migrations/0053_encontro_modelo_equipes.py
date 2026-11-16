from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0052_entrega_integridade')]

    operations = [
        migrations.AddField(
            model_name='encontro',
            name='modelo_equipes',
            field=models.CharField(
                choices=[('LEGADO', 'Legado'), ('CANONICO', 'Canônico')],
                db_default='LEGADO', default='LEGADO', max_length=8,
            ),
        ),
        migrations.AddConstraint(
            model_name='encontro',
            constraint=models.CheckConstraint(
                condition=models.Q(modelo_equipes__in=('LEGADO', 'CANONICO')),
                name='encontro_modelo_equipes_valido',
            ),
        ),
    ]
