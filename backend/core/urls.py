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
    ResultadoParticipacaoCommandViewSet,
    EquipeEncontroViewSet, TrabalhoEncontroCommandViewSet,
    PresencaPreparatoriaCommandViewSet,
    PropostaVioleirosViewSet,
    SessaoFormativaCommandViewSet,
)
from .views import dashboard_stats
from .views import current_user
from .views import catalogo_formacao
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
router.register(r'participacoes-eventos', ParticipacaoEventoViewSet)
router.register(r'logs', LogSistemaViewSet)
router.register(r'materiais', MaterialViewSet)
router.register(r'entregas-materiais', EntregaMaterialViewSet)

# Exporta as rotas 
urlpatterns = [
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
