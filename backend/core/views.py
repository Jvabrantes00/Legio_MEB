import mimetypes
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError as django_core_validation_error
from django.http import FileResponse, Http404
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import APIException, MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

from .models import (
    Alpinista, AvaliacaoEncontro, CalendarioEncontro, ConviteEncontro,
    CorrespondenciaCadastralInscricao,
    DiaEncontro, Encontro, EntregaMaterial, EquipeEncontro, Evento,
    FotoEncontro, FuncaoEncontro, Inscricao, InscricaoEncontro, Palestra,
    ParticipacaoEncontro as ResultadoParticipacaoEncontro,
    ParticipacaoEvento, LogSistema, Material, PalestranteSessao,
    PerfilAlpinista, PresencaPreparatoria, ReuniaoPreparatoriaEncontro,
    PublicacaoCalendarioInstitucional, SessaoFormativa, TrabalhoEncontro,
    ItemPropostaVioleiros, PropostaVioleiros,
    VinculoEncontroLegado as ParticipacaoEncontro,
)
from .serializers import (
    AlpinistaCompletoSerializer, AlpinistaFotoSerializer, CurrentUserSerializer,
    AlpinistaResumoSerializer,
    AlpinistaMusicaCommandSerializer, HistoricoPalestraSerializer,
    HistoricoVioleiroSerializer,
    EncontroComunicacaoSerializer, EncontroSerializer, EventoSerializer,
    EntregaMaterialSerializer, FotoEncontroSerializer, MaterialSerializer,
    FuncaoEncontroSerializer, ParticipacaoEncontroSerializer,
    ParticipacaoEventoSerializer, LogSistemaSerializer,
    InscricaoEncontroCommandSerializer, ConviteEncontroCommandSerializer,
    RespostaConviteEncontroCommandSerializer,
    ResultadoParticipacaoCommandSerializer,
    AlocacaoTrabalhoCommandSerializer, EquipeEncontroSerializer,
    CorrecaoPresencaPreparatoriaCommandSerializer,
    PresencaPreparatoriaCommandSerializer,
    ResultadoTrabalhoCommandSerializer,
    SubstituicaoTrabalhoCommandSerializer,
    TrabalhoEncontroCommandSerializer,
    AlteracaoTemaSessaoCommandSerializer,
    CriacaoSessaoFormativaCommandSerializer,
    HistoricoFormativoSerializer,
    PalestranteSessaoCommandSerializer,
    PalestranteSessaoSerializer,
    PeriodoCalendarioQuerySerializer,
    ConsultaCalendarioInstitucionalSerializer,
    AgendaEncontroSerializer,
    AvaliacaoAgendaCommandSerializer,
    CalendarioSemDadosCommandSerializer,
    CriacaoEncontroCalendarioCommandSerializer,
    DadosBasicosCalendarioCommandSerializer,
    PlanejamentoCalendarioCommandSerializer,
    ExportacaoCalendarioCommandSerializer,
    HistoricoPublicacaoCalendarioQuerySerializer,
    PublicacaoCalendarioSerializer,
    ReuniaoAgendaCriacaoCommandSerializer,
    ReuniaoAgendaEdicaoCommandSerializer,
    RotuloDiaCalendarioCommandSerializer,
    ResultadoComandoCalendarioSerializer,
    RealizacaoSessaoCommandSerializer,
    RemocaoPalestranteCommandSerializer,
    SessaoFormativaSerializer,
    TemaFormativoSerializer,
    AproveitamentoPropostaVioleirosCommandSerializer,
    CriacaoPropostaVioleirosCommandSerializer,
    EdicaoPropostaVioleirosCommandSerializer,
    ItemPropostaVioleirosCommandSerializer,
    PreenchimentoPropostaVioleirosCommandSerializer,
    PropostaVioleirosSerializer,
    ComandoSemPayloadSerializer,
    ResolucaoCadastralInscricaoSerializer,
    SelecaoCamposResolucaoSerializer,
    SubstituicaoPropostaVioleirosCommandSerializer,
    )
from .permissions import (
    AlpinistaQueryPolicy,
    CanRegisterPreparatoryAttendance,
    HasAnySiaRole,
    require_sia_roles,
)
from .services.reunioes_preparatorias import corrigir_presenca_preparatoria
from .services import avaliacoes_encontro as avaliacao_services
from .services import reunioes_preparatorias as reuniao_services
from .services import trabalhos as trabalho_services
from .services import formacoes as formacao_services
from .services import propostas_violeiros as proposta_violeiros_services
from .services import resolucao_cadastral as resolucao_cadastral_services
from .services import calendario_institucional as calendario_services
from .services import comandos_calendario as calendario_command_services
from .services import exportacao_calendario as exportacao_calendario_services
from .serializers import _erro_de_dominio, _erro_de_trabalho
from .formacao_catalogo import TEMAS_FORMATIVOS
from .roles import (
    EVENT_MANAGEMENT_ROLES,
    ENCOUNTER_PHOTO_MANAGEMENT_ROLES,
    ENCOUNTER_READ_ROLES,
    FICHAS_MANAGEMENT_ROLES,
    FORMATION_HISTORY_ROLES,
    FORMATION_MANAGEMENT_ROLES,
    FULL_ADMIN_ROLES,
    INSTITUTIONAL_CALENDAR_MANAGEMENT_ROLES,
    INSTITUTIONAL_CALENDAR_READ_ROLES,
    RECOGNIZED_ROLES,
    MUSIC_MANAGEMENT_ROLES,
    MME_PROPOSAL_MANAGEMENT_ROLES,
    MME_PROPOSAL_READ_ROLES,
    MATERIAL_MANAGEMENT_ROLES,
    PROFILE_PHOTO_MANAGEMENT_ROLES,
    user_has_any_role,
)

from django.db.models import Count
from django.db import IntegrityError, transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters


SUMMARY_PROFILE_FIELDS = (
    'id',
    'nome',
    'foto',
    'dataNascimento',
    'grupo',
    'telefone',
    'batizado',
    'primeira_comunhao',
    'crismado',
    'eh_violeiro',
    'canta',
    'nomePai',
    'telefonePai',
    'nomeMae',
    'telefoneMae',
)


def protected_image_response(image_field, filename):
    if not image_field:
        raise Http404('Imagem não encontrada.')
    try:
        content = image_field.open('rb')
    except (FileNotFoundError, OSError) as error:
        raise Http404('Arquivo de imagem não encontrado.') from error
    content_type = mimetypes.guess_type(image_field.name)[0] or 'application/octet-stream'
    return FileResponse(
        content,
        as_attachment=False,
        filename=filename,
        content_type=content_type,
    )


class ExportacaoCalendarioIndisponivel(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = 'calendar_export_unavailable'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Return the minimal authenticated identity required by the future BFF."""
    return Response(CurrentUserSerializer(request.user).data)


@api_view(['GET'])
@permission_classes([
    require_sia_roles(*INSTITUTIONAL_CALENDAR_READ_ROLES),
])
def calendario_institucional(request):
    query = PeriodoCalendarioQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    resultado = calendario_services.consultar_calendario_institucional(
        query.validated_data['inicio'],
        query.validated_data['fim'],
    )
    pode_gerir = request.user.is_superuser or user_has_any_role(
        request.user,
        *INSTITUTIONAL_CALENDAR_MANAGEMENT_ROLES,
    )
    serializer = ConsultaCalendarioInstitucionalSerializer(
        resultado,
        context={'pode_gerir_calendario': pode_gerir},
    )
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([
    require_sia_roles(*INSTITUTIONAL_CALENDAR_READ_ROLES),
])
def agenda_encontro(request, encontro_id):
    encontro = get_object_or_404(Encontro, pk=encontro_id)
    resultado = calendario_services.consultar_agenda_encontro(encontro)
    return Response(AgendaEncontroSerializer(resultado).data)


@api_view(['GET'])
@permission_classes([
    require_sia_roles(*INSTITUTIONAL_CALENDAR_MANAGEMENT_ROLES),
])
def preview_calendario_institucional(request):
    query = ExportacaoCalendarioCommandSerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    dados = query.validated_data
    snapshot = exportacao_calendario_services.capturar_snapshot(
        escopo=dados['escopo'],
        periodo=dados['periodo'],
        layout=dados['layout'],
        ano=dados['ano'],
        mes=dados.get('mes'),
    )
    conteudo = exportacao_calendario_services.renderizar_pdf(
        snapshot,
    )
    resposta = FileResponse(
        BytesIO(conteudo),
        as_attachment=False,
        filename=exportacao_calendario_services.nome_arquivo(snapshot),
        content_type='application/pdf',
    )
    resposta['Cache-Control'] = 'no-store, private'
    resposta['X-Content-Type-Options'] = 'nosniff'
    return resposta


def _pode_gerir_exportacao_calendario(user):
    return user.is_superuser or user_has_any_role(
        user,
        *INSTITUTIONAL_CALENDAR_MANAGEMENT_ROLES,
    )


@api_view(['GET', 'POST'])
@permission_classes([
    require_sia_roles(*INSTITUTIONAL_CALENDAR_READ_ROLES),
])
def publicacoes_calendario_institucional(request):
    pode_gerir = _pode_gerir_exportacao_calendario(request.user)
    if request.method == 'POST':
        if not pode_gerir:
            raise PermissionDenied(
                'Seu papel não pode publicar o Calendário Institucional.'
            )
        comando = ExportacaoCalendarioCommandSerializer(data=request.data)
        comando.is_valid(raise_exception=True)
        try:
            publicacao = exportacao_calendario_services.publicar_calendario(
                **comando.validated_data,
                autor=request.user,
            )
        except exportacao_calendario_services.LogoOficialIndisponivel as error:
            raise ExportacaoCalendarioIndisponivel(str(error)) from error
        return Response(
            PublicacaoCalendarioSerializer(
                publicacao,
                context={'request': request},
            ).data,
            status=status.HTTP_201_CREATED,
        )

    query = HistoricoPublicacaoCalendarioQuerySerializer(
        data=request.query_params,
    )
    query.is_valid(raise_exception=True)
    escopo = query.validated_data.get('escopo')
    if escopo == 'INTERNO' and not pode_gerir:
        raise PermissionDenied(
            'Seu papel não pode consultar publicações internas.'
        )
    publicacoes = PublicacaoCalendarioInstitucional.objects.select_related(
        'publicado_por',
    )
    if pode_gerir:
        if escopo:
            publicacoes = publicacoes.filter(escopo=escopo)
    else:
        publicacoes = publicacoes.filter(escopo='PUBLICO')
    return Response(PublicacaoCalendarioSerializer(
        publicacoes,
        many=True,
        context={'request': request},
    ).data)


@api_view(['GET'])
@permission_classes([
    require_sia_roles(*INSTITUTIONAL_CALENDAR_READ_ROLES),
])
def download_publicacao_calendario(request, publicacao_id):
    publicacao = get_object_or_404(
        PublicacaoCalendarioInstitucional,
        pk=publicacao_id,
    )
    if (
        publicacao.escopo == 'INTERNO'
        and not _pode_gerir_exportacao_calendario(request.user)
    ):
        raise PermissionDenied(
            'Seu papel não pode baixar publicações internas.'
        )
    try:
        arquivo = publicacao.arquivo_pdf.open('rb')
    except (FileNotFoundError, OSError) as error:
        raise Http404('Arquivo da publicação não encontrado.') from error
    resposta = FileResponse(
        arquivo,
        as_attachment=True,
        filename=exportacao_calendario_services.nome_arquivo_publicacao(
            publicacao
        ),
        content_type='application/pdf',
    )
    resposta['Cache-Control'] = 'private, no-store'
    resposta['X-Content-Type-Options'] = 'nosniff'
    return resposta


class CalendarioEncontroCommandViewSet(viewsets.GenericViewSet):
    queryset = Encontro.objects.all()
    serializer_class = CriacaoEncontroCalendarioCommandSerializer
    permission_classes = [
        require_sia_roles(*INSTITUTIONAL_CALENDAR_MANAGEMENT_ROLES),
    ]

    serializer_classes = {
        'create': CriacaoEncontroCalendarioCommandSerializer,
        'dados_basicos': DadosBasicosCalendarioCommandSerializer,
        'planejamento': PlanejamentoCalendarioCommandSerializer,
        'rotulo_dia': RotuloDiaCalendarioCommandSerializer,
        'oficializar': CalendarioSemDadosCommandSerializer,
        'reprogramar': PlanejamentoCalendarioCommandSerializer,
        'adiar': CalendarioSemDadosCommandSerializer,
        'iniciar_planejamento': PlanejamentoCalendarioCommandSerializer,
        'cancelar': CalendarioSemDadosCommandSerializer,
        'reunioes': ReuniaoAgendaCriacaoCommandSerializer,
        'reuniao': ReuniaoAgendaEdicaoCommandSerializer,
        'avaliacao': AvaliacaoAgendaCommandSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_classes.get(
            self.action,
            self.serializer_class,
        )

    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def _auditar(self, request, encontro, operacao, *, acao='UPDATE'):
        LogSistema.objects.create(
            usuario=request.user,
            acao=acao,
            modulo='CalendarioInstitucional',
            descricao=f'Encontro ID {encontro.pk}: {operacao}.',
        )

    def _resposta(self, encontro, *, http_status=status.HTTP_200_OK):
        encontro.refresh_from_db(fields=['status'])
        calendario = (
            CalendarioEncontro.objects
            .filter(encontro=encontro, vigente=True)
            .prefetch_related('dias')
            .first()
        )
        dias = []
        if calendario is not None:
            dias = list(calendario.dias.order_by('ordem', 'id'))
        agenda = calendario_services.consultar_agenda_encontro(encontro)
        avisos = calendario_services.detectar_conflitos_para_encontro(
            encontro.pk,
            [item.data for item in agenda.itens],
        )
        dados = {
            'encontro_id': encontro.pk,
            'status': encontro.status,
            'calendario_id': calendario.pk if calendario else None,
            'calendario_versao': calendario.versao if calendario else None,
            'confirmacao': (
                None
                if calendario is None
                else (
                    calendario_services.CONFIRMACAO_OFICIAL
                    if calendario.oficializado_em is not None
                    else calendario_services.CONFIRMACAO_PROVISORIA
                )
            ),
            'dias': dias,
            'agenda': agenda.itens,
            'avisos_conflito': avisos,
        }
        return Response(
            ResultadoComandoCalendarioSerializer(dados).data,
            status=http_status,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                encontro = calendario_command_services.criar_encontro(
                    titulo=serializer.validated_data['encontro'],
                    tipo=serializer.validated_data['tipo'],
                    local=serializer.validated_data['local'],
                    dias=serializer.validated_data['dias'],
                    reunioes=serializer.validated_data.get('reunioes', ()),
                    avaliacao=serializer.validated_data.get('avaliacao'),
                )
                self._auditar(
                    request,
                    encontro,
                    'criado pelo calendário',
                    acao='CREATE',
                )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro, http_status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='dados-basicos')
    def dados_basicos(self, request, pk=None):
        encontro = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                encontro = calendario_command_services.editar_dados_basicos(
                    encontro,
                    titulo=serializer.validated_data.get('encontro'),
                    local=serializer.validated_data.get('local'),
                )
                self._auditar(request, encontro, 'dados básicos alterados')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro)

    @action(detail=True, methods=['patch'], url_path='planejamento')
    def planejamento(self, request, pk=None):
        encontro = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                calendario_command_services.editar_planejamento(
                    encontro,
                    dias=serializer.validated_data['dias'],
                )
                self._auditar(request, encontro, 'planejamento alterado')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro)

    @action(
        detail=True,
        methods=['patch'],
        url_path=r'dias/(?P<dia_id>[^/.]+)/rotulo',
    )
    def rotulo_dia(self, request, pk=None, dia_id=None):
        encontro = self.get_object()
        dia = get_object_or_404(
            DiaEncontro,
            pk=dia_id,
            calendario__encontro=encontro,
            calendario__vigente=True,
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                dia = calendario_command_services.editar_rotulo_dia(
                    encontro,
                    dia_id=dia.pk,
                    rotulo=serializer.validated_data['rotulo'],
                )
                self._auditar(
                    request,
                    encontro,
                    f'rótulo do dia ID {dia.pk} alterado pela Agenda',
                )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro)

    @action(detail=True, methods=['post'], url_path='oficializar')
    def oficializar(self, request, pk=None):
        return self._executar_sem_dados(
            request,
            self.get_object(),
            calendario_command_services.oficializar_agenda,
            'agenda oficializada',
        )

    @action(detail=True, methods=['post'], url_path='reprogramar')
    def reprogramar(self, request, pk=None):
        encontro = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                calendario_command_services.reprogramar_agenda(
                    encontro,
                    dias=serializer.validated_data['dias'],
                )
                self._auditar(request, encontro, 'agenda reprogramada')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro)

    @action(detail=True, methods=['post'], url_path='adiar')
    def adiar(self, request, pk=None):
        return self._executar_sem_dados(
            request,
            self.get_object(),
            calendario_command_services.adiar_encontro,
            'Encontro adiado',
        )

    @action(
        detail=True,
        methods=['post'],
        url_path='iniciar-planejamento',
    )
    def iniciar_planejamento(self, request, pk=None):
        encontro = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                calendario_command_services.iniciar_novo_planejamento(
                    encontro,
                    dias=serializer.validated_data['dias'],
                )
                self._auditar(request, encontro, 'novo planejamento iniciado')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        return self._executar_sem_dados(
            request,
            self.get_object(),
            calendario_command_services.cancelar_encontro,
            'Encontro cancelado',
        )

    @action(detail=True, methods=['post'], url_path='reunioes')
    def reunioes(self, request, pk=None):
        encontro = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                reuniao = reuniao_services.criar_reuniao_preparatoria(
                    encontro=encontro,
                    **serializer.validated_data,
                )
                self._auditar(
                    request,
                    encontro,
                    f'reunião preparatória ID {reuniao.pk} criada pela Agenda',
                    acao='CREATE',
                )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro, http_status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['patch'],
        url_path=r'reunioes/(?P<reuniao_id>[^/.]+)',
    )
    def reuniao(self, request, pk=None, reuniao_id=None):
        encontro = self.get_object()
        reuniao = get_object_or_404(
            ReuniaoPreparatoriaEncontro,
            pk=reuniao_id,
            encontro=encontro,
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                reuniao_services.editar_reuniao_preparatoria(
                    reuniao,
                    **serializer.validated_data,
                )
                self._auditar(
                    request,
                    encontro,
                    f'reunião preparatória ID {reuniao.pk} alterada pela Agenda',
                )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro)

    @action(
        detail=True,
        methods=['post', 'patch', 'delete'],
        url_path='avaliacao',
    )
    def avaliacao(self, request, pk=None):
        encontro = self.get_object()
        if request.method == 'POST':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                with transaction.atomic():
                    avaliacao = avaliacao_services.criar_avaliacao_encontro(
                        encontro=encontro,
                        **serializer.validated_data,
                    )
                    self._auditar(
                        request,
                        encontro,
                        f'avaliação ID {avaliacao.pk} criada pela Agenda',
                        acao='CREATE',
                    )
            except django_core_validation_error as error:
                _erro_de_dominio(error)
            return self._resposta(
                encontro,
                http_status=status.HTTP_201_CREATED,
            )

        avaliacao = get_object_or_404(AvaliacaoEncontro, encontro=encontro)
        if request.method == 'PATCH':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                with transaction.atomic():
                    avaliacao_services.editar_avaliacao_encontro(
                        avaliacao,
                        **serializer.validated_data,
                    )
                    self._auditar(
                        request,
                        encontro,
                        f'avaliação ID {avaliacao.pk} alterada pela Agenda',
                    )
            except django_core_validation_error as error:
                _erro_de_dominio(error)
            return self._resposta(encontro)

        with transaction.atomic():
            avaliacao_id = avaliacao.pk
            avaliacao_services.remover_avaliacao_encontro(avaliacao)
            self._auditar(
                request,
                encontro,
                f'avaliação ID {avaliacao_id} removida pela Agenda',
                acao='DELETE',
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _executar_sem_dados(self, request, encontro, comando, operacao):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                comando(encontro)
                self._auditar(request, encontro, operacao)
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(encontro)


@api_view(['GET'])
@permission_classes([require_sia_roles(*FORMATION_HISTORY_ROLES)])
def catalogo_formacao(request):
    encontro_id = request.query_params.get('encontro')
    if not encontro_id:
        raise ValidationError({'encontro': ['Este filtro é obrigatório.']})
    encontro = get_object_or_404(Encontro, pk=encontro_id)
    temas = sorted(
        (
            tema
            for tema in TEMAS_FORMATIVOS.values()
            if encontro.tipo in tema.tipos_encontro
        ),
        key=lambda tema: tema.ordem,
    )
    return Response(TemaFormativoSerializer(temas, many=True).data)


class AuditedCrudViewSetMixin:
    """Keep CRUD changes and their identifier-only audit log together."""

    audit_module = None

    def _write_audit_log(self, action, object_id, verb):
        LogSistema.objects.create(
            usuario=self.request.user,
            acao=action,
            modulo=self.audit_module,
            descricao=f'{self.audit_module} ID {object_id} {verb}.',
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            self._write_audit_log('CREATE', instance.pk, 'criado')

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            self._write_audit_log('UPDATE', instance.pk, 'alterado')

    def perform_destroy(self, instance):
        object_id = instance.pk
        with transaction.atomic():
            instance.delete()
            self._write_audit_log('DELETE', object_id, 'excluído')


class AlpinistaFilter(django_filters.FilterSet):
    palestrou = django_filters.BooleanFilter(method='filter_palestrou')

    class Meta:
        model = Alpinista
        fields = ('status', 'eh_violeiro', 'canta', 'palestrou')

    def filter_palestrou(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(palestras__isnull=not value).distinct()


class AlpinistaViewSet(viewsets.ModelViewSet):
    queryset = Alpinista.objects.all().order_by('nome') #Busca todos os alpinistas no banco de dados
    serializer_class = AlpinistaCompletoSerializer
    permission_classes = [HasAnySiaRole]
    read_roles = RECOGNIZED_ROLES
    write_roles = FICHAS_MANAGEMENT_ROLES
    action_roles = {
        'foto': PROFILE_PHOTO_MANAGEMENT_ROLES,
        'foto_arquivo': RECOGNIZED_ROLES,
        'musica': MUSIC_MANAGEMENT_ROLES,
        'historico_violeiro': MUSIC_MANAGEMENT_ROLES,
        'historico_palestras': FORMATION_HISTORY_ROLES,
        'historico_formativo': FORMATION_HISTORY_ROLES,
    }

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AlpinistaFilter
    search_fields = AlpinistaQueryPolicy.ADMIN_SEARCH_FIELDS
    ordering_fields = AlpinistaQueryPolicy.ADMIN_ORDERING_FIELDS

    def has_full_profile_access(self):
        user = self.request.user
        return user.is_superuser or user_has_any_role(
            user,
            *FICHAS_MANAGEMENT_ROLES,
        )

    def get_serializer_class(self):
        if self.action == 'foto':
            return AlpinistaFotoSerializer
        if self.action == 'musica':
            return AlpinistaMusicaCommandSerializer
        if self.action == 'historico_violeiro':
            return HistoricoVioleiroSerializer
        if self.action == 'historico_palestras':
            return HistoricoPalestraSerializer
        if self.action == 'historico_formativo':
            return HistoricoFormativoSerializer
        if self.has_full_profile_access():
            return AlpinistaCompletoSerializer
        return AlpinistaResumoSerializer

    @action(detail=True, methods=['patch', 'delete'], url_path='foto')
    def foto(self, request, pk=None):
        alpinista = self.get_object()
        foto_anterior = alpinista.foto
        nome_anterior = foto_anterior.name if foto_anterior else None
        storage = foto_anterior.storage if foto_anterior else None

        if request.method == 'DELETE':
            if nome_anterior:
                with transaction.atomic():
                    alpinista.foto = None
                    alpinista.save(update_fields=['foto'])
                    LogSistema.objects.create(
                        usuario=request.user,
                        acao='DELETE',
                        modulo='Alpinista',
                        descricao=f'Foto do Alpinista {alpinista.pk} removida.',
                    )
                storage.delete(nome_anterior)
            return Response({'id': alpinista.pk, 'foto': None})

        serializer = self.get_serializer(alpinista, data=request.data)
        serializer.is_valid(raise_exception=True)
        nome_novo = None
        novo_storage = None
        try:
            with transaction.atomic():
                alpinista = serializer.save()
                nome_novo = alpinista.foto.name
                novo_storage = alpinista.foto.storage
                LogSistema.objects.create(
                    usuario=request.user,
                    acao='UPDATE',
                    modulo='Alpinista',
                    descricao=(
                        f'Foto do Alpinista {alpinista.pk} '
                        f'{"substituída" if nome_anterior else "adicionada"}.'
                    ),
                )
        except Exception:
            if novo_storage and nome_novo and nome_novo != nome_anterior:
                novo_storage.delete(nome_novo)
            raise

        if nome_anterior and nome_anterior != nome_novo:
            storage.delete(nome_anterior)
        return Response({
            'id': alpinista.pk,
            'foto': serializer.data['foto'],
        })

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.has_full_profile_access():
            return queryset
        return queryset.only(*SUMMARY_PROFILE_FIELDS)

    def filter_queryset(self, queryset):
        AlpinistaQueryPolicy.validate(self.request.user, self.request.query_params)
        self.search_fields = AlpinistaQueryPolicy.search_fields(self.request.user)
        self.ordering_fields = AlpinistaQueryPolicy.ordering_fields(
            self.request.user
        )
        return super().filter_queryset(queryset)

    @action(detail=True, methods=['get'], url_path='foto-arquivo')
    def foto_arquivo(self, request, pk=None):
        alpinista = self.get_object()
        suffix = Path(alpinista.foto.name).suffix.lower() if alpinista.foto else ''
        return protected_image_response(
            alpinista.foto,
            f'alpinista-{alpinista.pk}{suffix}',
        )

    @action(detail=True, methods=['patch'], url_path='musica')
    def musica(self, request, pk=None):
        alpinista = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        field_mapping = {
            'violeiro': 'eh_violeiro',
            'canta': 'canta',
        }
        alteracoes = []
        update_fields = []
        for api_field, model_field in field_mapping.items():
            if api_field not in serializer.validated_data:
                continue
            valor_anterior = getattr(alpinista, model_field)
            novo_valor = serializer.validated_data[api_field]
            if valor_anterior != novo_valor:
                setattr(alpinista, model_field, novo_valor)
                update_fields.append(model_field)
                alteracoes.append(
                    f'{model_field}: {valor_anterior} -> {novo_valor}'
                )

        if update_fields:
            alpinista.save(update_fields=update_fields)
            LogSistema.objects.create(
                usuario=request.user,
                acao='UPDATE',
                modulo='Alpinista',
                descricao=(
                    f'Características musicais do Alpinista {alpinista.pk}: '
                    f'{"; ".join(alteracoes)}.'
                ),
            )

        return Response({
            'id': alpinista.pk,
            'musica': {
                'violeiro': alpinista.eh_violeiro,
                'canta': alpinista.canta,
            },
        })

    @action(detail=True, methods=['get'], url_path='historico-violeiro')
    def historico_violeiro(self, request, pk=None):
        alpinista = self.get_object()
        participacoes = (
            alpinista.participacoes_encontros
            .filter(funcao__eh_violeiro=True)
            .select_related('encontro', 'funcao')
            .order_by('-encontro__data_referencia', '-id')
        )
        serializer = self.get_serializer(participacoes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='historico-palestras')
    def historico_palestras(self, request, pk=None):
        alpinista = self.get_object()
        palestras = (
            Palestra.objects
            .filter(alpinista=alpinista)
            .select_related('encontro')
            .order_by('-encontro__data_referencia', '-id')
        )
        serializer = self.get_serializer(palestras, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='historico-formativo')
    def historico_formativo(self, request, pk=None):
        alpinista = self.get_object()
        if alpinista.pessoa_id is None:
            raise Http404('PerfilAlpinista não encontrado.')
        perfil = get_object_or_404(
            PerfilAlpinista,
            pessoa_id=alpinista.pessoa_id,
        )
        historico = formacao_services.obter_historico_formativo(perfil)
        serializer = self.get_serializer(historico, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        alpinista = serializer.save()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='CREATE',
            modulo='Alpinista',
            descricao=f'Alpinista ID {alpinista.pk} criado.'
        )
    
    def perform_update(self, serializer):
        alpinista = serializer.save()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='UPDATE',
            modulo='Alpinista',
            descricao=f'Alpinista ID {alpinista.pk} atualizado.'
        )

    def perform_destroy(self, instance):
        alpinista_id = instance.pk
        instance.delete()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='DELETE',
            modulo='Alpinista',
            descricao=f'Alpinista ID {alpinista_id} excluído.'
        )

class EncontroViewSet(viewsets.ModelViewSet):
    queryset = Encontro.objects.all().order_by('-data_referencia') 
    serializer_class = EncontroSerializer
    permission_classes = [HasAnySiaRole]
    read_roles = ENCOUNTER_READ_ROLES
    write_roles = FICHAS_MANAGEMENT_ROLES
    action_roles = {
        'fotos': ENCOUNTER_PHOTO_MANAGEMENT_ROLES,
        'foto_detail': ENCOUNTER_PHOTO_MANAGEMENT_ROLES,
        'foto_arquivo': ENCOUNTER_PHOTO_MANAGEMENT_ROLES,
        'efetivar_encontrista': FICHAS_MANAGEMENT_ROLES,
        'remover_encontristas': FICHAS_MANAGEMENT_ROLES,
        'preparar_equipes': FICHAS_MANAGEMENT_ROLES,
    }

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['encontro']
    search_fields = ['encontro']
    ordering_fields = ['data_referencia', 'encontro']

    def has_full_encontro_access(self):
        user = self.request.user
        return user.is_superuser or user_has_any_role(
            user,
            *FICHAS_MANAGEMENT_ROLES,
        )

    def get_serializer_class(self):
        if self.action in {'fotos', 'foto_detail'}:
            return FotoEncontroSerializer
        if self.has_full_encontro_access():
            return EncontroSerializer
        return EncontroComunicacaoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.has_full_encontro_access():
            return queryset
        return queryset.only('id', 'encontro', 'tipo', 'data_referencia')

    @action(detail=True, methods=['post'], url_path='preparar-equipes')
    def preparar_equipes(self, request, pk=None):
        encontro = self.get_object()
        with transaction.atomic():
            equipes = trabalho_services.preparar_equipes_encontro(encontro)
            LogSistema.objects.create(
                usuario=request.user,
                acao='CREATE',
                modulo='EquipeEncontro',
                descricao=f'Equipes do Encontro {encontro.pk} preparadas.',
            )
        return Response(
            EquipeEncontroSerializer(
                equipes,
                many=True,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get', 'post'], url_path='fotos')
    def fotos(self, request, pk=None):
        encontro = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(encontro.fotos.all(), many=True)
            return Response(serializer.data)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        foto = None
        try:
            with transaction.atomic():
                foto = serializer.save(encontro=encontro)
                LogSistema.objects.create(
                    usuario=request.user,
                    acao='CREATE',
                    modulo='FotoEncontro',
                    descricao=f'Foto {foto.pk} adicionada ao Encontro {encontro.pk}.',
                )
        except Exception:
            if foto and foto.imagem:
                foto.imagem.storage.delete(foto.imagem.name)
            raise
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path=r'fotos/(?P<foto_id>[^/.]+)',
    )
    def foto_detail(self, request, pk=None, foto_id=None):
        encontro = self.get_object()
        foto = get_object_or_404(
            FotoEncontro,
            pk=foto_id,
            encontro=encontro,
        )
        nome_anterior = foto.imagem.name
        storage = foto.imagem.storage

        if request.method == 'DELETE':
            foto_pk = foto.pk
            with transaction.atomic():
                foto.delete()
                LogSistema.objects.create(
                    usuario=request.user,
                    acao='DELETE',
                    modulo='FotoEncontro',
                    descricao=f'Foto {foto_pk} removida do Encontro {encontro.pk}.',
                )
            storage.delete(nome_anterior)
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = self.get_serializer(foto, data=request.data)
        serializer.is_valid(raise_exception=True)
        nome_novo = None
        novo_storage = None
        try:
            with transaction.atomic():
                foto = serializer.save()
                nome_novo = foto.imagem.name
                novo_storage = foto.imagem.storage
                LogSistema.objects.create(
                    usuario=request.user,
                    acao='UPDATE',
                    modulo='FotoEncontro',
                    descricao=f'Foto {foto.pk} substituída no Encontro {encontro.pk}.',
                )
        except Exception:
            if novo_storage and nome_novo and nome_novo != nome_anterior:
                novo_storage.delete(nome_novo)
            raise

        if nome_anterior != nome_novo:
            storage.delete(nome_anterior)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'fotos/(?P<foto_id>[^/.]+)/arquivo',
    )
    def foto_arquivo(self, request, pk=None, foto_id=None):
        encontro = self.get_object()
        foto = get_object_or_404(
            FotoEncontro,
            pk=foto_id,
            encontro=encontro,
        )
        suffix = Path(foto.imagem.name).suffix.lower()
        return protected_image_response(
            foto.imagem,
            f'encontro-{encontro.pk}-foto-{foto.pk}{suffix}',
        )

    def perform_create(self, serializer):
        encontro = serializer.save()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='CREATE',
            modulo='Encontro',
            descricao=f'Encontro {encontro.encontro} criado.'
        )
    
    def perform_update(self, serializer):
        encontro = serializer.save()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='UPDATE',
            modulo='Encontro',
            descricao=f'Encontro {encontro.encontro} atualizado.'
        )

    def perform_destroy(self, instance):
        nome_encontro = instance.encontro
        instance.delete()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='DELETE',
            modulo='Encontro',
            descricao=f'Encontro {nome_encontro} excluído.'
        )

    @action(detail=True, methods=['post'], url_path='efetivar-encontristas')
    def efetivar_encontrista (self, request, pk=None):
        encontro = self.get_object()
        alpinistas_ids = request.data.get('alpinistas_ids', [])

        if not alpinistas_ids:
            return Response({"erro": "Nenhum alpinista selecionado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                funcao = (
                    FuncaoEncontro.objects
                    .filter(tipo='encontrista')
                    .order_by('pk')
                    .first()
                )
                if funcao is None:
                    funcao = FuncaoEncontro.objects.create(
                        nome='Encontrista',
                        tipo='encontrista',
                    )

                sucessos = 0
                for alp_id in alpinistas_ids:
                    alpinista = Alpinista.objects.get(id=alp_id)

                    ParticipacaoEncontro.objects.get_or_create(
                        encontro=encontro,
                        alpinista=alpinista,
                        funcao=funcao
                    )

                    sucessos += 1

                LogSistema.objects.create(
                    usuario=request.user,
                    acao='CREATE',
                    modulo='ParticipacaoEncontro',
                    descricao=(
                        f'Efetivação em lote no Encontro ID {encontro.pk}; '
                        f'Alpinistas IDs {list(alpinistas_ids)}.'
                    ),
                )
        except Alpinista.DoesNotExist:
            return Response(
                {"erro": "Alpinista não encontrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {"erro": "Não foi possível efetivar o lote."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"mensagem": f"{sucessos} alpinistas efetivados com sucesso."}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'], url_path='remover-encontristas')
    def remover_encontristas(self, request, pk=None):
        encontro = self.get_object()
        alpinistas_ids = request.data.get('alpinistas_ids', [])
        
        if not alpinistas_ids:
            return Response({"erro": "Nenhum alpinista selecionado."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                sucessos = 0
                removidos_ids = []
                for alp_id in alpinistas_ids:
                    try:
                        alpinista = Alpinista.objects.get(id=alp_id)
                    except Alpinista.DoesNotExist:
                        continue

                    participacao = ParticipacaoEncontro.objects.filter(
                        encontro=encontro,
                        alpinista=alpinista,
                        funcao__tipo='encontrista',
                    ).first()

                    if participacao:
                        participacao.delete()

                        sucessos += 1
                        removidos_ids.append(alpinista.pk)

                LogSistema.objects.create(
                    usuario=request.user,
                    acao='DELETE',
                    modulo='ParticipacaoEncontro',
                    descricao=(
                        f'Remoção em lote no Encontro ID {encontro.pk}; '
                        f'Alpinistas IDs {removidos_ids}.'
                    ),
                )
        except IntegrityError:
            return Response(
                {"erro": "Não foi possível remover o lote."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"mensagem": f"{sucessos} encontristas removidos com sucesso!"},
            status=status.HTTP_200_OK,
        )


class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all().order_by('data_evento', 'id')
    serializer_class = EventoSerializer 
    permission_classes = [require_sia_roles(*EVENT_MANAGEMENT_ROLES)]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = [ 'nome', 'local']
    ordering_fields = ['data_evento', 'nome']

    def perform_create(self, serializer):
        evento = serializer.save()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='CREATE',
            modulo='Evento',
            descricao=f'Evento {evento.nome} criado.'
        )
    
    def perform_update(self, serializer):
        evento = serializer.save()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='UPDATE',
            modulo='Evento',
            descricao=f'Evento {evento.nome} atualizado.'
        )

    def perform_destroy(self, instance):
        nome_evento = instance.nome
        instance.delete()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='DELETE',
            modulo='Evento',
            descricao=f'Evento {nome_evento} excluído.'
        )

class FuncaoEncontroViewSet(AuditedCrudViewSetMixin, viewsets.ModelViewSet):
    queryset = FuncaoEncontro.objects.all() 
    serializer_class = FuncaoEncontroSerializer 
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]
    pagination_class = None
    audit_module = 'FuncaoEncontro'

class ParticipacaoEncontroViewSet(AuditedCrudViewSetMixin, viewsets.ModelViewSet):
    queryset = ParticipacaoEncontro.objects.select_related('alpinista', 'encontro', 'funcao').all()
    serializer_class = ParticipacaoEncontroSerializer
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]
    audit_module = 'ParticipacaoEncontro'

    pagination_class = None

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['encontro', 'alpinista', 'funcao']  # Permite filtrar por encontro, alpinista e função


class InscricaoEncontroCommandViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Inscricao.objects.select_related('pessoa').all()
    serializer_class = InscricaoEncontroCommandSerializer
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]

    def perform_create(self, serializer):
        with transaction.atomic():
            inscricao = serializer.save()
            LogSistema.objects.create(
                usuario=self.request.user,
                acao='CREATE',
                modulo='Inscricao',
                descricao=f'Inscrição ID {inscricao.pk} criada.',
            )


class InscricaoResolucaoCadastralViewSet(
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ResolucaoCadastralInscricaoSerializer
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]

    def get_queryset(self):
        return (
            InscricaoEncontro.objects
            .select_related('encontro', 'pessoa', 'dados_declarados')
            .prefetch_related(
                'correspondencias_cadastrais__pessoa_candidata__telefones',
                'correspondencias_cadastrais__decidida_por',
            )
            .order_by('id')
        )

    def get_serializer_class(self):
        if self.action in {
            'gerar_sugestoes',
            'aceitar_correspondencia',
            'rejeitar_correspondencia',
        }:
            return ComandoSemPayloadSerializer
        if self.action in {'criar_pessoa', 'aplicar_campos'}:
            return SelecaoCamposResolucaoSerializer
        return ResolucaoCadastralInscricaoSerializer

    def _resposta(self, inscricao, *, codigo=status.HTTP_200_OK):
        inscricao = self.get_queryset().get(pk=inscricao.pk)
        return Response(
            ResolucaoCadastralInscricaoSerializer(inscricao).data,
            status=codigo,
        )

    def _validar_comando(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def _correspondencia(self, inscricao, correspondencia_id):
        return get_object_or_404(
            CorrespondenciaCadastralInscricao,
            pk=correspondencia_id,
            inscricao=inscricao,
        )

    @action(detail=True, methods=['post'], url_path='gerar-sugestoes')
    def gerar_sugestoes(self, request, pk=None):
        inscricao = self.get_object()
        self._validar_comando(request)
        try:
            resolucao_cadastral_services.gerar_sugestoes_cadastrais(
                usuario=request.user,
                inscricao=inscricao,
            )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(inscricao)

    @action(
        detail=True,
        methods=['post'],
        url_path=(
            r'correspondencias/(?P<correspondencia_id>\d+)/aceitar'
        ),
    )
    def aceitar_correspondencia(
        self,
        request,
        pk=None,
        correspondencia_id=None,
    ):
        inscricao = self.get_object()
        self._validar_comando(request)
        correspondencia = self._correspondencia(
            inscricao,
            correspondencia_id,
        )
        try:
            resolucao_cadastral_services.aceitar_correspondencia_cadastral(
                usuario=request.user,
                inscricao=inscricao,
                correspondencia=correspondencia,
            )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(inscricao)

    @action(
        detail=True,
        methods=['post'],
        url_path=(
            r'correspondencias/(?P<correspondencia_id>\d+)/rejeitar'
        ),
    )
    def rejeitar_correspondencia(
        self,
        request,
        pk=None,
        correspondencia_id=None,
    ):
        inscricao = self.get_object()
        self._validar_comando(request)
        correspondencia = self._correspondencia(
            inscricao,
            correspondencia_id,
        )
        try:
            resolucao_cadastral_services.rejeitar_correspondencia_cadastral(
                usuario=request.user,
                inscricao=inscricao,
                correspondencia=correspondencia,
            )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(inscricao)

    @action(detail=True, methods=['post'], url_path='criar-pessoa')
    def criar_pessoa(self, request, pk=None):
        inscricao = self.get_object()
        dados = self._validar_comando(request)
        try:
            resolucao_cadastral_services.criar_pessoa_da_inscricao(
                usuario=request.user,
                inscricao=inscricao,
                campos=dados['campos'],
            )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(inscricao, codigo=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='aplicar-campos')
    def aplicar_campos(self, request, pk=None):
        inscricao = self.get_object()
        dados = self._validar_comando(request)
        try:
            resolucao_cadastral_services.aplicar_dados_declarados(
                usuario=request.user,
                inscricao=inscricao,
                campos=dados['campos'],
            )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(inscricao)


class ConviteEncontroCommandViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ConviteEncontro.objects.select_related(
        'pessoa',
        'encontro',
        'inscricao',
    )
    serializer_class = ConviteEncontroCommandSerializer
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]

    def perform_create(self, serializer):
        with transaction.atomic():
            convite = serializer.save()
            avaliacao = getattr(convite, 'avaliacao_elegibilidade', None)
            codigos = (
                ','.join(avaliacao.codigos)
                if avaliacao is not None
                else '-'
            )
            avisos_confirmados = bool(
                avaliacao is not None and avaliacao.avisos
            )
            LogSistema.objects.create(
                usuario=self.request.user,
                acao='CREATE',
                modulo='ConviteEncontro',
                descricao=(
                    f'ConviteEncontro ID {convite.pk} criado; '
                    f'avisos_confirmados={str(avisos_confirmados).lower()}; '
                    f'códigos de avaliação: {codigos}.'
                ),
            )

    @action(detail=True, methods=['post'], url_path='responder')
    def responder(self, request, pk=None):
        convite = self.get_object()
        serializer = RespostaConviteEncontroCommandSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            convite = serializer.save(convite=convite)
            LogSistema.objects.create(
                usuario=request.user,
                acao='UPDATE',
                modulo='ConviteEncontro',
                descricao=f'ConviteEncontro ID {convite.pk} respondido.',
            )
        return Response(
            self.get_serializer(convite).data,
            status=status.HTTP_200_OK,
        )


class ResultadoParticipacaoCommandViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ResultadoParticipacaoEncontro.objects.select_related(
        'pessoa',
        'encontro',
        'convite',
    )
    serializer_class = ResultadoParticipacaoCommandSerializer
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]

    def perform_create(self, serializer):
        with transaction.atomic():
            participacao = serializer.save()
            LogSistema.objects.create(
                usuario=self.request.user,
                acao='CREATE',
                modulo='ParticipacaoEncontroResultado',
                descricao=(
                    f'ParticipacaoEncontroResultado ID {participacao.pk} '
                    'registrada.'
                ),
            )


class EquipeEncontroViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EquipeEncontroSerializer
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]
    pagination_class = None

    def get_queryset(self):
        queryset = (
            EquipeEncontro.objects
            .select_related('encontro', 'template_origem')
            .prefetch_related('roles__trabalhos__pessoa')
            .order_by('encontro_id', 'ordem', 'id')
        )
        encontro_id = self.request.query_params.get('encontro')
        if self.action == 'list':
            if not encontro_id:
                raise ValidationError({
                    'encontro': ['Este filtro é obrigatório.'],
                })
            queryset = queryset.filter(encontro_id=encontro_id)
        return queryset


class TrabalhoEncontroCommandViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TrabalhoEncontroCommandSerializer
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]
    pagination_class = None

    def get_queryset(self):
        queryset = (
            TrabalhoEncontro.objects
            .select_related(
                'pessoa',
                'encontro',
                'convite',
                'role_equipe__equipe_encontro',
            )
            .order_by('id')
        )
        encontro_id = self.request.query_params.get('encontro')
        if self.action == 'list':
            if not encontro_id:
                raise ValidationError({
                    'encontro': ['Este filtro é obrigatório.'],
                })
            queryset = queryset.filter(encontro_id=encontro_id)
        return queryset

    def get_serializer_class(self):
        return {
            'alocar': AlocacaoTrabalhoCommandSerializer,
            'realocar': AlocacaoTrabalhoCommandSerializer,
            'resultado': ResultadoTrabalhoCommandSerializer,
            'substituir': SubstituicaoTrabalhoCommandSerializer,
        }.get(self.action, TrabalhoEncontroCommandSerializer)

    def _resposta(self, trabalho):
        return Response(
            TrabalhoEncontroCommandSerializer(
                trabalho,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_200_OK,
        )

    def _auditar(self, request, trabalho, operacao, *, acao='UPDATE'):
        avaliacao = getattr(trabalho, 'avaliacao_elegibilidade', None)
        codigos = ','.join(avaliacao.codigos) if avaliacao is not None else '-'
        avisos_confirmados = bool(avaliacao is not None and avaliacao.avisos)
        LogSistema.objects.create(
            usuario=request.user,
            acao=acao,
            modulo='TrabalhoEncontro',
            descricao=(
                f'TrabalhoEncontro ID {trabalho.pk}: {operacao}; '
                f'avisos_confirmados={str(avisos_confirmados).lower()}; '
                f'códigos de avaliação: {codigos}.'
            ),
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            trabalho = serializer.save()
            self._auditar(
                self.request,
                trabalho,
                'iniciado',
                acao='CREATE',
            )

    def _executar_com_avaliacao(self, request, operacao, nome):
        trabalho = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                trabalho = operacao(trabalho, **serializer.validated_data)
                self._auditar(request, trabalho, nome)
        except django_core_validation_error as error:
            _erro_de_trabalho(error)
        return self._resposta(trabalho)

    @action(detail=True, methods=['post'])
    def alocar(self, request, pk=None):
        return self._executar_com_avaliacao(
            request,
            trabalho_services.alocar_trabalho,
            'alocado',
        )

    @action(detail=True, methods=['post'])
    def realocar(self, request, pk=None):
        return self._executar_com_avaliacao(
            request,
            trabalho_services.alocar_trabalho,
            'realocado',
        )

    @action(detail=True, methods=['post'])
    def desalocar(self, request, pk=None):
        trabalho = self.get_object()
        try:
            with transaction.atomic():
                trabalho = trabalho_services.desalocar_trabalho(trabalho)
                self._auditar(request, trabalho, 'desalocado')
        except django_core_validation_error as error:
            _erro_de_trabalho(error)
        return self._resposta(trabalho)

    @action(detail=True, methods=['post'])
    def retirar(self, request, pk=None):
        trabalho = self.get_object()
        try:
            with transaction.atomic():
                trabalho = trabalho_services.retirar_trabalho(trabalho)
                self._auditar(request, trabalho, 'retirado')
        except django_core_validation_error as error:
            _erro_de_trabalho(error)
        return self._resposta(trabalho)

    @action(detail=True, methods=['post'])
    def resultado(self, request, pk=None):
        trabalho = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                trabalho = trabalho_services.registrar_resultado_trabalho(
                    trabalho,
                    **serializer.validated_data,
                )
                self._auditar(request, trabalho, 'resultado registrado')
        except django_core_validation_error as error:
            _erro_de_trabalho(error)
        return self._resposta(trabalho)

    @action(detail=True, methods=['post'])
    def substituir(self, request, pk=None):
        trabalho = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                anterior, novo = trabalho_services.substituir_trabalho(
                    trabalho,
                    **serializer.validated_data,
                )
                self._auditar(request, anterior, 'substituído')
                self._auditar(request, novo, 'substituto alocado')
        except django_core_validation_error as error:
            _erro_de_trabalho(error)
        return Response({
            'anterior': TrabalhoEncontroCommandSerializer(anterior).data,
            'novo': TrabalhoEncontroCommandSerializer(novo).data,
        })


class PropostaVioleirosViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [HasAnySiaRole]
    read_roles = MME_PROPOSAL_READ_ROLES
    write_roles = MME_PROPOSAL_MANAGEMENT_ROLES
    action_roles = {
        'editar_nome': MME_PROPOSAL_MANAGEMENT_ROLES,
        'preencher_posicao': MME_PROPOSAL_MANAGEMENT_ROLES,
        'substituir_posicao': MME_PROPOSAL_MANAGEMENT_ROLES,
        'retirar_item': MME_PROPOSAL_MANAGEMENT_ROLES,
        'encerrar': MME_PROPOSAL_MANAGEMENT_ROLES,
        'resumo': MME_PROPOSAL_READ_ROLES,
        'aproveitar_candidato': FICHAS_MANAGEMENT_ROLES,
    }
    pagination_class = None

    def get_queryset(self):
        queryset = (
            PropostaVioleiros.objects
            .select_related('encontro')
            .order_by('encontro_id', 'criada_em', 'id')
        )
        encontro_id = self.request.query_params.get('encontro')
        if self.action == 'list':
            if not encontro_id:
                raise ValidationError({
                    'encontro': ['Este filtro é obrigatório.'],
                })
            queryset = queryset.filter(encontro_id=encontro_id)
        return queryset

    def get_serializer_class(self):
        return {
            'create': CriacaoPropostaVioleirosCommandSerializer,
            'editar_nome': EdicaoPropostaVioleirosCommandSerializer,
            'preencher_posicao': (
                PreenchimentoPropostaVioleirosCommandSerializer
            ),
            'substituir_posicao': (
                SubstituicaoPropostaVioleirosCommandSerializer
            ),
            'retirar_item': ItemPropostaVioleirosCommandSerializer,
            'aproveitar_candidato': (
                AproveitamentoPropostaVioleirosCommandSerializer
            ),
        }.get(self.action, PropostaVioleirosSerializer)

    def _resposta(self, proposta, *, status_code=status.HTTP_200_OK):
        proposta = self.get_queryset().get(pk=proposta.pk)
        return Response(
            PropostaVioleirosSerializer(
                proposta,
                context=self.get_serializer_context(),
            ).data,
            status=status_code,
        )

    def _auditar(self, request, proposta, operacao, *, acao='UPDATE'):
        LogSistema.objects.create(
            usuario=request.user,
            acao=acao,
            modulo='PropostaVioleiros',
            descricao=f'PropostaVioleiros ID {proposta.pk}: {operacao}.',
        )

    def list(self, request, *args, **kwargs):
        precisa_completar = request.query_params.get('precisa_completar')
        if precisa_completar not in {None, 'true', 'false'}:
            raise ValidationError({
                'precisa_completar': ['Use true ou false.'],
            })

        propostas = list(self.get_queryset())
        for proposta in propostas:
            proposta._resumo_violeiros = (
                proposta_violeiros_services.resumir_proposta_violeiros(
                    proposta
                )
            )
        if precisa_completar is not None:
            esperado = precisa_completar == 'true'
            propostas = [
                proposta
                for proposta in propostas
                if (
                    proposta.status == PropostaVioleiros.Status.ABERTA
                    and proposta._resumo_violeiros.precisa_completar
                ) == esperado
            ]
        return Response(PropostaVioleirosSerializer(
            propostas,
            many=True,
            context=self.get_serializer_context(),
        ).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                proposta = (
                    proposta_violeiros_services.criar_proposta_violeiros(
                        **serializer.validated_data,
                    )
                )
                self._auditar(request, proposta, 'criada', acao='CREATE')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(proposta, status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='editar-nome')
    def editar_nome(self, request, pk=None):
        proposta = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                proposta = (
                    proposta_violeiros_services.editar_proposta_violeiros(
                        proposta,
                        **serializer.validated_data,
                    )
                )
                self._auditar(request, proposta, 'nome alterado')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(proposta)

    @action(detail=True, methods=['post'], url_path='preencher-posicao')
    def preencher_posicao(self, request, pk=None):
        proposta = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                item = (
                    proposta_violeiros_services.preencher_posicao_proposta(
                        proposta,
                        **serializer.validated_data,
                    )
                )
                self._auditar(
                    request,
                    proposta,
                    f'posição preenchida pelo item {item.pk}',
                )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(proposta, status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='substituir-posicao')
    def substituir_posicao(self, request, pk=None):
        proposta = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = get_object_or_404(
            ItemPropostaVioleiros,
            pk=serializer.validated_data['item'].pk,
            proposta=proposta,
        )
        try:
            with transaction.atomic():
                anterior, novo = (
                    proposta_violeiros_services.substituir_ocupacao_proposta(
                        item,
                        perfil_alpinista=(
                            serializer.validated_data['perfil_alpinista']
                        ),
                    )
                )
                self._auditar(
                    request,
                    proposta,
                    f'item {anterior.pk} substituído pelo item {novo.pk}',
                )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(proposta)

    @action(detail=True, methods=['post'], url_path='retirar-item')
    def retirar_item(self, request, pk=None):
        proposta = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = get_object_or_404(
            ItemPropostaVioleiros,
            pk=serializer.validated_data['item'].pk,
            proposta=proposta,
        )
        try:
            with transaction.atomic():
                item = proposta_violeiros_services.retirar_item_proposta(item)
                self._auditar(
                    request,
                    proposta,
                    f'item {item.pk} retirado',
                )
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(proposta)

    @action(detail=True, methods=['post'])
    def encerrar(self, request, pk=None):
        proposta = self.get_object()
        try:
            with transaction.atomic():
                proposta = (
                    proposta_violeiros_services.encerrar_proposta_violeiros(
                        proposta
                    )
                )
                self._auditar(request, proposta, 'encerrada')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(proposta)

    @action(detail=True, methods=['get'])
    def resumo(self, request, pk=None):
        return self._resposta(self.get_object())

    @action(detail=True, methods=['post'], url_path='aproveitar-candidato')
    def aproveitar_candidato(self, request, pk=None):
        proposta = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = get_object_or_404(
            ItemPropostaVioleiros,
            pk=serializer.validated_data['item'].pk,
            proposta=proposta,
        )
        try:
            with transaction.atomic():
                pessoa = (
                    proposta_violeiros_services
                    .obter_candidato_para_aproveitamento(item)
                )
                convite = trabalho_services.criar_convite_trabalho(
                    pessoa=pessoa,
                    encontro=proposta.encontro,
                    role_proposta=serializer.validated_data.get('role_equipe'),
                    confirmar_avisos=serializer.validated_data.get(
                        'confirmar_avisos',
                        False,
                    ),
                )
                LogSistema.objects.create(
                    usuario=request.user,
                    acao='CREATE',
                    modulo='ConviteEncontro',
                    descricao=(
                        f'ConviteEncontro ID {convite.pk}: aproveitamento do '
                        f'ItemPropostaVioleiros ID {item.pk} solicitado.'
                    ),
                )
        except django_core_validation_error as error:
            _erro_de_trabalho(error)
        return Response(
            ConviteEncontroCommandSerializer(
                convite,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_200_OK,
        )


class SessaoFormativaCommandViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [HasAnySiaRole]
    read_roles = FORMATION_HISTORY_ROLES
    write_roles = FORMATION_MANAGEMENT_ROLES
    action_roles = {
        'palestrantes': FORMATION_HISTORY_ROLES,
        'alterar_tema': FORMATION_MANAGEMENT_ROLES,
        'cancelar': FORMATION_MANAGEMENT_ROLES,
        'adicionar_palestrante': FORMATION_MANAGEMENT_ROLES,
        'remover_palestrante': FORMATION_MANAGEMENT_ROLES,
        'realizar': FORMATION_MANAGEMENT_ROLES,
    }
    pagination_class = None

    def get_queryset(self):
        queryset = (
            SessaoFormativa.objects
            .select_related('encontro')
            .prefetch_related('palestrantes__perfil_alpinista__pessoa')
            .order_by('encontro_id', 'id')
        )
        encontro_id = self.request.query_params.get('encontro')
        if self.action == 'list':
            if not encontro_id:
                raise ValidationError({
                    'encontro': ['Este filtro é obrigatório.'],
                })
            queryset = queryset.filter(encontro_id=encontro_id)
        return queryset

    def get_serializer_class(self):
        return {
            'create': CriacaoSessaoFormativaCommandSerializer,
            'alterar_tema': AlteracaoTemaSessaoCommandSerializer,
            'adicionar_palestrante': PalestranteSessaoCommandSerializer,
            'remover_palestrante': RemocaoPalestranteCommandSerializer,
            'realizar': RealizacaoSessaoCommandSerializer,
        }.get(self.action, SessaoFormativaSerializer)

    def _resposta(self, sessao, *, status_code=status.HTTP_200_OK):
        sessao = self.get_queryset().get(pk=sessao.pk)
        return Response(
            SessaoFormativaSerializer(
                sessao,
                context=self.get_serializer_context(),
            ).data,
            status=status_code,
        )

    def _auditar(self, request, sessao, operacao, *, acao='UPDATE'):
        LogSistema.objects.create(
            usuario=request.user,
            acao=acao,
            modulo='SessaoFormativa',
            descricao=f'SessaoFormativa ID {sessao.pk}: {operacao}.',
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            sessao = serializer.save()
            self._auditar(request, sessao, 'criada', acao='CREATE')
        return self._resposta(sessao, status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='alterar-tema')
    def alterar_tema(self, request, pk=None):
        sessao = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                sessao = formacao_services.alterar_tema_sessao(
                    sessao,
                    **serializer.validated_data,
                )
                self._auditar(request, sessao, 'tema alterado')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(sessao)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        sessao = self.get_object()
        try:
            with transaction.atomic():
                sessao = formacao_services.cancelar_sessao_formativa(sessao)
                self._auditar(request, sessao, 'cancelada')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(sessao)

    @action(detail=True, methods=['get'])
    def palestrantes(self, request, pk=None):
        sessao = self.get_object()
        palestrantes = (
            sessao.palestrantes
            .select_related('perfil_alpinista__pessoa')
            .order_by('id')
        )
        return Response(PalestranteSessaoSerializer(
            palestrantes,
            many=True,
        ).data)

    @action(
        detail=True,
        methods=['post'],
        url_path='adicionar-palestrante',
    )
    def adicionar_palestrante(self, request, pk=None):
        sessao = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                if 'perfil_alpinista' in serializer.validated_data:
                    palestrante = (
                        formacao_services.adicionar_palestrante_alpinista(
                            sessao,
                            serializer.validated_data['perfil_alpinista'],
                        )
                    )
                else:
                    palestrante = (
                        formacao_services.adicionar_palestrante_externo(
                            sessao,
                            nome_externo=(
                                serializer.validated_data['nome_externo']
                            ),
                        )
                    )
                self._auditar(request, sessao, 'palestrante adicionado')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return Response(
            PalestranteSessaoSerializer(palestrante).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['post'],
        url_path='remover-palestrante',
    )
    def remover_palestrante(self, request, pk=None):
        sessao = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        palestrante = get_object_or_404(
            PalestranteSessao,
            pk=serializer.validated_data['palestrante_id'],
            sessao_formativa=sessao,
        )
        try:
            with transaction.atomic():
                formacao_services.remover_palestrante(palestrante)
                self._auditar(request, sessao, 'palestrante removido')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def realizar(self, request, pk=None):
        sessao = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resultados = {
            item['palestrante_id']: item['status']
            for item in serializer.validated_data['resultados']
        }
        try:
            with transaction.atomic():
                sessao = formacao_services.registrar_realizacao_sessao(
                    sessao,
                    resultados=resultados,
                )
                self._auditar(request, sessao, 'realizada')
        except django_core_validation_error as error:
            _erro_de_dominio(error)
        return self._resposta(sessao)


class PresencaPreparatoriaCommandViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = PresencaPreparatoria.objects.select_related(
        'reuniao__encontro',
        'trabalho__pessoa',
        'registrada_por',
    )
    serializer_class = PresencaPreparatoriaCommandSerializer
    permission_classes = [CanRegisterPreparatoryAttendance]

    def perform_create(self, serializer):
        reuniao = serializer.validated_data['reuniao']
        self.check_object_permissions(self.request, reuniao)
        with transaction.atomic():
            presenca = serializer.save(registrada_por=self.request.user)
            LogSistema.objects.create(
                usuario=self.request.user,
                acao='CREATE',
                modulo='PresencaPreparatoria',
                descricao=f'PresencaPreparatoria ID {presenca.pk} registrada.',
            )

    @action(detail=True, methods=['patch'], url_path='corrigir')
    def corrigir(self, request, pk=None):
        presenca = self.get_object()
        serializer = CorrecaoPresencaPreparatoriaCommandSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            presenca = corrigir_presenca_preparatoria(
                presenca,
                registrada_por=request.user,
                **serializer.validated_data,
            )
            LogSistema.objects.create(
                usuario=request.user,
                acao='UPDATE',
                modulo='PresencaPreparatoria',
                descricao=f'PresencaPreparatoria ID {presenca.pk} corrigida.',
            )
        return Response(
            self.get_serializer(presenca).data,
            status=status.HTTP_200_OK,
        )


class ParticipacaoEventoViewSet(AuditedCrudViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        ParticipacaoEvento.objects
        .select_related('alpinista', 'evento')
        .order_by('id')
    )
    serializer_class = ParticipacaoEventoSerializer
    permission_classes = [require_sia_roles(*EVENT_MANAGEMENT_ROLES)]
    audit_module = 'ParticipacaoEvento'

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['evento', 'alpinista']


class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [require_sia_roles(*MATERIAL_MANAGEMENT_ROLES)]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome']
    ordering_fields = ['nome', 'quantidade_disponivel']

    def perform_create(self, serializer):
        with transaction.atomic():
            material = serializer.save()
            LogSistema.objects.create(
                usuario=self.request.user,
                acao='CREATE',
                modulo='Material',
                descricao=f'Material {material.pk} criado.',
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            material = serializer.save()
            LogSistema.objects.create(
                usuario=self.request.user,
                acao='UPDATE',
                modulo='Material',
                descricao=f'Material {material.pk} alterado.',
            )

    def destroy(self, request, *args, **kwargs):
        material = self.get_object()
        with transaction.atomic():
            material = Material.objects.select_for_update().get(pk=material.pk)
            if material.entregas.exists():
                raise ValidationError({
                    'material': [
                        'Materiais com entregas registradas não podem ser excluídos.'
                    ]
                })
            material_pk = material.pk
            material.delete()
            LogSistema.objects.create(
                usuario=request.user,
                acao='DELETE',
                modulo='Material',
                descricao=f'Material {material_pk} excluído.',
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class EntregaMaterialViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        EntregaMaterial.objects
        .select_related('material', 'alpinista')
        .all()
    )
    serializer_class = EntregaMaterialSerializer
    permission_classes = [require_sia_roles(*MATERIAL_MANAGEMENT_ROLES)]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['material', 'alpinista']

    def perform_create(self, serializer):
        material_id = serializer.validated_data['material'].pk
        quantidade = serializer.validated_data['quantidade']

        with transaction.atomic():
            material = Material.objects.select_for_update().get(pk=material_id)
            if quantidade > material.quantidade_disponivel:
                raise ValidationError({
                    'quantidade': ['A quantidade solicitada excede o estoque disponível.']
                })

            material.quantidade_disponivel -= quantidade
            material.save(update_fields=['quantidade_disponivel'])
            entrega = serializer.save(material=material)
            LogSistema.objects.create(
                usuario=self.request.user,
                acao='CREATE',
                modulo='EntregaMaterial',
                descricao=(
                    f'Entrega {entrega.pk} registrada para o Material '
                    f'{material.pk} e Alpinista {entrega.alpinista_id}.'
                ),
            )


@api_view(['GET'])
@permission_classes([require_sia_roles(*FICHAS_MANAGEMENT_ROLES)])
def dashboard_stats(request):
    usuario = request.user

    coordenacoes = usuario.groups.values_list('name', flat=True)
    proximos_encontros = Encontro.objects.filter(
        data_referencia__gte=timezone.localdate()
    ).order_by('data_referencia', 'id')[:3]

    dados_resposta = {
        "usuarioLogado": usuario.username,
        "coordenacoes": list(coordenacoes),
        "totalAlpinistas": Alpinista.objects.count(),
        "proximosEncontros": [
            {"nome": encontro.encontro, "data": str(encontro.data_referencia)}
            for encontro in proximos_encontros
        ]
    }

    if 'Diretoria' in coordenacoes:
        dados_resposta['visaoGeral'] = {
            "ativos": Alpinista.objects.filter(status=Alpinista.Status.ATIVO).count(),
            "pendentes": Alpinista.objects.filter(status=Alpinista.Status.PENDENTE).count(),
            "inativos": Alpinista.objects.filter(status=Alpinista.Status.INATIVO).count(),
        }
    if 'Fichas' in coordenacoes:
        dados_resposta['moduloFichas'] = {
            "fichasPendentes": Alpinista.objects.filter(
                status=Alpinista.Status.PENDENTE
            ).count(),
            "alertaFichas": "Existem novos alpinistas aguardando triagem"
        }
    if 'MME' in coordenacoes:
        dados_resposta['moduloMME'] = {
            "numVioleiros": "Número de violeiros"
        }

    return Response(dados_resposta)

class LogSistemaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LogSistema.objects.all()
    serializer_class = LogSistemaSerializer
    permission_classes = [require_sia_roles(*FULL_ADMIN_ROLES)]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['acao', 'modulo', 'usuario']
    search_fields = ['descricao', 'usuario__username']
