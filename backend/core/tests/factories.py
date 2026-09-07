from datetime import date
from itertools import count

from core.models import Alpinista, Encontro, Evento, FuncaoEncontro


_sequence = count(1)


def make_alpinista(**overrides):
    number = next(_sequence)
    values = {
        'nome': f'Alpinista {number}',
        'email': f'alpinista{number}@example.test',
        'telefone': f'610000{number:04d}',
        'status': 'pendente',
    }
    values.update(overrides)
    return Alpinista.objects.create(**values)


def make_encontro(**overrides):
    number = next(_sequence)
    values = {
        'encontro': f'Escalada {number}',
        'tipo': 'Escalada',
        'data_referencia': date(2030, 1, 1),
        'data_exato': '1 de janeiro de 2030',
        'local': 'Local de teste',
        'status': 'agendado',
    }
    values.update(overrides)
    return Encontro.objects.create(**values)


def make_evento(**overrides):
    number = next(_sequence)
    values = {
        'nome': f'Evento {number}',
        'data_evento': date(2030, 1, 1),
        'local': 'Local de teste',
    }
    values.update(overrides)
    return Evento.objects.create(**values)


def make_funcao(**overrides):
    number = next(_sequence)
    values = {
        'nome': f'Função {number}',
        'tipo': 'equipe',
    }
    values.update(overrides)
    return FuncaoEncontro.objects.create(**values)
