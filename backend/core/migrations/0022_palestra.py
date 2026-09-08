import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_alpinista_musica_e_funcao_violeiro'),
    ]

    operations = [
        migrations.CreateModel(
            name='Palestra',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('titulo', models.CharField(max_length=255)),
                (
                    'alpinista',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='palestras',
                        to='core.alpinista',
                    ),
                ),
                (
                    'encontro',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='palestras',
                        to='core.encontro',
                    ),
                ),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('alpinista', 'encontro', 'titulo'),
                        name='unica_palestra_por_alpinista_encontro_titulo',
                    )
                ],
            },
        ),
    ]
