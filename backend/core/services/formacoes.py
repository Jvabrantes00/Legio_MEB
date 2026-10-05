from collections.abc import Mapping

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.formacao_catalogo import (
    TEMAS_FORMATIVOS,
    TipoConteudoFormativo,
)
from core.models import (
    Encontro,
    PalestranteSessao,
    PerfilAlpinista,
    Pessoa,
    SessaoFormativa,
    TrabalhoEncontro,
)


TIPO_CONTEUDO_POR_ENCONTRO = {
    Encontro.Tipo.ESCALADA: TipoConteudoFormativo.PALESTRA,
    Encontro.Tipo.ESPPA: TipoConteudoFormativo.PALESTRA,
    Encontro.Tipo.AVC: TipoConteudoFormativo.BATE_PAPO,
}

STATUS_TRABALHO_COMPATIVEIS_AVC = {
    TrabalhoEncontro.Status.ALOCADO,
    TrabalhoEncontro.Status.TRABALHOU,
}


def _pk(instance, nome):
    if instance is None or instance.pk is None:
        raise ValidationError(f'{nome} deve estar persistido.')
    return instance.pk


def _bloquear_pessoa_por_id(pessoa_id):
    try:
        return Pessoa.objects.select_for_update().get(pk=pessoa_id)
    except Pessoa.DoesNotExist as error:
        raise ValidationError('Pessoa não encontrada.') from error


def _bloquear_perfil(perfil_alpinista):
    perfil_id = _pk(perfil_alpinista, 'PerfilAlpinista')
    pessoa = _bloquear_pessoa_por_id(perfil_alpinista.pessoa_id)
    try:
        perfil = (
            PerfilAlpinista.objects
            .select_for_update()
            .get(pk=perfil_id)
        )
    except PerfilAlpinista.DoesNotExist as error:
        raise ValidationError('PerfilAlpinista não encontrado.') from error
    if perfil.pessoa_id != pessoa.pk:
        raise ValidationError('PerfilAlpinista e Pessoa são incoerentes.')
    return perfil, pessoa


def _bloquear_encontro_por_id(encontro_id):
    try:
        return Encontro.objects.select_for_update().get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error


def _bloquear_encontro(encontro):
    return _bloquear_encontro_por_id(_pk(encontro, 'Encontro'))


def _bloquear_sessao(sessao, encontro):
    sessao_id = _pk(sessao, 'Sessão formativa')
    try:
        sessao_bloqueada = (
            SessaoFormativa.objects
            .select_for_update()
            .get(pk=sessao_id)
        )
    except SessaoFormativa.DoesNotExist as error:
        raise ValidationError('Sessão formativa não encontrada.') from error
    if sessao_bloqueada.encontro_id != encontro.pk:
        raise ValidationError('Sessão formativa e Encontro são incoerentes.')
    return sessao_bloqueada


def _resolver_tema(tema_codigo):
    codigo = str(tema_codigo or '').strip()
    if not codigo:
        raise ValidationError('Código de tema é obrigatório.')
    tema = TEMAS_FORMATIVOS.get(codigo)
    if tema is None or tema.codigo != codigo:
        raise ValidationError('Tema formativo inválido.')
    try:
        tipo_conteudo = TipoConteudoFormativo(tema.tipo_conteudo)
    except ValueError as error:
        raise ValidationError('Tipo de conteúdo do tema é inválido.') from error
    if not tema.titulo.strip():
        raise ValidationError('Título do tema formativo é obrigatório.')
    return tema, tipo_conteudo


def _validar_tema_para_encontro(tema, tipo_conteudo, encontro):
    tipo_esperado = TIPO_CONTEUDO_POR_ENCONTRO.get(encontro.tipo)
    if tipo_esperado is None:
        if encontro.tipo == Encontro.Tipo.ACAMPAMENTO:
            raise ValidationError(
                'Acampamento não possui sessão formativa deste domínio.'
            )
        raise ValidationError('Tipo de Encontro sem formação configurada.')
    if tipo_conteudo != tipo_esperado:
        raise ValidationError(
            'O tipo de conteúdo não é compatível com este Encontro.'
        )
    if encontro.tipo not in tema.tipos_encontro:
        raise ValidationError('O tema não é aplicável a este tipo de Encontro.')


def _validar_estrutura_sessao(sessao, encontro):
    tipo_esperado = TIPO_CONTEUDO_POR_ENCONTRO.get(encontro.tipo)
    if tipo_esperado is None:
        raise ValidationError('Este Encontro não admite sessão formativa.')
    if sessao.tipo_conteudo != tipo_esperado.value:
        raise ValidationError(
            'A sessão possui conteúdo incompatível com o tipo do Encontro.'
        )


def _validar_sessao_planejada(sessao):
    if sessao.status != SessaoFormativa.Status.PLANEJADA:
        raise ValidationError('Somente sessão planejada pode ser alterada.')


def _bloquear_trabalho_avc(pessoa, encontro):
    trabalho = (
        TrabalhoEncontro.objects
        .select_for_update()
        .filter(pessoa=pessoa, encontro=encontro)
        .first()
    )
    if trabalho is None:
        raise ValidationError(
            'Palestrante do AVC deve trabalhar no mesmo Encontro.'
        )
    if trabalho.status not in STATUS_TRABALHO_COMPATIVEIS_AVC:
        raise ValidationError(
            'O trabalho do palestrante no AVC não está em estado compatível.'
        )
    return trabalho


@transaction.atomic
def criar_sessao_formativa(*, encontro, tema_codigo):
    tema, tipo_conteudo = _resolver_tema(tema_codigo)
    encontro_bloqueado = _bloquear_encontro(encontro)
    _validar_tema_para_encontro(
        tema,
        tipo_conteudo,
        encontro_bloqueado,
    )
    return SessaoFormativa.objects.create(
        encontro=encontro_bloqueado,
        tema_codigo=tema.codigo,
        tipo_conteudo=tipo_conteudo.value,
        titulo_snapshot=tema.titulo,
    )


@transaction.atomic
def alterar_tema_sessao(sessao, *, tema_codigo):
    tema, tipo_conteudo = _resolver_tema(tema_codigo)
    encontro = _bloquear_encontro_por_id(sessao.encontro_id)
    sessao_bloqueada = _bloquear_sessao(sessao, encontro)
    _validar_sessao_planejada(sessao_bloqueada)
    _validar_tema_para_encontro(tema, tipo_conteudo, encontro)

    sessao_bloqueada.tema_codigo = tema.codigo
    sessao_bloqueada.tipo_conteudo = tipo_conteudo.value
    sessao_bloqueada.titulo_snapshot = tema.titulo
    sessao_bloqueada.save(
        update_fields=[
            'tema_codigo',
            'tipo_conteudo',
            'titulo_snapshot',
            'atualizado_em',
        ]
    )
    return sessao_bloqueada


@transaction.atomic
def adicionar_palestrante_alpinista(sessao, perfil_alpinista):
    perfil, pessoa = _bloquear_perfil(perfil_alpinista)
    encontro = _bloquear_encontro_por_id(sessao.encontro_id)
    if encontro.tipo == Encontro.Tipo.AVC:
        _bloquear_trabalho_avc(pessoa, encontro)
    sessao_bloqueada = _bloquear_sessao(sessao, encontro)
    _validar_sessao_planejada(sessao_bloqueada)
    _validar_estrutura_sessao(sessao_bloqueada, encontro)

    existente = (
        PalestranteSessao.objects
        .select_for_update()
        .filter(
            sessao_formativa=sessao_bloqueada,
            perfil_alpinista=perfil,
        )
        .first()
    )
    if existente is not None:
        return existente

    try:
        with transaction.atomic():
            return PalestranteSessao.objects.create(
                sessao_formativa=sessao_bloqueada,
                perfil_alpinista=perfil,
            )
    except IntegrityError as error:
        raise ValidationError(
            'O Alpinista já é palestrante desta sessão.'
        ) from error


@transaction.atomic
def adicionar_palestrante_externo(sessao, *, nome_externo):
    nome_normalizado = ' '.join(str(nome_externo or '').split())
    if not nome_normalizado:
        raise ValidationError('Nome do palestrante externo é obrigatório.')

    encontro = _bloquear_encontro_por_id(sessao.encontro_id)
    sessao_bloqueada = _bloquear_sessao(sessao, encontro)
    _validar_sessao_planejada(sessao_bloqueada)
    _validar_estrutura_sessao(sessao_bloqueada, encontro)
    if encontro.tipo == Encontro.Tipo.AVC:
        raise ValidationError('AVC não permite palestrante externo.')

    return PalestranteSessao.objects.create(
        sessao_formativa=sessao_bloqueada,
        nome_externo=nome_normalizado,
    )


@transaction.atomic
def remover_palestrante(palestrante):
    palestrante_id = _pk(palestrante, 'Palestrante da sessão')
    if palestrante.perfil_alpinista_id is not None:
        _bloquear_perfil(palestrante.perfil_alpinista)
    encontro = _bloquear_encontro_por_id(
        palestrante.sessao_formativa.encontro_id
    )
    sessao = _bloquear_sessao(palestrante.sessao_formativa, encontro)
    _validar_sessao_planejada(sessao)
    try:
        palestrante_bloqueado = (
            PalestranteSessao.objects
            .select_for_update()
            .get(pk=palestrante_id, sessao_formativa=sessao)
        )
    except PalestranteSessao.DoesNotExist as error:
        raise ValidationError('Palestrante da sessão não encontrado.') from error
    if palestrante_bloqueado.status != PalestranteSessao.Status.PREVISTO:
        raise ValidationError('Atuação já registrada não pode ser removida.')
    palestrante_bloqueado.delete()


@transaction.atomic
def cancelar_sessao_formativa(sessao):
    encontro = _bloquear_encontro_por_id(sessao.encontro_id)
    sessao_bloqueada = _bloquear_sessao(sessao, encontro)
    if sessao_bloqueada.status == SessaoFormativa.Status.CANCELADA:
        return sessao_bloqueada
    if sessao_bloqueada.status == SessaoFormativa.Status.REALIZADA:
        raise ValidationError('Sessão realizada não pode ser cancelada.')
    sessao_bloqueada.status = SessaoFormativa.Status.CANCELADA
    sessao_bloqueada.realizada_em = None
    sessao_bloqueada.save(
        update_fields=['status', 'realizada_em', 'atualizado_em']
    )
    return sessao_bloqueada


def _normalizar_resultados(resultados):
    if not isinstance(resultados, Mapping):
        raise ValidationError('Resultados devem ser informados por palestrante.')
    normalizados = {}
    for referencia, status in resultados.items():
        palestrante_id = (
            referencia.pk
            if isinstance(referencia, PalestranteSessao)
            else referencia
        )
        if not isinstance(palestrante_id, int) or palestrante_id <= 0:
            raise ValidationError('Palestrante inválido nos resultados.')
        if status not in {
            PalestranteSessao.Status.MINISTROU,
            PalestranteSessao.Status.NAO_MINISTROU,
        }:
            raise ValidationError('Resultado de palestrante inválido.')
        normalizados[palestrante_id] = status
    return normalizados


def _bloquear_contexto_realizacao(sessao, resultados):
    sessao_id = _pk(sessao, 'Sessão formativa')
    referencias = list(
        PalestranteSessao.objects
        .filter(sessao_formativa_id=sessao_id)
        .values_list('pk', 'perfil_alpinista_id', 'perfil_alpinista__pessoa_id')
        .order_by('pk')
    )
    pessoa_ids = sorted({item[2] for item in referencias if item[2] is not None})
    pessoas = {
        pessoa.pk: pessoa
        for pessoa in (
            Pessoa.objects
            .select_for_update()
            .filter(pk__in=pessoa_ids)
            .order_by('pk')
        )
    }
    if len(pessoas) != len(pessoa_ids):
        raise ValidationError('Pessoa de palestrante não encontrada.')

    perfil_ids = sorted({item[1] for item in referencias if item[1] is not None})
    perfis = list(
        PerfilAlpinista.objects
        .select_for_update()
        .filter(pk__in=perfil_ids)
        .order_by('pk')
    )
    if len(perfis) != len(perfil_ids):
        raise ValidationError('PerfilAlpinista não encontrado.')

    encontro = _bloquear_encontro_por_id(sessao.encontro_id)
    if encontro.tipo == Encontro.Tipo.AVC:
        trabalhos = {
            trabalho.pessoa_id: trabalho
            for trabalho in (
                TrabalhoEncontro.objects
                .select_for_update()
                .filter(
                    pessoa_id__in=pessoa_ids,
                    encontro=encontro,
                )
                .order_by('pk')
            )
        }
        for pessoa_id in pessoa_ids:
            trabalho = trabalhos.get(pessoa_id)
            if trabalho is None:
                raise ValidationError(
                    'Palestrante do AVC deve trabalhar no mesmo Encontro.'
                )
            if trabalho.status not in STATUS_TRABALHO_COMPATIVEIS_AVC:
                raise ValidationError(
                    'O trabalho do palestrante no AVC não está em estado '
                    'compatível.'
                )

    sessao_bloqueada = _bloquear_sessao(sessao, encontro)
    palestrantes = list(
        PalestranteSessao.objects
        .select_for_update()
        .filter(sessao_formativa=sessao_bloqueada)
        .order_by('pk')
    )
    ids_antes = {item[0] for item in referencias}
    ids_bloqueados = {item.pk for item in palestrantes}
    if ids_antes != ids_bloqueados:
        raise ValidationError(
            'A composição da sessão mudou durante a realização; tente novamente.'
        )
    if set(resultados) != ids_bloqueados:
        raise ValidationError(
            'Informe o resultado de todos os palestrantes da sessão.'
        )
    return sessao_bloqueada, encontro, palestrantes


@transaction.atomic
def registrar_realizacao_sessao(sessao, *, resultados, momento=None):
    resultados_normalizados = _normalizar_resultados(resultados)
    if PalestranteSessao.Status.MINISTROU not in resultados_normalizados.values():
        raise ValidationError('Ao menos um palestrante deve ter ministrado.')

    sessao_bloqueada, encontro, palestrantes = _bloquear_contexto_realizacao(
        sessao,
        resultados_normalizados,
    )
    _validar_estrutura_sessao(sessao_bloqueada, encontro)

    if sessao_bloqueada.status == SessaoFormativa.Status.CANCELADA:
        raise ValidationError('Sessão cancelada não pode ser realizada.')
    if sessao_bloqueada.status == SessaoFormativa.Status.REALIZADA:
        if all(
            palestrante.status == resultados_normalizados[palestrante.pk]
            for palestrante in palestrantes
        ):
            return sessao_bloqueada
        raise ValidationError('A sessão já possui outro resultado registrado.')

    if any(
        palestrante.status != PalestranteSessao.Status.PREVISTO
        for palestrante in palestrantes
    ):
        raise ValidationError('A sessão possui atuação previamente finalizada.')
    if encontro.tipo == Encontro.Tipo.AVC and any(
        palestrante.perfil_alpinista_id is None
        for palestrante in palestrantes
    ):
        raise ValidationError('AVC não permite palestrante externo.')

    instante = momento or timezone.now()
    for palestrante in palestrantes:
        palestrante.status = resultados_normalizados[palestrante.pk]
        palestrante.ministrou_em = (
            instante
            if palestrante.status == PalestranteSessao.Status.MINISTROU
            else None
        )
        palestrante.save(
            update_fields=['status', 'ministrou_em', 'atualizado_em']
        )

    sessao_bloqueada.status = SessaoFormativa.Status.REALIZADA
    sessao_bloqueada.realizada_em = instante
    sessao_bloqueada.save(
        update_fields=['status', 'realizada_em', 'atualizado_em']
    )
    return sessao_bloqueada


def obter_historico_formativo(perfil_alpinista):
    perfil_id = _pk(perfil_alpinista, 'PerfilAlpinista')
    if not PerfilAlpinista.objects.filter(pk=perfil_id).exists():
        raise ValidationError('PerfilAlpinista não encontrado.')
    return (
        PalestranteSessao.objects
        .filter(
            perfil_alpinista_id=perfil_id,
            status=PalestranteSessao.Status.MINISTROU,
            sessao_formativa__status=SessaoFormativa.Status.REALIZADA,
        )
        .select_related(
            'perfil_alpinista__pessoa',
            'sessao_formativa__encontro',
        )
        .order_by('-sessao_formativa__realizada_em', '-pk')
    )


def validar_transicao_trabalho_formacao(trabalho, *, novo_status):
    if trabalho.encontro.tipo != Encontro.Tipo.AVC:
        return
    if novo_status in STATUS_TRABALHO_COMPATIVEIS_AVC:
        return
    possui_atuacao = PalestranteSessao.objects.filter(
        perfil_alpinista__pessoa_id=trabalho.pessoa_id,
        sessao_formativa__encontro_id=trabalho.encontro_id,
        sessao_formativa__status__in=(
            SessaoFormativa.Status.PLANEJADA,
            SessaoFormativa.Status.REALIZADA,
        ),
        status__in=(
            PalestranteSessao.Status.PREVISTO,
            PalestranteSessao.Status.MINISTROU,
        ),
    ).exists()
    if possui_atuacao:
        raise ValidationError(
            'O trabalho no AVC não pode perder estado operacional enquanto '
            'a Pessoa for palestrante do Encontro.'
        )
