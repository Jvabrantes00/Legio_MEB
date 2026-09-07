from django.db import migrations


SIA_ROLE_NAMES = (
    'Suporte',
    'Diretoria',
    'Fichas',
    'MME',
    'Formação',
    'Secretaria',
    'Ação Social',
    'Liturgia',
    'Eventos',
    'Comunicação',
)


def create_sia_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for role_name in SIA_ROLE_NAMES:
        Group.objects.get_or_create(name=role_name)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0018_alter_alpinista_cpf'),
    ]

    operations = [
        migrations.RunPython(
            create_sia_role_groups,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
