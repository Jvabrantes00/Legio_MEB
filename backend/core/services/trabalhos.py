from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Pessoa,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.services.participacoes import criar_convite
from core.services.elegibilidade_trabalho import (
    AvisosElegibilidadePendentes,
    BloqueioElegibilidadeTrabalho,
    avaliar_alocacao_trabalho,
    avaliar_elegibilidade_trabalho,
)


STATUS_FINAIS = {
    TrabalhoEncontro.Status.TRABALHOU,
    TrabalhoEncontro.Status.FALTOU,
    TrabalhoEncontro.Status.RETIRADO,
}


def _validar_avaliacao_trabalho(avaliacao, *, confirmar_avisos):
    if avaliacao.bloqueios:
        raise BloqueioElegibilidadeTrabalho(
            avaliacao,
            'A operação foi bloqueada pela elegibilidade estrutural.',
        )
    if avaliacao.avisos and not confirmar_avisos:
        raise AvisosElegibilidadePendentes(
            avaliacao,
            'Confirme explicitamente os avisos para continuar.',
        )


def _anexar_avaliacao(instancia, avaliacao):
    instancia.avaliacao_elegibilidade = avaliacao
    return instancia


def _pk(instance, nome):
    if instance is None or instance.pk is None:
        raise ValidationError(f'{nome} deve estar persistido.')
    return instance.pk


def _bloquear_pessoa(pessoa):
    pessoa_id = _pk(pessoa, 'Pessoa')
    try:
        return Pessoa.objects.select_for_update().get(pk=pessoa_id)
    except Pessoa.DoesNotExist as error:
        raise ValidationError('Pessoa não encontrada.') from error


def _bloquear_encontro(encontro):
    encontro_id = _pk(encontro, 'Encontro')
    try:
        return Encontro.objects.select_for_update().get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error


def _bloquear_convite(convite):
    convite_id = _pk(convite, 'Convite')
    try:
        return (
            ConviteEncontro.objects
            .select_for_update()
            .get(pk=convite_id)
        )
    except ConviteEncontro.DoesNotExist as error:
        raise ValidationError('Convite não encontrado.') from error


def _bloquear_role(role_equipe):
    role_id = _pk(role_equipe, 'Role de equipe')
    try:
        return (
            RoleEquipeEncontro.objects
            .select_for_update()
            .select_related(
                'equipe_encontro__template_origem',
                'template_origem__template_equipe',
            )
            .get(pk=role_id)
        )
    except RoleEquipeEncontro.DoesNotExist as error:
        raise ValidationError('Role de equipe não encontrada.') from error


def _bloquear_contexto_trabalho(trabalho):
    trabalho_id = _pk(trabalho, 'Trabalho')
    pessoa = _bloquear_pessoa(trabalho.pessoa)
    encontro = _bloquear_encontro(trabalho.encontro)
    convite = _bloquear_convite(trabalho.convite)
    try:
        trabalho_bloqueado = (
            TrabalhoEncontro.objects
            .select_for_update()
            .get(pk=trabalho_id)
        )
    except TrabalhoEncontro.DoesNotExist as error:
        raise ValidationError('Trabalho não encontrado.') from error

    if (
        trabalho_bloqueado.pessoa_id != pessoa.pk
        or trabalho_bloqueado.encontro_id != encontro.pk
        or trabalho_bloqueado.convite_id != convite.pk
    ):
        raise ValidationError('O vínculo operacional do trabalho é incoerente.')
    _validar_convite_do_trabalho(convite, pessoa, encontro)
    return trabalho_bloqueado, pessoa, encontro, convite


def _validar_convite_do_trabalho(convite, pessoa, encontro):
    if convite.finalidade != ConviteEncontro.Finalidade.TRABALHAR:
        raise ValidationError('O trabalho exige convite com finalidade TRABALHAR.')
    if convite.pessoa_id != pessoa.pk or convite.encontro_id != encontro.pk:
        raise ValidationError(
            'Convite, Pessoa e Encontro devem representar o mesmo trabalho.'
        )
    if convite.status != ConviteEncontro.Status.CONFIRMADO:
        raise ValidationError('O trabalho exige convite confirmado.')


def _validar_role_do_encontro(role_equipe, encontro):
    if role_equipe.equipe_encontro.encontro_id != encontro.pk:
        raise ValidationError('A role deve pertencer ao snapshot deste Encontro.')
    if (
        role_equipe.template_origem.template_equipe_id
        != role_equipe.equipe_encontro.template_origem_id
    ):
        raise ValidationError('A role é incompatível com a equipe do snapshot.')


def _validar_quantidade_estrutural(
    role_equipe,
    *,
    excluir_trabalhos=(),
):
    limite = role_equipe.quantidade_estrutural
    if limite is None:
        return

    ocupantes = TrabalhoEncontro.objects.filter(
        role_equipe=role_equipe,
        status=TrabalhoEncontro.Status.ALOCADO,
    )
    ids_excluidos = [
        trabalho.pk
        for trabalho in excluir_trabalhos
        if trabalho is not None and trabalho.pk is not None
    ]
    if ids_excluidos:
        ocupantes = ocupantes.exclude(pk__in=ids_excluidos)
    if ocupantes.count() >= limite:
        raise ValidationError('A quantidade estrutural desta role foi atingida.')


def _snapshots_do_encontro(encontro):
    return list(
        EquipeEncontro.objects
        .filter(encontro=encontro)
        .prefetch_related('roles')
        .order_by('ordem', 'pk')
    )


@transaction.atomic
def preparar_equipes_encontro(encontro):
    encontro_bloqueado = _bloquear_encontro(encontro)
    snapshots_existentes = list(
        EquipeEncontro.objects
        .select_for_update()
        .filter(encontro=encontro_bloqueado)
        .order_by('ordem', 'pk')
    )
    if snapshots_existentes:
        return _snapshots_do_encontro(encontro_bloqueado)

    templates = list(
        TemplateEquipeEncontro.objects
        .select_for_update()
        .filter(
            tipo_encontro=encontro_bloqueado.tipo,
            ativo=True,
        )
        .order_by('ordem', 'pk')
    )
    if not templates:
        return []

    for template in templates:
        roles = list(
            TemplateRoleEquipe.objects
            .select_for_update()
            .filter(template_equipe=template, ativo=True)
            .order_by('ordem', 'pk')
        )
        equipe = EquipeEncontro.objects.create(
            encontro=encontro_bloqueado,
            template_origem=template,
            codigo=template.codigo,
            nome=template.nome,
            ordem=template.ordem,
            capacidade_minima_recomendada=(
                template.capacidade_minima_recomendada
            ),
            capacidade_maxima_recomendada=(
                template.capacidade_maxima_recomendada
            ),
        )
        RoleEquipeEncontro.objects.bulk_create([
            RoleEquipeEncontro(
                equipe_encontro=equipe,
                template_origem=role,
                codigo=role.codigo,
                nome=role.nome,
                ordem=role.ordem,
                quantidade_estrutural=role.quantidade_estrutural,
                concede_registro_presenca=role.concede_registro_presenca,
            )
            for role in roles
        ])

    return _snapshots_do_encontro(encontro_bloqueado)


@transaction.atomic
def criar_convite_trabalho(
    *,
    pessoa,
    encontro,
    role_proposta=None,
    confirmar_avisos=False,
):
    pessoa_bloqueada = _bloquear_pessoa(pessoa)
    encontro_bloqueado = _bloquear_encontro(encontro)
    avaliacao = avaliar_elegibilidade_trabalho(
        pessoa_bloqueada,
        encontro_bloqueado,
    )
    _validar_avaliacao_trabalho(
        avaliacao,
        confirmar_avisos=confirmar_avisos,
    )
    convite = criar_convite(
        pessoa=pessoa_bloqueada,
        encontro=encontro_bloqueado,
        finalidade=ConviteEncontro.Finalidade.TRABALHAR,
    )
    convite_bloqueado = _bloquear_convite(convite)

    if role_proposta is None:
        return _anexar_avaliacao(convite_bloqueado, avaliacao)

    role_bloqueada = _bloquear_role(role_proposta)
    _validar_role_do_encontro(role_bloqueada, convite_bloqueado.encontro)
    if convite_bloqueado.role_trabalho_proposta_id not in {
        None,
        role_bloqueada.pk,
    }:
        raise ValidationError('O convite já possui outra role proposta.')
    if convite_bloqueado.role_trabalho_proposta_id is None:
        convite_bloqueado.role_trabalho_proposta = role_bloqueada
        convite_bloqueado.save(
            update_fields=['role_trabalho_proposta', 'atualizado_em']
        )
    return _anexar_avaliacao(convite_bloqueado, avaliacao)


@transaction.atomic
def iniciar_trabalho_confirmado(convite, *, confirmar_avisos=False):
    pessoa_bloqueada = _bloquear_pessoa(convite.pessoa)
    encontro_bloqueado = _bloquear_encontro(convite.encontro)
    convite_bloqueado = _bloquear_convite(convite)
    _validar_convite_do_trabalho(
        convite_bloqueado,
        pessoa_bloqueada,
        encontro_bloqueado,
    )
    avaliacao = avaliar_elegibilidade_trabalho(
        pessoa_bloqueada,
        encontro_bloqueado,
    )
    if convite_bloqueado.role_trabalho_proposta_id is not None:
        avaliacao = avaliar_alocacao_trabalho(
            pessoa_bloqueada,
            encontro_bloqueado,
            convite_bloqueado.role_trabalho_proposta,
        )
    _validar_avaliacao_trabalho(
        avaliacao,
        confirmar_avisos=confirmar_avisos,
    )

    trabalho = (
        TrabalhoEncontro.objects
        .select_for_update()
        .filter(convite=convite_bloqueado)
        .first()
    )
    if trabalho is not None:
        if (
            trabalho.pessoa_id != pessoa_bloqueada.pk
            or trabalho.encontro_id != encontro_bloqueado.pk
        ):
            raise ValidationError('O trabalho existente é incoerente com o convite.')
        return _anexar_avaliacao(trabalho, avaliacao)

    outro_trabalho = (
        TrabalhoEncontro.objects
        .select_for_update()
        .filter(
            pessoa=pessoa_bloqueada,
            encontro=encontro_bloqueado,
        )
        .first()
    )
    if outro_trabalho is not None:
        raise ValidationError('A Pessoa já possui trabalho neste Encontro.')

    role_bloqueada = None
    status = TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO
    if convite_bloqueado.role_trabalho_proposta_id is not None:
        role_bloqueada = _bloquear_role(
            convite_bloqueado.role_trabalho_proposta
        )
        _validar_role_do_encontro(role_bloqueada, encontro_bloqueado)
        _validar_quantidade_estrutural(role_bloqueada)
        status = TrabalhoEncontro.Status.ALOCADO

    try:
        with transaction.atomic():
            trabalho = TrabalhoEncontro.objects.create(
                pessoa=pessoa_bloqueada,
                encontro=encontro_bloqueado,
                convite=convite_bloqueado,
                role_equipe=role_bloqueada,
                status=status,
            )
            return _anexar_avaliacao(trabalho, avaliacao)
    except IntegrityError as error:
        raise ValidationError(
            'A Pessoa já possui trabalho neste Encontro.'
        ) from error


@transaction.atomic
def alocar_trabalho(
    trabalho,
    role_equipe,
    *,
    confirmar_avisos=False,
):
    trabalho_bloqueado, _, encontro_bloqueado, _ = (
        _bloquear_contexto_trabalho(trabalho)
    )
    role_bloqueada = _bloquear_role(role_equipe)
    _validar_role_do_encontro(role_bloqueada, encontro_bloqueado)

    if trabalho_bloqueado.status in STATUS_FINAIS:
        raise ValidationError('Trabalho finalizado não pode ser alocado novamente.')
    avaliacao = avaliar_alocacao_trabalho(
        trabalho_bloqueado.pessoa,
        encontro_bloqueado,
        role_bloqueada,
        trabalho=trabalho_bloqueado,
    )
    _validar_avaliacao_trabalho(
        avaliacao,
        confirmar_avisos=confirmar_avisos,
    )
    if (
        trabalho_bloqueado.status == TrabalhoEncontro.Status.ALOCADO
        and trabalho_bloqueado.role_equipe_id == role_bloqueada.pk
    ):
        return _anexar_avaliacao(trabalho_bloqueado, avaliacao)

    _validar_quantidade_estrutural(
        role_bloqueada,
        excluir_trabalhos=(trabalho_bloqueado,),
    )
    trabalho_bloqueado.role_equipe = role_bloqueada
    trabalho_bloqueado.status = TrabalhoEncontro.Status.ALOCADO
    trabalho_bloqueado.resultado_registrado_em = None
    trabalho_bloqueado.save(
        update_fields=[
            'role_equipe',
            'status',
            'resultado_registrado_em',
            'atualizado_em',
        ]
    )
    return _anexar_avaliacao(trabalho_bloqueado, avaliacao)


@transaction.atomic
def desalocar_trabalho(trabalho):
    trabalho_bloqueado, _, _, _ = _bloquear_contexto_trabalho(trabalho)
    if trabalho_bloqueado.status == TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO:
        return trabalho_bloqueado
    if trabalho_bloqueado.status != TrabalhoEncontro.Status.ALOCADO:
        raise ValidationError('Somente trabalho alocado pode ser desalocado.')

    trabalho_bloqueado.role_equipe = None
    trabalho_bloqueado.status = TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO
    trabalho_bloqueado.resultado_registrado_em = None
    trabalho_bloqueado.save(
        update_fields=[
            'role_equipe',
            'status',
            'resultado_registrado_em',
            'atualizado_em',
        ]
    )
    return trabalho_bloqueado


@transaction.atomic
def retirar_trabalho(trabalho):
    trabalho_bloqueado, _, _, _ = _bloquear_contexto_trabalho(trabalho)
    if trabalho_bloqueado.status == TrabalhoEncontro.Status.RETIRADO:
        return trabalho_bloqueado
    if trabalho_bloqueado.status in {
        TrabalhoEncontro.Status.TRABALHOU,
        TrabalhoEncontro.Status.FALTOU,
    }:
        raise ValidationError('Resultado final não pode ser convertido em retirada.')

    trabalho_bloqueado.status = TrabalhoEncontro.Status.RETIRADO
    trabalho_bloqueado.resultado_registrado_em = None
    trabalho_bloqueado.save(
        update_fields=['status', 'resultado_registrado_em', 'atualizado_em']
    )
    return trabalho_bloqueado


@transaction.atomic
def registrar_resultado_trabalho(trabalho, *, status, momento=None):
    if status not in {
        TrabalhoEncontro.Status.TRABALHOU,
        TrabalhoEncontro.Status.FALTOU,
    }:
        raise ValidationError('Resultado de trabalho inválido.')

    trabalho_bloqueado, _, _, _ = _bloquear_contexto_trabalho(trabalho)
    if trabalho_bloqueado.status == status:
        return trabalho_bloqueado
    if trabalho_bloqueado.status in STATUS_FINAIS:
        raise ValidationError('O trabalho já possui estado final.')
    if trabalho_bloqueado.status != TrabalhoEncontro.Status.ALOCADO:
        raise ValidationError('Somente trabalho alocado pode receber resultado.')

    trabalho_bloqueado.status = status
    trabalho_bloqueado.resultado_registrado_em = momento or timezone.now()
    trabalho_bloqueado.save(
        update_fields=['status', 'resultado_registrado_em', 'atualizado_em']
    )
    return trabalho_bloqueado


@transaction.atomic
def substituir_trabalho(
    trabalho_anterior,
    trabalho_novo,
    role_equipe,
    *,
    confirmar_avisos=False,
):
    anterior_id = _pk(trabalho_anterior, 'Trabalho anterior')
    novo_id = _pk(trabalho_novo, 'Trabalho novo')
    if anterior_id == novo_id:
        raise ValidationError('A substituição exige dois trabalhos distintos.')

    pessoa_ids = sorted({
        trabalho_anterior.pessoa_id,
        trabalho_novo.pessoa_id,
    })
    pessoas = list(
        Pessoa.objects
        .select_for_update()
        .filter(pk__in=pessoa_ids)
        .order_by('pk')
    )
    if len(pessoas) != len(pessoa_ids):
        raise ValidationError('Pessoa do trabalho não encontrada.')

    encontro_ids = {
        trabalho_anterior.encontro_id,
        trabalho_novo.encontro_id,
    }
    if len(encontro_ids) != 1:
        raise ValidationError('A substituição exige trabalhos do mesmo Encontro.')
    try:
        encontro = (
            Encontro.objects
            .select_for_update()
            .get(pk=encontro_ids.pop())
        )
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error

    convite_ids = sorted({
        trabalho_anterior.convite_id,
        trabalho_novo.convite_id,
    })
    convites = {
        convite.pk: convite
        for convite in (
            ConviteEncontro.objects
            .select_for_update()
            .filter(pk__in=convite_ids)
            .order_by('pk')
        )
    }
    if len(convites) != len(convite_ids):
        raise ValidationError('Convite do trabalho não encontrado.')

    trabalhos = {
        trabalho.pk: trabalho
        for trabalho in (
            TrabalhoEncontro.objects
            .select_for_update()
            .filter(pk__in=sorted((anterior_id, novo_id)))
            .order_by('pk')
        )
    }
    if len(trabalhos) != 2:
        raise ValidationError('Trabalho da substituição não encontrado.')

    anterior = trabalhos[anterior_id]
    novo = trabalhos[novo_id]
    if anterior.pessoa_id == novo.pessoa_id:
        raise ValidationError('A substituição exige Pessoas distintas.')
    for trabalho in (anterior, novo):
        convite = convites[trabalho.convite_id]
        pessoa = next(
            pessoa for pessoa in pessoas if pessoa.pk == trabalho.pessoa_id
        )
        if trabalho.encontro_id != encontro.pk:
            raise ValidationError('Trabalho pertence a outro Encontro.')
        _validar_convite_do_trabalho(convite, pessoa, encontro)

    role_bloqueada = _bloquear_role(role_equipe)
    _validar_role_do_encontro(role_bloqueada, encontro)
    if anterior.role_equipe_id != role_bloqueada.pk:
        raise ValidationError('A substituição deve preservar a posição anterior.')

    avaliacao = avaliar_alocacao_trabalho(
        novo.pessoa,
        encontro,
        role_bloqueada,
        trabalho=novo,
    )
    _validar_avaliacao_trabalho(
        avaliacao,
        confirmar_avisos=confirmar_avisos,
    )

    if (
        anterior.status == TrabalhoEncontro.Status.RETIRADO
        and novo.status == TrabalhoEncontro.Status.ALOCADO
        and novo.role_equipe_id == role_bloqueada.pk
    ):
        return anterior, _anexar_avaliacao(novo, avaliacao)
    if anterior.status != TrabalhoEncontro.Status.ALOCADO:
        raise ValidationError('O trabalho substituído deve estar alocado.')
    if novo.status != TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO:
        raise ValidationError(
            'O trabalho substituto deve estar aguardando alocação.'
        )

    _validar_quantidade_estrutural(
        role_bloqueada,
        excluir_trabalhos=(anterior, novo),
    )
    anterior.status = TrabalhoEncontro.Status.RETIRADO
    anterior.resultado_registrado_em = None
    anterior.save(
        update_fields=['status', 'resultado_registrado_em', 'atualizado_em']
    )
    novo.role_equipe = role_bloqueada
    novo.status = TrabalhoEncontro.Status.ALOCADO
    novo.resultado_registrado_em = None
    novo.save(
        update_fields=[
            'role_equipe',
            'status',
            'resultado_registrado_em',
            'atualizado_em',
        ]
    )
    return anterior, _anexar_avaliacao(novo, avaliacao)
