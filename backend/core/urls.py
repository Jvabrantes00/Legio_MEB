from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    AlpinistaViewSet, EncontroViewSet, EventoViewSet,
    EntregaMaterialViewSet, FuncaoEncontroViewSet, MaterialViewSet,
    ParticipacaoEncontroViewSet, ParticipacaoEventoViewSet, LogSistemaViewSet,
    InscricaoEncontroCommandViewSet, ConviteEncontroCommandViewSet,
    InscricaoEncontroPublicaAPIView,
    ConviteEncontroPublicoAPIView,
    InscricaoResolucaoCadastralViewSet,
    CampanhaConvitesEncontroViewSet,
    ResultadoParticipacaoCommandViewSet,
    EquipeEncontroViewSet, TrabalhoEncontroCommandViewSet,
    PresencaPreparatoriaCommandViewSet,
    PropostaVioleirosViewSet,
    SessaoFormativaCommandViewSet,
    CalendarioEncontroCommandViewSet,
    AtendimentoPreEncontroListaAPIView,
    AtendimentoPreEncontroBuscaAPIView,
    AtendimentoPreEncontroDetalheAPIView,
    CheckinPreEncontroAPIView,
    RegularizacaoPreEncontroAPIView,
    PagamentoPreEncontroAPIView,
    CuidadosPreEncontroAPIView,
    ConferenciaCuidadoPreEncontroAPIView,
    FotoPreEncontroAPIView,
    DecisaoVagaPreEncontroAPIView,
    CapacidadePreEncontroAPIView,
    CapabilitiesContextoPreEncontroAPIView,
    InscricoesLookupPreEncontroAPIView,
    PessoasLookupPreEncontroAPIView,
    RegularizacaoInscricoesLookupPreEncontroAPIView,
    RegularizacaoPessoasLookupPreEncontroAPIView,
)
from .views import dashboard_stats
from .views import current_user
from .views import catalogo_formacao
from .views import calendario_institucional
from .views import agenda_encontro
from .views import preview_calendario_institucional
from .views import publicacoes_calendario_institucional
from .views import download_publicacao_calendario
from .authentication import SiaTokenRefreshSerializer
from .permissions import IsSiaSuperuser


class SiaTokenRefreshView(TokenRefreshView):
    serializer_class = SiaTokenRefreshSerializer


class SiaApiRootView(DefaultRouter.APIRootView):
    permission_classes = [IsSiaSuperuser]


class SiaRouter(DefaultRouter):
    APIRootView = SiaApiRootView

# Cria o roteador automativo
router = SiaRouter()


router.register(r'alpinistas', AlpinistaViewSet)
router.register(r'encontros', EncontroViewSet)
router.register(r'eventos', EventoViewSet)

router.register(r'funcoes', FuncaoEncontroViewSet)
router.register(r'participacoes-encontros', ParticipacaoEncontroViewSet)
router.register(
    r'inscricoes-encontros',
    InscricaoEncontroCommandViewSet,
    basename='inscricao-encontro',
)
router.register(
    r'resolucoes-inscricoes',
    InscricaoResolucaoCadastralViewSet,
    basename='resolucao-inscricao',
)
router.register(
    r'campanhas-convites-encontros',
    CampanhaConvitesEncontroViewSet,
    basename='campanha-convites-encontro',
)
router.register(
    r'convites-encontros',
    ConviteEncontroCommandViewSet,
    basename='convite-encontro',
)
router.register(
    r'resultados-participacoes-encontros',
    ResultadoParticipacaoCommandViewSet,
    basename='resultado-participacao-encontro',
)
router.register(
    r'equipes-encontros',
    EquipeEncontroViewSet,
    basename='equipe-encontro',
)
router.register(
    r'trabalhos-encontros',
    TrabalhoEncontroCommandViewSet,
    basename='trabalho-encontro',
)
router.register(
    r'presencas-preparatorias',
    PresencaPreparatoriaCommandViewSet,
    basename='presenca-preparatoria',
)
router.register(
    r'sessoes-formativas',
    SessaoFormativaCommandViewSet,
    basename='sessao-formativa',
)
router.register(
    r'propostas-violeiros',
    PropostaVioleirosViewSet,
    basename='proposta-violeiros',
)
router.register(
    r'calendario-institucional/encontros',
    CalendarioEncontroCommandViewSet,
    basename='calendario-encontro-command',
)
router.register(r'participacoes-eventos', ParticipacaoEventoViewSet)
router.register(r'logs', LogSistemaViewSet)
router.register(r'materiais', MaterialViewSet)
router.register(r'entregas-materiais', EntregaMaterialViewSet)

# Exporta as rotas 
urlpatterns = [
    path(
        'encontros/<int:encontro_id>/pre-encontro/lookups/inscricoes/',
        InscricoesLookupPreEncontroAPIView.as_view(),
        name='pre-encontro-lookup-inscricoes',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/lookups/pessoas/',
        PessoasLookupPreEncontroAPIView.as_view(),
        name='pre-encontro-lookup-pessoas',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/regularizacao/inscricoes/',
        RegularizacaoInscricoesLookupPreEncontroAPIView.as_view(),
        name='pre-encontro-regularizacao-lookup-inscricoes',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/regularizacao/pessoas/',
        RegularizacaoPessoasLookupPreEncontroAPIView.as_view(),
        name='pre-encontro-regularizacao-lookup-pessoas',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/capabilities/',
        CapabilitiesContextoPreEncontroAPIView.as_view(),
        name='pre-encontro-capabilities',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/',
        AtendimentoPreEncontroListaAPIView.as_view(),
        name='pre-encontro-atendimentos',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/busca/',
        AtendimentoPreEncontroBuscaAPIView.as_view(),
        name='pre-encontro-atendimentos-busca',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/',
        AtendimentoPreEncontroDetalheAPIView.as_view(),
        name='pre-encontro-atendimento-detalhe',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/check-in/',
        CheckinPreEncontroAPIView.as_view(),
        name='pre-encontro-check-in',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/regularizar/',
        RegularizacaoPreEncontroAPIView.as_view(),
        name='pre-encontro-regularizar',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/pagamento/',
        PagamentoPreEncontroAPIView.as_view(),
        name='pre-encontro-pagamento',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/cuidados/',
        CuidadosPreEncontroAPIView.as_view(),
        name='pre-encontro-cuidados',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/cuidados/conferir/',
        ConferenciaCuidadoPreEncontroAPIView.as_view(),
        name='pre-encontro-cuidados-conferir',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/foto/',
        FotoPreEncontroAPIView.as_view(),
        name='pre-encontro-foto',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/atendimentos/<int:atendimento_id>/decisao-vaga/',
        DecisaoVagaPreEncontroAPIView.as_view(),
        name='pre-encontro-decisao-vaga',
    ),
    path(
        'encontros/<int:encontro_id>/pre-encontro/capacidade/',
        CapacidadePreEncontroAPIView.as_view(),
        name='pre-encontro-capacidade',
    ),
    path(
        'public/convites/',
        ConviteEncontroPublicoAPIView.as_view(),
        name='convite-encontro-publico',
    ),
    path(
        'public/encontros/<uuid:public_id>/inscricao/',
        InscricaoEncontroPublicaAPIView.as_view(),
        name='inscricao-encontro-publica',
    ),
    path(
        'calendario-institucional/publicacoes/<int:publicacao_id>/download/',
        download_publicacao_calendario,
        name='calendario-institucional-publicacao-download',
    ),
    path(
        'calendario-institucional/publicacoes/',
        publicacoes_calendario_institucional,
        name='calendario-institucional-publicacoes',
    ),
    path(
        'calendario-institucional/preview-pdf/',
        preview_calendario_institucional,
        name='calendario-institucional-preview-pdf',
    ),
    path(
        'calendario-institucional/encontros/<int:encontro_id>/agenda/',
        agenda_encontro,
        name='agenda-encontro',
    ),
    path(
        'calendario-institucional/',
        calendario_institucional,
        name='calendario-institucional',
    ),
    path('', include(router.urls)),
    path('dashboard-stats/', dashboard_stats, name='dashboard-stats'),
    path('catalogo-formacao/', catalogo_formacao, name='catalogo-formacao'),
    path('auth/me/', current_user, name='current-user'),
    
    # --- ROTAS DE AUTENTICAÇÃO ---
    # É aqui que o Next.js vai bater para fazer o login
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', SiaTokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
]
