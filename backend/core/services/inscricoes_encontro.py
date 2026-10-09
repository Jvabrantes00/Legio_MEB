from collections.abc import Mapping
from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Min
from django.utils import timezone

from core.models import (
    ConfiguracaoEncontristasEncontro,
    DadosCuidadoInscricao,
    DadosDeclaradosInscricao,
    DadosEsppaInscricao,
    DiaEncontro,
    Encontro,
    InscricaoEncontro,
    Pessoa,
    ResponsavelDeclaradoInscricao,
)
from core.validators import normalize_cpf


class ErroFichaInscricao(ValidationError):
    pass


_CAMPOS_PARTICIPANTE = frozenset({
    'nome_completo',
    'apelido',
    'data_nascimento',
    'cpf',
    'email',
    'telefone_whatsapp',
    'cep',
    'logradouro',
    'numero',
    'complemento',
    'bairro',
    'cidade',
    'uf',
    'como_conheceu',
    'como_conheceu_outro',
    'batismo',
    'primeira_comunhao',
    'crisma',
})
_CAMPOS_RESPONSAVEL = frozenset({
    'nome_completo',
    'cpf',
    'parentesco',
    'telefone_whatsapp',
    'email',
})
_CAMPOS_CUIDADO = frozenset({
    'possui_alergias',
    'alergias',
    'possui_restricoes_intolerancias',
    'restricoes_intolerancias',
    'usa_medicamentos',
    'medicamentos',
    'horarios_medicamentos',
    'observacoes_medicamentos',
    'neurodivergencia_apoio',
    'neurodivergencia_condicao',
    'necessidades_apoio',
    'sensibilidades_desconfortos',
    'o_que_ajuda',
    'outras_informacoes',
    'observacoes',
})
_CAMPOS_ESPPA = frozenset({
    'estado_civil',
    'nome_conjuge',
    'telefone_conjuge',
    'nome_referencia',
    'relacao_referencia',
    'telefone_referencia',
})


def _erro(campo, mensagem):
    raise ErroFichaInscricao({campo: [mensagem]})


def _mapping(payload, nome, campos):
    if not isinstance(payload, Mapping):
        _erro(nome, 'Informe os dados por campos.')
    desconhecidos = set(payload) - campos
    if desconhecidos:
        _erro(
            nome,
            'Campos desconhecidos: ' + ', '.join(sorted(desconhecidos)) + '.',
        )
    return payload


def _texto(payload, campo, *, obrigatorio=False):
    valor = payload.get(campo, '')
    if valor is None:
        valor = ''
    if not isinstance(valor, str):
        _erro(campo, 'Informe um valor textual.')
    valor = valor.strip()
    if obrigatorio and not valor:
        _erro(campo, 'Este campo é obrigatório.')
    return valor


def _cpf(payload, campo, *, obrigatorio=False):
    valor = payload.get(campo)
    if obrigatorio and not valor:
        _erro(campo, 'Este campo é obrigatório.')
    try:
        return normalize_cpf(valor)
    except ValidationError as error:
        _erro(campo, '; '.join(error.messages))


def _email(payload, campo='email'):
    valor = _texto(payload, campo).lower()
    if valor:
        try:
            validate_email(valor)
        except ValidationError as error:
            _erro(campo, '; '.join(error.messages))
    return valor


def _escolha(payload, campo, valores, *, obrigatorio=True, padrao=None):
    valor = payload.get(campo, padrao)
    if valor is None and not obrigatorio:
        return None
    if valor not in valores:
        _erro(campo, 'Escolha inválida.')
    return valor


def _momento_atual(momento):
    momento = momento or timezone.now()
    if not isinstance(momento, datetime) or timezone.is_naive(momento):
        _erro('momento', 'Informe data e hora com fuso horário.')
    return momento


def _idade_em(data_nascimento, referencia):
    return referencia.year - data_nascimento.year - (
        (referencia.month, referencia.day)
        < (data_nascimento.month, data_nascimento.day)
    )


def _normalizar_participante(payload, *, data_operacao):
    payload = _mapping(
        payload,
        'dados_declarados',
        _CAMPOS_PARTICIPANTE,
    )
    nascimento = payload.get('data_nascimento')
    if not isinstance(nascimento, date):
        _erro('data_nascimento', 'Informe uma data válida.')
    if nascimento > data_operacao:
        _erro('data_nascimento', 'A data de nascimento não pode ser futura.')

    email = _email(payload)
    telefone = _texto(payload, 'telefone_whatsapp')
    if not email and not telefone:
        _erro(
            'contato',
            'Informe pelo menos e-mail ou telefone/WhatsApp.',
        )

    como_conheceu = _escolha(
        payload,
        'como_conheceu',
        DadosDeclaradosInscricao.ComoConheceu.values,
    )
    complemento_origem = _texto(payload, 'como_conheceu_outro')
    if (
        como_conheceu == DadosDeclaradosInscricao.ComoConheceu.OUTRO
        and not complemento_origem
    ):
        _erro(
            'como_conheceu_outro',
            'Informe como conheceu o Movimento Escalada.',
        )

    sacramentos = {
        campo: _escolha(
            payload,
            campo,
            DadosDeclaradosInscricao.Sacramento.values,
            padrao=DadosDeclaradosInscricao.Sacramento.NAO_INFORMADO,
        )
        for campo in ('batismo', 'primeira_comunhao', 'crisma')
    }
    return {
        'nome_completo': _texto(payload, 'nome_completo', obrigatorio=True),
        'apelido': _texto(payload, 'apelido'),
        'data_nascimento': nascimento,
        'cpf': _cpf(payload, 'cpf'),
        'email': email,
        'telefone_whatsapp': telefone,
        'cep': _texto(payload, 'cep', obrigatorio=True),
        'logradouro': _texto(payload, 'logradouro', obrigatorio=True),
        'numero': _texto(payload, 'numero', obrigatorio=True),
        'complemento': _texto(payload, 'complemento'),
        'bairro': _texto(payload, 'bairro', obrigatorio=True),
        'cidade': _texto(payload, 'cidade', obrigatorio=True),
        'uf': _texto(payload, 'uf', obrigatorio=True).upper(),
        'como_conheceu': como_conheceu,
        'como_conheceu_outro': complemento_origem,
        **sacramentos,
    }


def _normalizar_responsavel(payload, *, cpf_obrigatorio):
    payload = _mapping(payload, 'responsavel', _CAMPOS_RESPONSAVEL)
    return {
        'nome_completo': _texto(
            payload,
            'nome_completo',
            obrigatorio=True,
        ),
        'cpf': _cpf(payload, 'cpf', obrigatorio=cpf_obrigatorio),
        'parentesco': _texto(payload, 'parentesco', obrigatorio=True),
        'telefone_whatsapp': _texto(
            payload,
            'telefone_whatsapp',
            obrigatorio=True,
        ),
        'email': _email(payload),
    }


def _normalizar_cuidado(payload):
    if payload is None:
        return None
    payload = _mapping(payload, 'dados_cuidado', _CAMPOS_CUIDADO)
    binarios = DadosCuidadoInscricao.RespostaBinaria.values
    possui_alergias = _escolha(payload, 'possui_alergias', binarios)
    possui_restricoes = _escolha(
        payload,
        'possui_restricoes_intolerancias',
        binarios,
    )
    usa_medicamentos = _escolha(payload, 'usa_medicamentos', binarios)
    neurodivergencia_apoio = _escolha(
        payload,
        'neurodivergencia_apoio',
        DadosCuidadoInscricao.RespostaApoio.values,
    )
    alergias = _texto(payload, 'alergias')
    restricoes = _texto(payload, 'restricoes_intolerancias')
    medicamentos = _texto(payload, 'medicamentos')
    horarios = _texto(payload, 'horarios_medicamentos')
    observacoes_medicamentos = _texto(
        payload,
        'observacoes_medicamentos',
    )

    if possui_alergias == DadosCuidadoInscricao.RespostaBinaria.SIM:
        if not alergias:
            _erro('alergias', 'Descreva as alergias informadas.')
    elif alergias:
        _erro('alergias', 'Não informe alergias quando a resposta for Não.')

    if possui_restricoes == DadosCuidadoInscricao.RespostaBinaria.SIM:
        if not restricoes:
            _erro(
                'restricoes_intolerancias',
                'Descreva as restrições ou intolerâncias informadas.',
            )
    elif restricoes:
        _erro(
            'restricoes_intolerancias',
            'Não informe restrições quando a resposta for Não.',
        )

    if usa_medicamentos == DadosCuidadoInscricao.RespostaBinaria.SIM:
        if not medicamentos:
            _erro('medicamentos', 'Informe os medicamentos utilizados.')
        if not horarios:
            _erro(
                'horarios_medicamentos',
                'Informe os horários dos medicamentos.',
            )
    elif medicamentos or horarios or observacoes_medicamentos:
        _erro(
            'medicamentos',
            'Não informe medicamentos quando a resposta for Não.',
        )

    return {
        'possui_alergias': possui_alergias,
        'alergias': alergias,
        'possui_restricoes_intolerancias': possui_restricoes,
        'restricoes_intolerancias': restricoes,
        'usa_medicamentos': usa_medicamentos,
        'medicamentos': medicamentos,
        'horarios_medicamentos': horarios,
        'observacoes_medicamentos': observacoes_medicamentos,
        'neurodivergencia_apoio': neurodivergencia_apoio,
        'neurodivergencia_condicao': _texto(
            payload,
            'neurodivergencia_condicao',
        ),
        'necessidades_apoio': _texto(payload, 'necessidades_apoio'),
        'sensibilidades_desconfortos': _texto(
            payload,
            'sensibilidades_desconfortos',
        ),
        'o_que_ajuda': _texto(payload, 'o_que_ajuda'),
        'outras_informacoes': _texto(payload, 'outras_informacoes'),
        'observacoes': _texto(payload, 'observacoes'),
    }


def _normalizar_esppa(payload, *, encontro):
    if encontro.tipo != Encontro.Tipo.ESPPA:
        if payload is not None:
            _erro(
                'dados_esppa',
                'Dados específicos do ESPPA não se aplicam a este Encontro.',
            )
        return None
    if payload is None:
        _erro('dados_esppa', 'Informe os dados específicos do ESPPA.')

    payload = _mapping(payload, 'dados_esppa', _CAMPOS_ESPPA)
    estado_civil = _escolha(
        payload,
        'estado_civil',
        DadosEsppaInscricao.EstadoCivil.values,
    )
    valores = {
        'estado_civil': estado_civil,
        'nome_conjuge': _texto(payload, 'nome_conjuge'),
        'telefone_conjuge': _texto(payload, 'telefone_conjuge'),
        'nome_referencia': _texto(payload, 'nome_referencia'),
        'relacao_referencia': _texto(payload, 'relacao_referencia'),
        'telefone_referencia': _texto(payload, 'telefone_referencia'),
    }
    if estado_civil == DadosEsppaInscricao.EstadoCivil.CASADO:
        if not valores['nome_conjuge'] or not valores['telefone_conjuge']:
            _erro(
                'conjuge',
                'Informe nome e telefone do cônjuge.',
            )
        if any(
            valores[campo]
            for campo in (
                'nome_referencia',
                'relacao_referencia',
                'telefone_referencia',
            )
        ):
            _erro(
                'referencia',
                'Pessoa casada não deve informar pessoa de referência.',
            )
    else:
        if valores['nome_conjuge'] or valores['telefone_conjuge']:
            _erro(
                'conjuge',
                'Cônjuge não se aplica ao estado civil informado.',
            )
        if not all(
            valores[campo]
            for campo in (
                'nome_referencia',
                'relacao_referencia',
                'telefone_referencia',
            )
        ):
            _erro(
                'referencia',
                'Informe nome, relação e telefone da pessoa de referência.',
            )
        if (
            valores['relacao_referencia']
            not in DadosEsppaInscricao.RelacaoReferencia.values
        ):
            _erro('relacao_referencia', 'Escolha inválida.')
    return valores


def _validar_responsavel(
    participante,
    responsavel,
    *,
    primeiro_dia_oficial,
):
    menor = (
        _idade_em(
            participante['data_nascimento'],
            primeiro_dia_oficial,
        )
        < 18
    )
    if menor and responsavel is None:
        _erro(
            'responsavel',
            'Responsável é obrigatório para participante menor de 18 anos.',
        )
    return (
        _normalizar_responsavel(
            responsavel,
            cpf_obrigatorio=menor,
        )
        if responsavel is not None
        else None
    )


def _validar_schema_version(valor):
    if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
        _erro('snapshot_schema_version', 'Informe uma versão positiva.')
    return valor


def _valor_snapshot(valor):
    if isinstance(valor, date):
        return valor.isoformat()
    return valor


def _componente_snapshot(valores):
    if valores is None:
        return None
    return {
        campo: _valor_snapshot(valor)
        for campo, valor in valores.items()
    }


def _construir_snapshot(
    *,
    schema_version,
    participante,
    responsavel,
    cuidado,
    esppa,
):
    return {
        'schema_version': schema_version,
        'participante': _componente_snapshot(participante),
        'responsavel': _componente_snapshot(responsavel),
        'cuidado': _componente_snapshot(cuidado),
        'esppa': _componente_snapshot(esppa),
    }


def _encontro_persistido(encontro):
    if encontro is None or encontro.pk is None:
        _erro('encontro', 'Encontro deve estar persistido.')
    try:
        encontro = Encontro.objects.get(pk=encontro.pk)
    except Encontro.DoesNotExist:
        _erro('encontro', 'Encontro não encontrado.')
    if encontro.tipo not in {Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA}:
        _erro(
            'encontro',
            'A ficha é permitida somente para Escalada e ESPPA.',
        )
    return encontro


def _pessoa_persistida(pessoa):
    if pessoa is None:
        return None
    if not isinstance(pessoa, Pessoa) or pessoa.pk is None:
        _erro('pessoa', 'Pessoa deve estar persistida.')
    try:
        return Pessoa.objects.get(pk=pessoa.pk)
    except Pessoa.DoesNotExist:
        _erro('pessoa', 'Pessoa não encontrada.')


def _validar_origem(origem):
    if origem not in InscricaoEncontro.Origem.values:
        _erro('origem', 'Origem inválida.')
    return origem


def _exigir_janela_publica(encontro, momento):
    try:
        configuracao = encontro.configuracao_encontristas
    except ConfiguracaoEncontristasEncontro.DoesNotExist:
        _erro(
            'janela',
            'O Encontro não possui configuração de inscrições.',
        )
    if not (
        configuracao.inscricoes_abrem_em
        <= momento
        <= configuracao.inscricoes_encerram_em
    ):
        _erro('janela', 'A janela de inscrições não está aberta.')


def _primeiro_dia_oficial_vigente(encontro):
    primeiro_dia = (
        DiaEncontro.objects
        .filter(
            calendario__encontro=encontro,
            calendario__vigente=True,
            calendario__oficializado_em__isnull=False,
        )
        .aggregate(primeiro_dia=Min('data'))['primeiro_dia']
    )
    if primeiro_dia is None:
        _erro(
            'calendario',
            'O Encontro não possui calendário oficial vigente com dias.',
        )
    return primeiro_dia


def _normalizar_ficha(
    *,
    encontro,
    dados_declarados,
    responsavel,
    dados_cuidado,
    dados_esppa,
    snapshot_schema_version,
    momento,
):
    data_operacao = timezone.localtime(momento).date()
    participante = _normalizar_participante(
        dados_declarados,
        data_operacao=data_operacao,
    )
    responsavel = _validar_responsavel(
        participante,
        responsavel,
        primeiro_dia_oficial=_primeiro_dia_oficial_vigente(encontro),
    )
    cuidado = _normalizar_cuidado(dados_cuidado)
    esppa = _normalizar_esppa(dados_esppa, encontro=encontro)
    schema_version = _validar_schema_version(snapshot_schema_version)
    snapshot = _construir_snapshot(
        schema_version=schema_version,
        participante=participante,
        responsavel=responsavel,
        cuidado=cuidado,
        esppa=esppa,
    )
    participante = {
        **participante,
        'snapshot_schema_version': schema_version,
        'snapshot_atual': snapshot,
    }
    return participante, responsavel, cuidado, esppa


def _validar_model(instance):
    try:
        instance.full_clean()
    except ValidationError as error:
        raise ErroFichaInscricao(error.message_dict) from error


def _criar_componente(model, inscricao, valores):
    if valores is None:
        return None
    instance = model(inscricao=inscricao, **valores)
    _validar_model(instance)
    instance.save()
    return instance


@transaction.atomic
def submeter_inscricao_encontro(
    *,
    encontro,
    origem,
    dados_declarados,
    responsavel=None,
    dados_cuidado=None,
    dados_esppa=None,
    pessoa=None,
    snapshot_schema_version=1,
    momento=None,
):
    momento = _momento_atual(momento)
    encontro = _encontro_persistido(encontro)
    origem = _validar_origem(origem)
    pessoa = _pessoa_persistida(pessoa)
    if origem == InscricaoEncontro.Origem.PUBLICA:
        if pessoa is not None:
            _erro(
                'pessoa',
                'Submissão pública não associa Pessoa automaticamente.',
            )
        _exigir_janela_publica(encontro, momento)

    participante, responsavel, cuidado, esppa = _normalizar_ficha(
        encontro=encontro,
        dados_declarados=dados_declarados,
        responsavel=responsavel,
        dados_cuidado=dados_cuidado,
        dados_esppa=dados_esppa,
        snapshot_schema_version=snapshot_schema_version,
        momento=momento,
    )
    inscricao = InscricaoEncontro(
        encontro=encontro,
        pessoa=pessoa,
        origem=origem,
        status=InscricaoEncontro.Status.ENVIADA,
    )
    _validar_model(inscricao)
    try:
        with transaction.atomic():
            inscricao.save()
            _criar_componente(
                DadosDeclaradosInscricao,
                inscricao,
                participante,
            )
            _criar_componente(
                ResponsavelDeclaradoInscricao,
                inscricao,
                responsavel,
            )
            _criar_componente(
                DadosCuidadoInscricao,
                inscricao,
                cuidado,
            )
            _criar_componente(
                DadosEsppaInscricao,
                inscricao,
                esppa,
            )
    except IntegrityError as error:
        raise ErroFichaInscricao({
            'inscricao': ['A inscrição conflita com um registro existente.'],
        }) from error
    return inscricao


def _bloquear_inscricao(inscricao):
    if inscricao is None or inscricao.pk is None:
        _erro('inscricao', 'Inscrição deve estar persistida.')
    try:
        return (
            InscricaoEncontro.objects
            .select_for_update()
            .select_related('encontro', 'pessoa')
            .get(pk=inscricao.pk)
        )
    except InscricaoEncontro.DoesNotExist:
        _erro('inscricao', 'Inscrição não encontrada.')


def _sincronizar_componente(model, inscricao, valores):
    existente = model.objects.filter(inscricao=inscricao).first()
    if valores is None:
        if existente is None:
            return False
        existente.delete()
        return True
    if existente is None:
        _criar_componente(model, inscricao, valores)
        return True

    alterados = {
        campo: valor
        for campo, valor in valores.items()
        if getattr(existente, campo) != valor
    }
    if not alterados:
        return False
    for campo, valor in alterados.items():
        setattr(existente, campo, valor)
    _validar_model(existente)
    existente.save()
    return True


@transaction.atomic
def atualizar_ficha_inscricao(
    *,
    inscricao,
    origem_operacao,
    dados_declarados,
    responsavel=None,
    dados_cuidado=None,
    dados_esppa=None,
    snapshot_schema_version=1,
    momento=None,
):
    momento = _momento_atual(momento)
    origem_operacao = _validar_origem(origem_operacao)
    inscricao = _bloquear_inscricao(inscricao)
    if origem_operacao == InscricaoEncontro.Origem.PUBLICA:
        _exigir_janela_publica(inscricao.encontro, momento)

    participante, responsavel, cuidado, esppa = _normalizar_ficha(
        encontro=inscricao.encontro,
        dados_declarados=dados_declarados,
        responsavel=responsavel,
        dados_cuidado=dados_cuidado,
        dados_esppa=dados_esppa,
        snapshot_schema_version=snapshot_schema_version,
        momento=momento,
    )
    mudou = _sincronizar_componente(
        DadosDeclaradosInscricao,
        inscricao,
        participante,
    )
    mudou |= _sincronizar_componente(
        ResponsavelDeclaradoInscricao,
        inscricao,
        responsavel,
    )
    mudou |= _sincronizar_componente(
        DadosCuidadoInscricao,
        inscricao,
        cuidado,
    )
    mudou |= _sincronizar_componente(
        DadosEsppaInscricao,
        inscricao,
        esppa,
    )
    if mudou:
        inscricao.save(update_fields=['atualizada_em'])
    return inscricao


@transaction.atomic
def cancelar_inscricao_encontro(
    *,
    inscricao,
    origem_operacao,
    momento=None,
):
    momento = _momento_atual(momento)
    origem_operacao = _validar_origem(origem_operacao)
    inscricao = _bloquear_inscricao(inscricao)
    if origem_operacao == InscricaoEncontro.Origem.PUBLICA:
        _exigir_janela_publica(inscricao.encontro, momento)
    if inscricao.status == InscricaoEncontro.Status.CANCELADA:
        return inscricao
    inscricao.status = InscricaoEncontro.Status.CANCELADA
    inscricao.cancelada_em = momento
    inscricao.save(
        update_fields=['status', 'cancelada_em', 'atualizada_em'],
    )
    return inscricao


@transaction.atomic
def reativar_inscricao_encontro(
    *,
    inscricao,
    origem_operacao,
    momento=None,
):
    momento = _momento_atual(momento)
    origem_operacao = _validar_origem(origem_operacao)
    inscricao = _bloquear_inscricao(inscricao)
    if origem_operacao == InscricaoEncontro.Origem.PUBLICA:
        _exigir_janela_publica(inscricao.encontro, momento)
    if inscricao.status == InscricaoEncontro.Status.ENVIADA:
        return inscricao
    inscricao.status = InscricaoEncontro.Status.ENVIADA
    inscricao.reativada_em = momento
    inscricao.save(
        update_fields=['status', 'reativada_em', 'atualizada_em'],
    )
    return inscricao
