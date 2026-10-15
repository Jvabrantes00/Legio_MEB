import hashlib
import os
import re
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Min
from django.utils import timezone

from core.models import (
    AtendimentoPreEncontro,
    ConfiguracaoEncontristasEncontro,
    DadosDeclaradosInscricao,
    DadosEsppaInscricao,
    DiaEncontro,
    Encontro,
    InscricaoEncontro,
)
from core.serializers import SubmissaoInscricaoPublicaSerializer
from core.services.inscricoes_encontro import (
    _idade_em as calcular_idade,
    submeter_inscricao_encontro,
)


SEED_ENVIRONMENT = 'development'
SEED_EMAIL_DOMAIN = 'example.test'
SEED_EMAIL_PREFIX = 'workspace.seed'

_NOMES = (
    'Ana Beatriz', 'Lucas Henrique', 'Mariana', 'Gabriel', 'Júlia',
    'Pedro Henrique', 'Larissa', 'Rafael', 'Camila', 'Matheus',
    'Beatriz', 'João Victor', 'Isabela', 'Felipe', 'Amanda',
    'Gustavo', 'Letícia', 'Bruno', 'Sofia', 'Daniel',
)
_SOBRENOMES = (
    'Souza', 'Almeida', 'Oliveira Costa', 'Fernandes Lima',
    'Carvalho Rocha', 'Martins', 'Ribeiro Alves', 'Gomes Ferreira',
    'Mendes Silva', 'Rodrigues Pereira', 'Moreira Santos', 'Araújo',
    'Castro Nunes', 'Barbosa Melo', 'Freitas Lopes', 'Correia Ramos',
    'Vieira Monteiro', 'Teixeira Moraes', 'Cardoso Pires', 'Farias Cunha',
)
_BAIRROS = ('Centro', 'Asa Norte', 'Asa Sul', 'Lago Norte', 'Taguatinga')


def _exigir_ambiente_desenvolvimento():
    environment = os.getenv('SIA_ENVIRONMENT', '').strip().lower()
    if not settings.DEBUG or environment != SEED_ENVIRONMENT:
        raise CommandError(
            'seed_inscricoes_workspace é bloqueado fora do desenvolvimento. '
            'Exige DEBUG=True e SIA_ENVIRONMENT=development.'
        )


def _resolver_encontro(raw_id):
    try:
        encontro_id = int(str(raw_id))
    except (TypeError, ValueError) as error:
        raise CommandError('--encontro-id deve ser um ID inteiro válido.') from error
    if encontro_id <= 0:
        raise CommandError('--encontro-id deve ser um ID inteiro positivo.')
    try:
        return Encontro.objects.get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise CommandError(
            f'Encontro {encontro_id} não encontrado.'
        ) from error


def _contexto_encontro(encontro):
    try:
        configuracao = encontro.configuracao_encontristas
    except ConfiguracaoEncontristasEncontro.DoesNotExist as error:
        raise CommandError(
            'O Encontro não possui ConfiguracaoEncontristasEncontro. '
            'Configure inscrições antes de executar a seed.'
        ) from error
    primeiro_dia = (
        DiaEncontro.objects
        .filter(
            calendario__encontro=encontro,
            calendario__vigente=True,
            calendario__oficializado_em__isnull=False,
        )
        .aggregate(data=Min('data'))['data']
    )
    if primeiro_dia is None:
        raise CommandError(
            'O Encontro não possui calendário oficial vigente com dias.'
        )
    if encontro.tipo not in {Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA}:
        raise CommandError(
            'A inscrição pública existe somente para Escalada e ESPPA.'
        )
    return configuracao, primeiro_dia


def _email_seed(encontro_id, indice):
    return (
        f'{SEED_EMAIL_PREFIX}.{encontro_id}.{indice:04d}'
        f'@{SEED_EMAIL_DOMAIN}'
    )


def _queryset_marcadores(encontro):
    prefixo = f'{SEED_EMAIL_PREFIX}.{encontro.pk}.'
    padrao = re.compile(
        rf'^{re.escape(prefixo)}\d{{4,}}@{re.escape(SEED_EMAIL_DOMAIN)}$'
    )
    candidatos = (
        DadosDeclaradosInscricao.objects
        .filter(
            inscricao__encontro=encontro,
            email__startswith=prefixo,
            email__endswith=f'@{SEED_EMAIL_DOMAIN}',
        )
        .select_related('inscricao')
    )
    return [item for item in candidatos if padrao.fullmatch(item.email)]


def _cpf_sintetico(encontro_id, indice):
    digest = hashlib.sha256(
        f'workspace-seed:{encontro_id}:{indice}:responsavel'.encode()
    ).hexdigest()
    base = f'{int(digest[:12], 16) % 1_000_000_000:09d}'
    if len(set(base)) == 1:
        base = f'{(int(base) + 123456789) % 1_000_000_000:09d}'
    digitos = list(base)
    for posicao in (9, 10):
        peso = posicao + 1
        total = sum(
            int(digito) * (peso - offset)
            for offset, digito in enumerate(digitos[:posicao])
        )
        resto = (total * 10) % 11
        digitos.append(str(0 if resto == 10 else resto))
    return ''.join(digitos)


def _datas_nascimento_validas(configuracao, primeiro_dia, momento):
    hoje = timezone.localdate()
    data_operacao = timezone.localtime(momento).date()
    limite_superior = min(hoje, data_operacao, primeiro_dia)
    primeiro_ano_possivel = max(
        1,
        primeiro_dia.year - configuracao.idade_maxima - 1,
    )
    cursor = date(primeiro_ano_possivel, 1, 1)
    datas = []
    while cursor <= limite_superior:
        idade = calcular_idade(cursor, primeiro_dia)
        if configuracao.idade_minima <= idade <= configuracao.idade_maxima:
            datas.append(cursor)
        cursor += timedelta(days=1)
    if not datas:
        raise CommandError(
            'Não existe data de nascimento válida para a configuração atual '
            'do Encontro.'
        )
    return tuple(datas)


def _data_nascimento(datas_validas, indice):
    # Passo primo distribui os registros pela faixa sem depender da quantidade.
    return datas_validas[((indice - 1) * 137) % len(datas_validas)]


def _momento_seed(configuracao):
    agora = timezone.now()
    if configuracao.inscricoes_abrem_em <= agora <= configuracao.inscricoes_encerram_em:
        return agora
    return configuracao.inscricoes_abrem_em + (
        configuracao.inscricoes_encerram_em
        - configuracao.inscricoes_abrem_em
    ) / 2


def _nome(indice):
    nome = _NOMES[(indice - 1) % len(_NOMES)]
    sobrenome = _SOBRENOMES[((indice - 1) // len(_NOMES)) % len(_SOBRENOMES)]
    segundo = _SOBRENOMES[(indice * 7) % len(_SOBRENOMES)]
    return f'{nome} {sobrenome} {segundo}'


def _dados_esppa(indice):
    estados = tuple(DadosEsppaInscricao.EstadoCivil.values)
    estado = estados[(indice - 1) % len(estados)]
    if estado == DadosEsppaInscricao.EstadoCivil.CASADO:
        return {
            'estado_civil': estado,
            'nome_conjuge': f'Cônjuge Fictício {indice:02d}',
            'telefone_conjuge': f'610001{indice:05d}',
            'nome_referencia': '',
            'relacao_referencia': '',
            'telefone_referencia': '',
        }
    return {
        'estado_civil': estado,
        'nome_conjuge': '',
        'telefone_conjuge': '',
        'nome_referencia': f'Referência Fictícia {indice:02d}',
        'relacao_referencia': (
            DadosEsppaInscricao.RelacaoReferencia.AMIGO
            if indice % 2 else DadosEsppaInscricao.RelacaoReferencia.OUTRO_FAMILIAR
        ),
        'telefone_referencia': f'610002{indice:05d}',
    }


def _payload(encontro, datas_nascimento, primeiro_dia, indice):
    nascimento = _data_nascimento(datas_nascimento, indice)
    idade = calcular_idade(nascimento, primeiro_dia)
    como_conheceu = tuple(DadosDeclaradosInscricao.ComoConheceu.values)[
        (indice - 1) % len(DadosDeclaradosInscricao.ComoConheceu.values)
    ]
    sacramentos = tuple(DadosDeclaradosInscricao.Sacramento.values)
    payload = {
        'dados_declarados': {
            'nome_completo': _nome(indice),
            'apelido': _NOMES[(indice - 1) % len(_NOMES)] if indice % 3 == 0 else '',
            'data_nascimento': nascimento,
            'cpf': None,
            'email': _email_seed(encontro.pk, indice),
            'telefone_whatsapp': f'610000{indice:05d}',
            'cep': f'700{indice % 100:02d}-{indice % 1000:03d}',
            'logradouro': f'Rua Fictícia {((indice - 1) % 12) + 1}',
            'numero': str(100 + indice),
            'complemento': f'Bloco {indice % 5 + 1}' if indice % 4 == 0 else '',
            'bairro': _BAIRROS[(indice - 1) % len(_BAIRROS)],
            'cidade': 'Brasília',
            'uf': 'DF',
            'como_conheceu': como_conheceu,
            'como_conheceu_outro': (
                'Atividade comunitária fictícia'
                if como_conheceu == DadosDeclaradosInscricao.ComoConheceu.OUTRO
                else ''
            ),
            'batismo': sacramentos[(indice - 1) % len(sacramentos)],
            'primeira_comunhao': sacramentos[indice % len(sacramentos)],
            'crisma': sacramentos[(indice + 1) % len(sacramentos)],
        },
        'dados_cuidado': None,
        'dados_esppa': (
            _dados_esppa(indice)
            if encontro.tipo == Encontro.Tipo.ESPPA else None
        ),
    }
    if idade < 18:
        payload['responsavel'] = {
            'nome_completo': f'Responsável Fictício {indice:02d}',
            'cpf': _cpf_sintetico(encontro.pk, indice),
            'parentesco': 'Responsável legal',
            'telefone_whatsapp': f'610003{indice:05d}',
            'email': '',
        }
    elif indice % 4 == 0:
        payload['responsavel'] = {
            'nome_completo': f'Contato Fictício {indice:02d}',
            'cpf': None,
            'parentesco': 'Contato de emergência',
            'telefone_whatsapp': f'610004{indice:05d}',
            'email': '',
        }
    return payload


@transaction.atomic
def _criar_seed(encontro, configuracao, primeiro_dia, quantidade):
    criadas = 0
    existentes = 0
    momento = _momento_seed(configuracao)
    datas_nascimento = _datas_nascimento_validas(
        configuracao,
        primeiro_dia,
        momento,
    )
    for indice in range(1, quantidade + 1):
        email = _email_seed(encontro.pk, indice)
        if DadosDeclaradosInscricao.objects.filter(
            inscricao__encontro=encontro,
            email=email,
        ).exists():
            existentes += 1
            continue
        serializer = SubmissaoInscricaoPublicaSerializer(
            data=_payload(encontro, datas_nascimento, primeiro_dia, indice),
        )
        if not serializer.is_valid():
            raise CommandError(
                f'Payload da inscrição seed #{indice} é inválido: '
                f'{serializer.errors}'
            )
        try:
            submeter_inscricao_encontro(
                encontro=encontro,
                origem=InscricaoEncontro.Origem.PUBLICA,
                momento=momento,
                **serializer.validated_data,
            )
        except ValidationError as error:
            raise CommandError(
                f'Não foi possível criar a inscrição seed #{indice}: '
                f'{error.message_dict}'
            ) from error
        criadas += 1
    return criadas, existentes


@transaction.atomic
def _limpar_seed(encontro):
    removidas = 0
    ignoradas = 0
    for dados in _queryset_marcadores(encontro):
        inscricao = dados.inscricao
        avancada = bool(
            inscricao.pessoa_id
            or inscricao.atendimentos_pre_encontro.exists()
            or inscricao.correspondencias_cadastrais.exists()
        )
        if avancada:
            ignoradas += 1
            continue
        inscricao.delete()
        removidas += 1
    return removidas, ignoradas


class Command(BaseCommand):
    help = 'Cria inscrições públicas não verificadas para testar o Workspace.'

    def add_arguments(self, parser):
        parser.add_argument('--encontro-id', required=True)
        parser.add_argument('--quantidade', type=int, default=25)
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Remove somente inscrições reconhecidas desta seed.',
        )

    def handle(self, *args, **options):
        del args
        _exigir_ambiente_desenvolvimento()
        encontro = _resolver_encontro(options['encontro_id'])
        if options['limpar']:
            removidas, ignoradas = _limpar_seed(encontro)
            self.stdout.write(self.style.SUCCESS(
                f'Seed Workspace — Encontro {encontro.pk}',
            ))
            self.stdout.write(f'Removidas: {removidas}')
            self.stdout.write(self.style.WARNING(
                f'Ignoradas por avanço operacional: {ignoradas}',
            ))
            return
        quantidade = options['quantidade']
        if quantidade <= 0:
            raise CommandError('--quantidade deve ser maior que zero.')
        configuracao, primeiro_dia = _contexto_encontro(encontro)
        criadas, existentes = _criar_seed(
            encontro,
            configuracao,
            primeiro_dia,
            quantidade,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Seed Workspace — Encontro {encontro.pk}',
        ))
        self.stdout.write(f'Inscrições solicitadas: {quantidade}')
        self.stdout.write(f'Criadas: {criadas}')
        self.stdout.write(f'Já existentes: {existentes}')
        self.stdout.write('Ignoradas: 0')
        self.stdout.write('Nenhuma Pessoa criada.')
        self.stdout.write('Nenhum AtendimentoPreEncontro criado.')
        self.stdout.write('Nenhum check-in criado.')
