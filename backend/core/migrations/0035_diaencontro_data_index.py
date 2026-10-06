from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_expand_propostas_violeiros'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='diaencontro',
            index=models.Index(
                fields=['data'],
                name='dia_encontro_data_idx',
            ),
        ),
    ]
