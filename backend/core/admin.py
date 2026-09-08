from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User

from .models import Alpinista, Encontro, Evento, ParticipacaoEncontro, ParticipacaoEvento, FuncaoEncontro


class TechnicalAdminSite(admin.AdminSite):
    """Django Admin reserved for the technical superuser boundary."""

    site_header = 'Administração técnica do SIA'

    def has_permission(self, request):
        user = request.user
        return bool(user.is_active and user.is_superuser)


technical_admin_site = TechnicalAdminSite(name='technical_admin')
technical_admin_site.register(User, UserAdmin)
technical_admin_site.register(Group, GroupAdmin)
technical_admin_site.register(Alpinista)
technical_admin_site.register(Encontro)
technical_admin_site.register(Evento)
technical_admin_site.register(ParticipacaoEncontro)
technical_admin_site.register(ParticipacaoEvento)
technical_admin_site.register(FuncaoEncontro)

