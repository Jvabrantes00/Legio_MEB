from django.db import migrations, models

import core.validators


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0041_inscricaoencontro_dadosesppainscricao_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='responsaveldeclaradoinscricao',
            name='cpf',
            field=models.CharField(
                blank=True,
                max_length=14,
                null=True,
                validators=[core.validators.validate_cpf],
            ),
        ),
    ]
