from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView # <-- Importamos as rotas de login
from .views import (
    AlpinistaViewSet, EncontroViewSet, EventoViewSet, 
    EntregaMaterialViewSet, FuncaoEncontroViewSet, MaterialViewSet,
    ParticipacaoEncontroViewSet, ParticipacaoEventoViewSet, LogSistemaViewSet,
)
from .views import dashboard_stats
from .views import current_user
from .permissions import IsSiaSuperuser


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
router.register(r'participacoes-eventos', ParticipacaoEventoViewSet)
router.register(r'logs', LogSistemaViewSet)
router.register(r'materiais', MaterialViewSet)
router.register(r'entregas-materiais', EntregaMaterialViewSet)

# Exporta as rotas 
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-stats/', dashboard_stats, name='dashboard-stats'),
    path('auth/me/', current_user, name='current-user'),
    
    # --- ROTAS DE AUTENTICAÇÃO ---
    # É aqui que o Next.js vai bater para fazer o login
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
