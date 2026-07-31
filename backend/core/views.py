from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Alpinista, Encontro, Evento, ParticipacaoEncontro, ParticipacaoEvento
from .serializers import AlpinistaSerializer, EncontroSerializer, EventoSerializer, ParticipacaoEncontroSerializer, ParticipacaoEventoSerializer
from django.http import JsonResponse
from django.db.models import Count
from datetime import date


class AlpinistaViewSet(viewsets.ModelViewSet):
    queryset = Alpinista.objects.all() #Busca todos os alpinistas no banco de dados
    serializer_class = AlpinistaSerializer #Usa o tradutor para converter os dados do modelo Alpinista em JSON e vice-versa

class EncontroViewSet(viewsets.ModelViewSet):
    queryset = Encontro.objects.all().order_by('-data_referencia') 
    serializer_class = EncontroSerializer
    permission_classes = [IsAuthenticated] #protecao de rota 

class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all() 
    serializer_class = EventoSerializer 

class ParticipacaoEncontroViewSet(viewsets.ModelViewSet):
    queryset = ParticipacaoEncontro.objects.all() 
    serializer_class = ParticipacaoEncontroSerializer 

class ParticipacaoEventoViewSet(viewsets.ModelViewSet):
    queryset = ParticipacaoEvento.objects.all() 
    serializer_class = ParticipacaoEventoSerializer


def dashboard_stats(request):
    # Contar o numero de alpinistas, encontros e eventos
    total_alpinistas = Alpinista.objects.count()
    ativos = Alpinista.objects.filter(status='Ativo').count()
    pendentes = Alpinista.objects.filter(status='Pendente').count()
    inativos = Alpinista.objects.filter(status='Inativo').count()
    proximos_encontros = Encontro.objects.filter(dataFim__gte=date.today()).order_by('dataInicio')[:3]

    lista_encontros = [
        {"nome": e.nome, "data": str(e.dataInicio)} for e in proximos_encontros
    ]


    return JsonResponse({
        "totalAlpinistas": total_alpinistas,
        "ativos": ativos,
        "pendentes": pendentes,
        "inativos": inativos,
        "proximosEncontros": lista_encontros
    })