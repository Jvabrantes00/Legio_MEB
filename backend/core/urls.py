from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView # <-- Importamos as rotas de login
from .views import AlpinistaViewSet, EncontroViewSet, EventoViewSet, ParticipacaoEncontroViewSet, ParticipacaoEventoViewSet
from .views import dashboard_stats

# Cria o roteador automativo
router = DefaultRouter()
router.register(r'alpinistas', AlpinistaViewSet)
router.register(r'encontros', EncontroViewSet)
router.register(r'eventos', EventoViewSet)
router.register(r'vinculos-encontros', ParticipacaoEncontroViewSet)
router.register(r'vinculos-eventos', ParticipacaoEventoViewSet)

# Exporta as rotas 
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-stats/', dashboard_stats, name='dashboard-stats'),
    
    # --- ROTAS DE AUTENTICAÇÃO ---
    # É aqui que o Next.js vai bater para fazer o login
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]