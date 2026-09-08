from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

from .models import (
    Alpinista, Encontro, EntregaMaterial, Evento, FotoEncontro,
    FuncaoEncontro, Palestra, ParticipacaoEncontro, ParticipacaoEvento,
    LogSistema, Material,
)
from .serializers import (
    AlpinistaCompletoSerializer, AlpinistaFotoSerializer,
    AlpinistaResumoSerializer,
    AlpinistaMusicaCommandSerializer, HistoricoPalestraSerializer,
    HistoricoVioleiroSerializer,
    EncontroComunicacaoSerializer, EncontroSerializer, EventoSerializer,
    EntregaMaterialSerializer, FotoEncontroSerializer, MaterialSerializer,
    FuncaoEncontroSerializer, ParticipacaoEncontroSerializer, ParticipacaoEventoSerializer,
    LogSistemaSerializer
    )
from .permissions import HasAnySiaRole, require_sia_roles
from .roles import (
    EVENT_MANAGEMENT_ROLES,
    ENCOUNTER_PHOTO_MANAGEMENT_ROLES,
    ENCOUNTER_READ_ROLES,
    FICHAS_MANAGEMENT_ROLES,
    FORMATION_HISTORY_ROLES,
    FULL_ADMIN_ROLES,
    RECOGNIZED_ROLES,
    MUSIC_MANAGEMENT_ROLES,
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
        'musica': MUSIC_MANAGEMENT_ROLES,
        'historico_violeiro': MUSIC_MANAGEMENT_ROLES,
        'historico_palestras': FORMATION_HISTORY_ROLES,
    }

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AlpinistaFilter
    search_fields = ['nome', 'email', 'telefone', 'grupo']
    ordering_fields = ['nome', 'data_nascimento', 'status']

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
                alpinista.foto = None
                alpinista.save(update_fields=['foto'])
                storage.delete(nome_anterior)
                LogSistema.objects.create(
                    usuario=request.user,
                    acao='DELETE',
                    modulo='Alpinista',
                    descricao=f'Foto do Alpinista {alpinista.pk} removida.',
                )
            return Response({'id': alpinista.pk, 'foto': None})

        serializer = self.get_serializer(alpinista, data=request.data)
        serializer.is_valid(raise_exception=True)
        alpinista = serializer.save()
        nome_novo = alpinista.foto.name
        if nome_anterior and nome_anterior != nome_novo:
            storage.delete(nome_anterior)
        LogSistema.objects.create(
            usuario=request.user,
            acao='UPDATE',
            modulo='Alpinista',
            descricao=(
                f'Foto do Alpinista {alpinista.pk} '
                f'{"substituída" if nome_anterior else "adicionada"}.'
            ),
        )
        return Response({
            'id': alpinista.pk,
            'foto': serializer.data['foto'],
        })

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.has_full_profile_access():
            return queryset
        return queryset.only(*SUMMARY_PROFILE_FIELDS)

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

    def perform_create(self, serializer):
        alpinista = serializer.save()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='CREATE',
            modulo='Alpinista',
            descricao=f'Alpinista {alpinista.nome} criado.'
        )
    
    def perform_update(self, serializer):
        alpinista = serializer.save()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='UPDATE',
            modulo='Alpinista',
            descricao=f'Alpinista {alpinista.nome} atualizado.'
        )

    def perform_destroy(self, instance):
        nome_alpinista = instance.nome
        instance.delete()
        LogSistema.objects.create(
            usuario=self.request.user,
            acao='DELETE',
            modulo='Alpinista',
            descricao=f'Alpinista {nome_alpinista} excluído.'
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

    @action(detail=True, methods=['get', 'post'], url_path='fotos')
    def fotos(self, request, pk=None):
        encontro = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(encontro.fotos.all(), many=True)
            return Response(serializer.data)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        foto = serializer.save(encontro=encontro)
        LogSistema.objects.create(
            usuario=request.user,
            acao='CREATE',
            modulo='FotoEncontro',
            descricao=f'Foto {foto.pk} adicionada ao Encontro {encontro.pk}.',
        )
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
            foto.delete()
            storage.delete(nome_anterior)
            LogSistema.objects.create(
                usuario=request.user,
                acao='DELETE',
                modulo='FotoEncontro',
                descricao=f'Foto {foto_pk} removida do Encontro {encontro.pk}.',
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = self.get_serializer(foto, data=request.data)
        serializer.is_valid(raise_exception=True)
        foto = serializer.save()
        if nome_anterior != foto.imagem.name:
            storage.delete(nome_anterior)
        LogSistema.objects.create(
            usuario=request.user,
            acao='UPDATE',
            modulo='FotoEncontro',
            descricao=f'Foto {foto.pk} substituída no Encontro {encontro.pk}.',
        )
        return Response(serializer.data)

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
                funcao, _ = FuncaoEncontro.objects.get_or_create(
                    tipo='encontrista',
                    defaults={'nome': 'Encontrista'}
                )

                sucessos = 0
                for alp_id in alpinistas_ids:
                    alpinista = Alpinista.objects.get(id=alp_id)
                    status_anterior = (alpinista.status or '').lower()

                    ParticipacaoEncontro.objects.get_or_create(
                        encontro=encontro,
                        alpinista=alpinista,
                        funcao=funcao
                    )

                    if status_anterior == Alpinista.Status.PENDENTE:
                        alpinista.status = Alpinista.Status.CONFIRMADO
                        alpinista.save(update_fields=['status'])

                    sucessos += 1
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
        
        sucessos = 0
        for alp_id in alpinistas_ids:
            try:
                alpinista = Alpinista.objects.get(id=alp_id)
                
                participacao = ParticipacaoEncontro.objects.filter(
                    encontro=encontro,
                    alpinista=alpinista,
                    funcao__tipo='encontrista'
                ).first()
                
                if participacao:
                    participacao.delete()
                    
                    if (alpinista.status or '').lower() in {
                        Alpinista.Status.CONFIRMADO,
                        Alpinista.Status.ATIVO,
                    }:
                        alpinista.status = Alpinista.Status.PENDENTE
                        alpinista.save(update_fields=['status'])
                        
                    sucessos += 1
            except Alpinista.DoesNotExist:
                continue

        return Response({"mensagem": f"{sucessos} encontristas removidos com sucesso!"}, status=status.HTTP_200_OK)


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

class FuncaoEncontroViewSet(viewsets.ModelViewSet):
    queryset = FuncaoEncontro.objects.all() 
    serializer_class = FuncaoEncontroSerializer 
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]
    pagination_class = None

class ParticipacaoEncontroViewSet(viewsets.ModelViewSet):
    queryset = ParticipacaoEncontro.objects.select_related('alpinista', 'encontro', 'funcao').all()
    serializer_class = ParticipacaoEncontroSerializer
    permission_classes = [require_sia_roles(*FICHAS_MANAGEMENT_ROLES)]

    pagination_class = None

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['encontro', 'alpinista', 'funcao']  # Permite filtrar por encontro, alpinista e função

class ParticipacaoEventoViewSet(viewsets.ModelViewSet):
    queryset = (
        ParticipacaoEvento.objects
        .select_related('alpinista', 'evento')
        .order_by('id')
    )
    serializer_class = ParticipacaoEventoSerializer
    permission_classes = [require_sia_roles(*EVENT_MANAGEMENT_ROLES)]

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
