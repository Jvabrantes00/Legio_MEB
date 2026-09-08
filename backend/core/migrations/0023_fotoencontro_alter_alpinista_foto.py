import django.db.models.deletion
from django.db import migrations, models

import core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_palestra'),
    ]

    operations = [
        migrations.CreateModel(
            name='FotoEncontro',
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
                (
                    'imagem',
                    models.ImageField(
                        upload_to='encontros/',
                        validators=[core.validators.validate_image_upload_size],
                    ),
                ),
                (
                    'encontro',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='fotos',
                        to='core.encontro',
                    ),
                ),
            ],
            options={'ordering': ['id']},
        ),
        migrations.AlterField(
            model_name='alpinista',
            name='foto',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='fotos/',
                validators=[core.validators.validate_image_upload_size],
            ),
        ),
    ]
