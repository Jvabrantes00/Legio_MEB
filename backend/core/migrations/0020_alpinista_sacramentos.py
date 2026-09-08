from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_create_sia_role_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='alpinista',
            name='batizado',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='alpinista',
            name='crismado',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='alpinista',
            name='primeira_comunhao',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
