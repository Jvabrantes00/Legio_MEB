import os


# Valores exclusivos da suíte. Não são credenciais de desenvolvimento ou produção.
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-only-key-not-for-production')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'testserver,localhost')
os.environ.setdefault('POSTGRES_DB', 'unused_in_tests')
os.environ.setdefault('POSTGRES_USER', 'unused_in_tests')
os.environ.setdefault('POSTGRES_PASSWORD', 'unused_in_tests')

from .settings import *  # noqa: E402,F403


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

ALLOWED_HOSTS = ['testserver', 'localhost']

# Senhas continuam passando pelo mecanismo do Django, mas com um hasher rápido
# apropriado para dados descartáveis de teste.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
