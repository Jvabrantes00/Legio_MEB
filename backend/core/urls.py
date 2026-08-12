from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView # <-- Importamos as rotas de login
from .views import (
    AlpinistaViewSet, EncontroViewSet, EventoViewSet, 
    FuncaoEncontroViewSet, ParticipacaoEncontroViewSet, ParticipacaoEventoViewSet,
    LogSistemaViewSet
)
from .views import dashboard_stats

# Cria o roteador automativo
router = DefaultRouter()


router.register(r'alpinistas', AlpinistaViewSet)
router.register(r'encontros', EncontroViewSet)
router.register(r'eventos', EventoViewSet)

router.register(r'funcoes', FuncaoEncontroViewSet)
router.register(r'participacoes-encontros', ParticipacaoEncontroViewSet)
router.register(r'participacoes-eventos', ParticipacaoEventoViewSet)
router.register(r'logs', LogSistemaViewSet)

# Exporta as rotas 
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-stats/', dashboard_stats, name='dashboard-stats'),
    
    # --- ROTAS DE AUTENTICAÇÃO ---
    # É aqui que o Next.js vai bater para fazer o login
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)