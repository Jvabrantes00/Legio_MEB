from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0048_conferenciacuidadopreencontro'),
    ]

    operations = [
        migrations.AddField(
            model_name='calendarioencontro',
            name='pre_encontro_data',
            field=models.DateField(blank=True, null=True),
        ),
    ]
