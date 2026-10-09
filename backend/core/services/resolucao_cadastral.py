from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    CorrespondenciaCadastralInscricao,
    DadosCuidadoInscricao,
    DadosDeclaradosInscricao,
    DadosSaudePessoa,
    EnderecoPessoa,
    InscricaoEncontro,
    Pessoa,
    TelefonePessoa,
)
from core.permissions import pode_resolver_cadastro_inscricao
from core.services.auditoria_encontros import (
    registrar_evento_auditoria_encontro,
)


class ErroResolucaoCadastral(ValidationError):
    pass


@dataclass(frozen=True)
class ResultadoAplicacaoCadastral:
    pessoa: Pessoa
    campos_alterados: tuple[str, ...]


CAMPOS_APLICAVEIS = frozenset({
    'nome',
    'apelido',
    'data_nascimento',
    'cpf',
    'email',
    'telefone',
    'endereco',
    'sacramentos',
    'alergias',
    'medicamentos',
    'neurodivergencia',
})

_CAMPOS_AUDITORIA_DECISAO = frozenset({
    'status',
    'inscricao_id',
    'pessoa_id',
    'correspondencia_id',
})
_CAMPOS_AUDITORIA_APLICACAO = frozenset({
    'inscricao_id',
    'pessoa_id',
    'campos_aplicados',
})
_SACRAMENTOS = {
    'batismo': 'batismo',
    'primeira_comunhao': 'primeira_comunhao',
    'crisma': 'crisma',
}


def _erro(campo, mensagem):
    raise ErroResolucaoCadastral({campo: [mensagem]})


def _exigir_permissao(usuario):
    if not pode_resolver_cadastro_inscricao(usuario):
        raise PermissionDenied(
            'Seu usuário não pode resolver cadastros de inscrições.'
        )


def _inscricao_persistida(inscricao, *, bloquear=False):
    if inscricao is None or inscricao.pk is None:
        _erro('inscricao', 'Inscrição deve estar persistida.')
    queryset = InscricaoEncontro.objects.select_related(
        'encontro',
        'pessoa',
        'dados_declarados',
    )
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        inscricao = queryset.get(pk=inscricao.pk)
    except InscricaoEncontro.DoesNotExist:
        _erro('inscricao', 'Inscrição não encontrada.')
    if not hasattr(inscricao, 'dados_declarados'):
        _erro('dados_declarados', 'A inscrição não possui ficha declarada.')
    return inscricao


def _correspondencia_persistida(
    correspondencia,
    *,
    inscricao,
    bloquear=False,
):
    if correspondencia is None or correspondencia.pk is None:
        _erro('correspondencia', 'Correspondência deve estar persistida.')
    queryset = CorrespondenciaCadastralInscricao.objects.select_related(
        'pessoa_candidata',
    )
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        correspondencia = queryset.get(pk=correspondencia.pk)
    except CorrespondenciaCadastralInscricao.DoesNotExist:
        _erro('correspondencia', 'Correspondência não encontrada.')
    if correspondencia.inscricao_id != inscricao.pk:
        _erro(
            'correspondencia',
            'A correspondência não pertence à inscrição informada.',
        )
    return correspondencia


def _campos_selecionados(campos, *, exigir_nome=False):
    if not isinstance(campos, (list, tuple, set, frozenset)):
        _erro('campos', 'Informe uma lista de campos selecionados.')
    if not all(isinstance(campo, str) for campo in campos):
        _erro('campos', 'A seleção possui campo inválido.')
    selecionados = frozenset(campos)
    desconhecidos = selecionados - CAMPOS_APLICAVEIS
    if desconhecidos:
        _erro(
            'campos',
            'Campos não suportados: ' + ', '.join(sorted(desconhecidos)) + '.',
        )
    if not selecionados:
        _erro('campos', 'Selecione ao menos um campo.')
    if exigir_nome and 'nome' not in selecionados:
        _erro('campos', 'A criação de Pessoa exige o campo nome.')
    return selecionados


def _cpf_formatado(cpf):
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


def _auditar(
    *,
    inscricao,
    usuario,
    fato,
    entidade,
    objeto_id,
    anterior,
    novo,
    campos_permitidos,
):
    return registrar_evento_auditoria_encontro(
        encontro=inscricao.encontro,
        ator=usuario,
        fato=fato,
        entidade=entidade,
        objeto_id=objeto_id,
        valor_anterior=anterior,
        valor_novo=novo,
        campos_permitidos=campos_permitidos,
    )


def consultar_correspondencias_cadastrais(*, usuario, inscricao):
    _exigir_permissao(usuario)
    inscricao = _inscricao_persistida(inscricao)
    return (
        CorrespondenciaCadastralInscricao.objects
        .filter(inscricao=inscricao)
        .select_related('pessoa_candidata', 'decidida_por')
        .prefetch_related('pessoa_candidata__telefones')
        .order_by('id')
    )


@transaction.atomic
def gerar_sugestoes_cadastrais(*, usuario, inscricao):
    _exigir_permissao(usuario)
    inscricao = _inscricao_persistida(inscricao, bloquear=True)
    cpf = inscricao.dados_declarados.cpf
    if cpf:
        candidatas = Pessoa.objects.filter(
            cpf__in=(cpf, _cpf_formatado(cpf)),
        ).order_by('id')
        for candidata in candidatas:
            CorrespondenciaCadastralInscricao.objects.get_or_create(
                inscricao=inscricao,
                pessoa_candidata=candidata,
                defaults={'origem_sinal': 'cpf_exato'},
            )
    return consultar_correspondencias_cadastrais(
        usuario=usuario,
        inscricao=inscricao,
    )


def _conflito_pessoa_encontro(inscricao, pessoa):
    return (
        InscricaoEncontro.objects
        .select_for_update()
        .filter(encontro=inscricao.encontro, pessoa=pessoa)
        .exclude(pk=inscricao.pk)
        .exists()
    )


def _exigir_sem_conflito(inscricao, pessoa):
    if _conflito_pessoa_encontro(inscricao, pessoa):
        _erro(
            'pessoa',
            'A Pessoa já está vinculada a outra inscrição deste Encontro; '
            'o conflito exige resolução humana.',
        )


@transaction.atomic
def aceitar_correspondencia_cadastral(
    *,
    usuario,
    inscricao,
    correspondencia,
    momento=None,
):
    _exigir_permissao(usuario)
    inscricao = _inscricao_persistida(inscricao, bloquear=True)
    correspondencia = _correspondencia_persistida(
        correspondencia,
        inscricao=inscricao,
        bloquear=True,
    )
    pessoa = correspondencia.pessoa_candidata

    if correspondencia.status == correspondencia.Status.REJEITADA:
        _erro(
            'correspondencia',
            'Correspondência rejeitada não pode ser aceita sem correção '
            'explícita da decisão.',
        )
    if correspondencia.status == correspondencia.Status.ACEITA:
        if inscricao.pessoa_id == pessoa.pk:
            return correspondencia
        _erro('correspondencia', 'A decisão aceita está inconsistente.')
    if inscricao.pessoa_id not in (None, pessoa.pk):
        _erro('pessoa', 'A inscrição já está associada a outra Pessoa.')
    if (
        CorrespondenciaCadastralInscricao.objects
        .select_for_update()
        .filter(inscricao=inscricao, status=correspondencia.Status.ACEITA)
        .exclude(pk=correspondencia.pk)
        .exists()
    ):
        _erro('correspondencia', 'A inscrição já possui correspondência aceita.')
    _exigir_sem_conflito(inscricao, pessoa)
    instante = momento or timezone.now()

    try:
        with transaction.atomic():
            inscricao.pessoa = pessoa
            inscricao.save(update_fields=['pessoa', 'atualizada_em'])
            correspondencia.status = correspondencia.Status.ACEITA
            correspondencia.decidida_por = usuario
            correspondencia.decidida_em = instante
            correspondencia.save(update_fields=[
                'status',
                'decidida_por',
                'decidida_em',
                'atualizada_em',
            ])
            _auditar(
                inscricao=inscricao,
                usuario=usuario,
                fato='resolucao_cadastral.correspondencia_aceita',
                entidade='correspondencia_cadastral',
                objeto_id=correspondencia.pk,
                anterior={
                    'status': correspondencia.Status.SUGERIDA,
                    'inscricao_id': inscricao.pk,
                    'pessoa_id': pessoa.pk,
                    'correspondencia_id': correspondencia.pk,
                },
                novo={
                    'status': correspondencia.Status.ACEITA,
                    'inscricao_id': inscricao.pk,
                    'pessoa_id': pessoa.pk,
                    'correspondencia_id': correspondencia.pk,
                },
                campos_permitidos=_CAMPOS_AUDITORIA_DECISAO,
            )
            _auditar(
                inscricao=inscricao,
                usuario=usuario,
                fato='resolucao_cadastral.pessoa_associada',
                entidade='inscricao_encontro',
                objeto_id=inscricao.pk,
                anterior={'inscricao_id': inscricao.pk},
                novo={
                    'inscricao_id': inscricao.pk,
                    'pessoa_id': pessoa.pk,
                },
                campos_permitidos=_CAMPOS_AUDITORIA_DECISAO,
            )
    except IntegrityError as error:
        _erro(
            'pessoa',
            'A Pessoa já foi vinculada a outra inscrição deste Encontro.',
        )
    return correspondencia


@transaction.atomic
def rejeitar_correspondencia_cadastral(
    *,
    usuario,
    inscricao,
    correspondencia,
    momento=None,
):
    _exigir_permissao(usuario)
    inscricao = _inscricao_persistida(inscricao, bloquear=True)
    correspondencia = _correspondencia_persistida(
        correspondencia,
        inscricao=inscricao,
        bloquear=True,
    )
    if correspondencia.status == correspondencia.Status.ACEITA:
        _erro(
            'correspondencia',
            'Correspondência aceita não pode ser rejeitada sem correção '
            'explícita da decisão.',
        )
    if correspondencia.status == correspondencia.Status.REJEITADA:
        return correspondencia

    correspondencia.status = correspondencia.Status.REJEITADA
    correspondencia.decidida_por = usuario
    correspondencia.decidida_em = momento or timezone.now()
    correspondencia.save(update_fields=[
        'status',
        'decidida_por',
        'decidida_em',
        'atualizada_em',
    ])
    _auditar(
        inscricao=inscricao,
        usuario=usuario,
        fato='resolucao_cadastral.correspondencia_rejeitada',
        entidade='correspondencia_cadastral',
        objeto_id=correspondencia.pk,
        anterior={
            'status': correspondencia.Status.SUGERIDA,
            'inscricao_id': inscricao.pk,
            'pessoa_id': correspondencia.pessoa_candidata_id,
            'correspondencia_id': correspondencia.pk,
        },
        novo={
            'status': correspondencia.Status.REJEITADA,
            'inscricao_id': inscricao.pk,
            'pessoa_id': correspondencia.pessoa_candidata_id,
            'correspondencia_id': correspondencia.pk,
        },
        campos_permitidos=_CAMPOS_AUDITORIA_DECISAO,
    )
    return correspondencia


def _valor_declarado(dados, campo):
    return getattr(dados, campo)


def _aplicar_campos_pessoa(pessoa, dados, selecionados):
    alterados = []
    mapeamento = {
        'nome': ('nome', _valor_declarado(dados, 'nome_completo')),
        'apelido': ('apelido', _valor_declarado(dados, 'apelido')),
        'data_nascimento': (
            'data_nascimento',
            _valor_declarado(dados, 'data_nascimento'),
        ),
        'cpf': ('cpf', _valor_declarado(dados, 'cpf')),
        'email': ('email', _valor_declarado(dados, 'email')),
    }
    for selecionado, (campo_pessoa, valor) in mapeamento.items():
        if selecionado not in selecionados or valor in (None, ''):
            continue
        if getattr(pessoa, campo_pessoa) != valor:
            setattr(pessoa, campo_pessoa, valor)
            alterados.append(selecionado)

    if 'sacramentos' in selecionados:
        sacramentos_alterados = False
        conversao = {
            DadosDeclaradosInscricao.Sacramento.SIM: True,
            DadosDeclaradosInscricao.Sacramento.NAO: False,
        }
        for campo_declarado, campo_pessoa in _SACRAMENTOS.items():
            valor = conversao.get(getattr(dados, campo_declarado))
            if valor is None or getattr(pessoa, campo_pessoa) == valor:
                continue
            setattr(pessoa, campo_pessoa, valor)
            sacramentos_alterados = True
        if sacramentos_alterados:
            alterados.append('sacramentos')

    if alterados:
        try:
            pessoa.full_clean()
        except ValidationError as error:
            raise ErroResolucaoCadastral({
                'pessoa': ['Os dados selecionados conflitam com o cadastro.'],
            }) from error
        pessoa.save()
    return alterados


def _aplicar_telefone(pessoa, dados, selecionados, alterados):
    if 'telefone' not in selecionados or not dados.telefone_whatsapp:
        return
    _, criado = TelefonePessoa.objects.get_or_create(
        pessoa=pessoa,
        numero=dados.telefone_whatsapp,
        defaults={'whatsapp': True},
    )
    if criado:
        alterados.append('telefone')


def _aplicar_endereco(pessoa, dados, selecionados, alterados):
    if 'endereco' not in selecionados:
        return
    valores = {
        'cep': dados.cep,
        'logradouro': dados.logradouro,
        'numero': dados.numero,
        'bairro': dados.bairro,
        'cidade': dados.cidade,
        'estado': dados.uf,
    }
    if dados.complemento:
        valores['complemento'] = dados.complemento
    endereco, criado = EnderecoPessoa.objects.get_or_create(
        pessoa=pessoa,
        defaults=valores,
    )
    mudou = criado
    if not criado:
        for campo, valor in valores.items():
            if getattr(endereco, campo) != valor:
                setattr(endereco, campo, valor)
                mudou = True
        if mudou:
            endereco.full_clean()
            endereco.save()
    if mudou:
        alterados.append('endereco')


def _aplicar_cuidado(pessoa, inscricao, selecionados, alterados):
    campos = {
        'alergias': ('alergias', 'alergias'),
        'medicamentos': ('medicamentos', 'medicamentos'),
        'neurodivergencia': (
            'neurodivergencia_condicao',
            'neurodivergencia',
        ),
    }
    solicitados = selecionados & campos.keys()
    if not solicitados:
        return
    try:
        declarado = inscricao.dados_cuidado
    except DadosCuidadoInscricao.DoesNotExist:
        return
    valores = {}
    selecao_por_destino = {}
    for selecionado, (origem, destino) in campos.items():
        valor = getattr(declarado, origem)
        if selecionado in solicitados and valor:
            valores[destino] = valor
            selecao_por_destino[destino] = selecionado
    if not valores:
        return
    saude, criado = DadosSaudePessoa.objects.get_or_create(
        pessoa=pessoa,
        defaults=valores,
    )
    campos_alterados = (
        list(selecao_por_destino.values())
        if criado
        else []
    )
    if not criado:
        for campo, valor in valores.items():
            if getattr(saude, campo) != valor:
                setattr(saude, campo, valor)
                campos_alterados.append(selecao_por_destino[campo])
        if campos_alterados:
            saude.full_clean()
            saude.save()
    if campos_alterados:
        alterados.extend(sorted(campos_alterados))


def _aplicar_selecao(inscricao, pessoa, selecionados):
    dados = inscricao.dados_declarados
    alterados = _aplicar_campos_pessoa(pessoa, dados, selecionados)
    _aplicar_telefone(pessoa, dados, selecionados, alterados)
    _aplicar_endereco(pessoa, dados, selecionados, alterados)
    _aplicar_cuidado(pessoa, inscricao, selecionados, alterados)
    return tuple(sorted(set(alterados)))


@transaction.atomic
def criar_pessoa_da_inscricao(*, usuario, inscricao, campos):
    _exigir_permissao(usuario)
    selecionados = _campos_selecionados(campos, exigir_nome=True)
    inscricao = _inscricao_persistida(inscricao, bloquear=True)
    if inscricao.pessoa_id is not None:
        _erro('pessoa', 'A inscrição já possui Pessoa associada.')

    pessoa = Pessoa(nome=inscricao.dados_declarados.nome_completo)
    try:
        with transaction.atomic():
            pessoa.full_clean()
            pessoa.save()
            alterados = _aplicar_selecao(inscricao, pessoa, selecionados)
            alterados = tuple(sorted(set(alterados) | {'nome'}))
            _exigir_sem_conflito(inscricao, pessoa)
            inscricao.pessoa = pessoa
            inscricao.save(update_fields=['pessoa', 'atualizada_em'])
            _auditar(
                inscricao=inscricao,
                usuario=usuario,
                fato='resolucao_cadastral.pessoa_criada',
                entidade='pessoa',
                objeto_id=pessoa.pk,
                anterior={'inscricao_id': inscricao.pk},
                novo={
                    'inscricao_id': inscricao.pk,
                    'pessoa_id': pessoa.pk,
                    'campos_aplicados': list(alterados),
                },
                campos_permitidos=(
                    _CAMPOS_AUDITORIA_DECISAO
                    | _CAMPOS_AUDITORIA_APLICACAO
                ),
            )
            _auditar(
                inscricao=inscricao,
                usuario=usuario,
                fato='resolucao_cadastral.pessoa_associada',
                entidade='inscricao_encontro',
                objeto_id=inscricao.pk,
                anterior={'inscricao_id': inscricao.pk},
                novo={
                    'inscricao_id': inscricao.pk,
                    'pessoa_id': pessoa.pk,
                },
                campos_permitidos=_CAMPOS_AUDITORIA_DECISAO,
            )
    except (IntegrityError, ValidationError) as error:
        if isinstance(error, ErroResolucaoCadastral):
            raise
        _erro(
            'pessoa',
            'Não foi possível criar a Pessoa com os campos selecionados.',
        )
    return pessoa


@transaction.atomic
def aplicar_dados_declarados(*, usuario, inscricao, campos):
    _exigir_permissao(usuario)
    selecionados = _campos_selecionados(campos)
    inscricao = _inscricao_persistida(inscricao, bloquear=True)
    if inscricao.pessoa_id is None:
        _erro('pessoa', 'Resolva a Pessoa da inscrição antes de aplicar dados.')
    pessoa = Pessoa.objects.select_for_update().get(pk=inscricao.pessoa_id)
    snapshot_antes = inscricao.dados_declarados.snapshot_atual
    try:
        with transaction.atomic():
            alterados = _aplicar_selecao(inscricao, pessoa, selecionados)
            if alterados:
                _auditar(
                    inscricao=inscricao,
                    usuario=usuario,
                    fato='resolucao_cadastral.campos_aplicados',
                    entidade='pessoa',
                    objeto_id=pessoa.pk,
                    anterior={
                        'inscricao_id': inscricao.pk,
                        'pessoa_id': pessoa.pk,
                        'campos_aplicados': [],
                    },
                    novo={
                        'inscricao_id': inscricao.pk,
                        'pessoa_id': pessoa.pk,
                        'campos_aplicados': list(alterados),
                    },
                    campos_permitidos=_CAMPOS_AUDITORIA_APLICACAO,
                )
    except IntegrityError as error:
        _erro(
            'pessoa',
            'Os dados selecionados conflitam com outro cadastro.',
        )
    inscricao.dados_declarados.refresh_from_db()
    if inscricao.dados_declarados.snapshot_atual != snapshot_antes:
        raise RuntimeError('A resolução cadastral não pode alterar o snapshot.')
    return ResultadoAplicacaoCadastral(
        pessoa=pessoa,
        campos_alterados=alterados,
    )
