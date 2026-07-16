from django.contrib import admin
from .models import Alpinista, Encontro, Evento, ParticipacaoEncontro, ParticipacaoEvento

admin.site.register(Alpinista)
admin.site.register(Encontro)
admin.site.register(Evento)
admin.site.register(ParticipacaoEncontro)
admin.site.register(ParticipacaoEvento)

