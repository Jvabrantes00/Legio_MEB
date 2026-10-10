from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_expand_campanha_convites'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventoauditoriaencontro',
            name='ator',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.PROTECT,
                related_name='eventos_auditoria_encontro',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
