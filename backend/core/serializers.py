from datetime import date
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.reverse import reverse
from .models import (
    Alpinista, ConviteEncontro, Encontro, EntregaMaterial, Evento,
    EquipeEncontro,
    FotoEncontro, FuncaoEncontro, Inscricao, LogSistema, Material, Palestra,
    ParticipacaoEncontro as ResultadoParticipacaoEncontro, ParticipacaoEvento,
    PalestranteSessao, PerfilAlpinista, Pessoa, PresencaPreparatoria,
    ItemPropostaVioleiros, PropostaVioleiros,
    ReuniaoPreparatoriaEncontro, RoleEquipeEncontro, SessaoFormativa,
    TrabalhoEncontro,
    VinculoEncontroLegado as ParticipacaoEncontro,
)
from .services import participacoes as participacao_services
from .services import reunioes_preparatorias as reuniao_services
from .services import trabalhos as trabalho_services
from .services import formacoes as formacao_services
from .services import propostas_violeiros as proposta_violeiros_services
from .services.calendario_institucional import MAXIMO_DIAS_INTERVALO
from .services.elegibilidade_trabalho import (
    avaliar_capacidade_equipe,
    avaliar_composicao_estrutural,
)
from .validators import normalize_cpf, validate_image_upload_size
from .roles import recognized_user_roles


class StrictCommandSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        extra_fields = (
            set(data) - set(self.fields)
            if hasattr(data, 'keys')
            else set()
        )
        if extra_fields:
            raise serializers.ValidationError({
                'campos_extras': [
                    f"Campos não permitidos: {', '.join(sorted(extra_fields))}."
                ]
            })
        return super().to_internal_value(data)


def calculate_age(birth_date):
    if birth_date is None:
        return None

    today = timezone.localdate()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


class CurrentUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    superuser = serializers.BooleanField(source='is_superuser', read_only=True)

    def get_roles(self, user):
        return list(recognized_user_roles(user))


class AlpinistaProtectedPhotoMixin:
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['foto'] = None
        if instance.foto:
            representation['foto'] = reverse(
                'alpinista-foto-arquivo',
                kwargs={'pk': instance.pk},
                request=self.context.get('request'),
            )
        return representation


class AlpinistaResumoSerializer(
    AlpinistaProtectedPhotoMixin,
    serializers.ModelSerializer,
):
    idade = serializers.SerializerMethodField()
    whatsapp = serializers.CharField(source='telefone', read_only=True)
    musica = serializers.SerializerMethodField()
    responsaveis = serializers.SerializerMethodField()

    class Meta:
        model = Alpinista
        fields = (
            'id',
            'nome',
            'foto',
            'idade',
            'grupo',
            'whatsapp',
            'batizado',
            'primeira_comunhao',
            'crismado',
            'musica',
            'responsaveis',
        )
        read_only_fields = fields

    def get_idade(self, obj):
        return calculate_age(obj.dataNascimento)

    def get_musica(self, obj):
        return {
            'violeiro': obj.eh_violeiro,
            'canta': obj.canta,
        }

    def get_responsaveis(self, obj):
        responsaveis = []
        for nome, telefone in (
            (obj.nomePai, obj.telefonePai),
            (obj.nomeMae, obj.telefoneMae),
        ):
            if nome or telefone:
                responsaveis.append({'nome': nome, 'telefone': telefone})
        return responsaveis

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        idade = representation['idade']
        if idade is None or idade >= 18:
            representation.pop('responsaveis', None)
        return representation


class AlpinistaMusicaCommandSerializer(serializers.Serializer):
    violeiro = serializers.BooleanField(required=False)
    canta = serializers.BooleanField(required=False)

    def validate(self, attrs):
        extra_fields = set(self.initial_data) - set(self.fields)
        if extra_fields:
            raise serializers.ValidationError({
                'campos_extras': [
                    f"Campos não permitidos: {', '.join(sorted(extra_fields))}."
                ]
            })
        if not attrs:
            raise serializers.ValidationError({
                'musica': ['Informe ao menos uma característica musical.']
            })
        return attrs


class AlpinistaFotoSerializer(
    AlpinistaProtectedPhotoMixin,
    serializers.ModelSerializer,
):
    foto = serializers.ImageField(
        required=True,
        allow_null=False,
        validators=[validate_image_upload_size],
    )

    class Meta:
        model = Alpinista
        fields = ('foto',)

    def validate(self, attrs):
        extra_fields = set(self.initial_data) - set(self.fields)
        if extra_fields:
            raise serializers.ValidationError({
                'campos_extras': [
                    f"Campos não permitidos: {', '.join(sorted(extra_fields))}."
                ]
            })
        return attrs


class HistoricoVioleiroSerializer(serializers.ModelSerializer):
    nome_encontro = serializers.CharField(source='encontro.encontro')
    tipo_encontro = serializers.CharField(source='encontro.tipo')
    data_encontro = serializers.DateField(source='encontro.data_referencia')
    funcao = serializers.CharField(source='funcao.nome')

    class Meta:
        model = ParticipacaoEncontro
        fields = (
            'encontro_id',
            'nome_encontro',
            'tipo_encontro',
            'data_encontro',
            'funcao',
        )
        read_only_fields = fields


class HistoricoPalestraSerializer(serializers.ModelSerializer):
    nome_encontro = serializers.CharField(source='encontro.encontro')
    tipo_encontro = serializers.CharField(source='encontro.tipo')
    data_encontro = serializers.DateField(source='encontro.data_referencia')

    class Meta:
        model = Palestra
        fields = (
            'encontro_id',
            'nome_encontro',
            'tipo_encontro',
            'data_encontro',
            'titulo',
        )
        read_only_fields = fields


class TemaFormativoSerializer(serializers.Serializer):
    tema_codigo = serializers.CharField(source='codigo', read_only=True)
    titulo = serializers.CharField(read_only=True)
    tipo = serializers.CharField(source='tipo_conteudo', read_only=True)
    ordem = serializers.IntegerField(read_only=True)
    bloco = serializers.CharField(read_only=True)


class PalestranteSessaoSerializer(serializers.ModelSerializer):
    perfil_alpinista_id = serializers.IntegerField(read_only=True)
    nome_alpinista = serializers.CharField(
        source='perfil_alpinista.pessoa.nome',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = PalestranteSessao
        fields = (
            'id',
            'perfil_alpinista_id',
            'nome_alpinista',
            'nome_externo',
            'status',
            'ministrou_em',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = fields


class SessaoFormativaSerializer(serializers.ModelSerializer):
    encontro_id = serializers.IntegerField(read_only=True)
    palestrantes = PalestranteSessaoSerializer(many=True, read_only=True)

    class Meta:
        model = SessaoFormativa
        fields = (
            'id',
            'encontro_id',
            'tema_codigo',
            'titulo_snapshot',
            'tipo_conteudo',
            'status',
            'realizada_em',
            'palestrantes',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = fields


class CriacaoSessaoFormativaCommandSerializer(serializers.Serializer):
    encontro_id = serializers.PrimaryKeyRelatedField(
        source='encontro',
        queryset=Encontro.objects.all(),
    )
    tema_codigo = serializers.SlugField(max_length=100)

    def create(self, validated_data):
        try:
            return formacao_services.criar_sessao_formativa(**validated_data)
        except ValidationError as error:
            _erro_de_dominio(error)


class AlteracaoTemaSessaoCommandSerializer(serializers.Serializer):
    tema_codigo = serializers.SlugField(max_length=100)


class PalestranteSessaoCommandSerializer(serializers.Serializer):
    perfil_alpinista_id = serializers.PrimaryKeyRelatedField(
        source='perfil_alpinista',
        queryset=PerfilAlpinista.objects.all(),
        required=False,
        allow_null=True,
    )
    nome_externo = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=False,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        perfil = attrs.get('perfil_alpinista')
        nome_externo = attrs.get('nome_externo')
        if (perfil is None) == (nome_externo is None):
            raise serializers.ValidationError(
                'Informe exatamente um Alpinista ou nome externo.'
            )
        return attrs


class RemocaoPalestranteCommandSerializer(serializers.Serializer):
    palestrante_id = serializers.IntegerField(min_value=1)


class ResultadoPalestranteCommandSerializer(serializers.Serializer):
    palestrante_id = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=(
        PalestranteSessao.Status.MINISTROU,
        PalestranteSessao.Status.NAO_MINISTROU,
    ))


class RealizacaoSessaoCommandSerializer(serializers.Serializer):
    resultados = ResultadoPalestranteCommandSerializer(
        many=True,
        allow_empty=False,
    )

    def validate_resultados(self, resultados):
        ids = [item['palestrante_id'] for item in resultados]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                'Cada palestrante deve possuir somente um resultado.'
            )
        return resultados


class HistoricoFormativoSerializer(serializers.ModelSerializer):
    palestrante_id = serializers.IntegerField(
        source='perfil_alpinista_id',
        read_only=True,
    )
    palestrante_nome = serializers.CharField(
        source='perfil_alpinista.pessoa.nome',
        read_only=True,
    )
    encontro_id = serializers.IntegerField(
        source='sessao_formativa.encontro_id',
        read_only=True,
    )
    nome_encontro = serializers.CharField(
        source='sessao_formativa.encontro.encontro',
        read_only=True,
    )
    tipo_encontro = serializers.CharField(
        source='sessao_formativa.encontro.tipo',
        read_only=True,
    )
    data_encontro = serializers.DateField(
        source='sessao_formativa.encontro.data_referencia',
        read_only=True,
    )
    tema_codigo = serializers.CharField(
        source='sessao_formativa.tema_codigo',
        read_only=True,
    )
    titulo = serializers.CharField(
        source='sessao_formativa.titulo_snapshot',
        read_only=True,
    )
    tipo_conteudo = serializers.CharField(
        source='sessao_formativa.tipo_conteudo',
        read_only=True,
    )

    class Meta:
        model = PalestranteSessao
        fields = (
            'palestrante_id',
            'palestrante_nome',
            'encontro_id',
            'nome_encontro',
            'tipo_encontro',
            'data_encontro',
            'tema_codigo',
            'titulo',
            'tipo_conteudo',
            'ministrou_em',
        )
        read_only_fields = fields


class AlpinistaCompletoSerializer(
    AlpinistaProtectedPhotoMixin,
    serializers.ModelSerializer,
):
    cpf = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=14,
    )
    idade_atual = serializers.SerializerMethodField()
    encontros_realizados = serializers.SerializerMethodField()
    historico_equipes = serializers.SerializerMethodField()
    historico_eventos = serializers.SerializerMethodField()

    class Meta:
        model = Alpinista
        fields = (
            'id',
            'cpf',
            'nome',
            'dataNascimento',
            'endereco',
            'email',
            'telefone',
            'nomePai',
            'telefonePai',
            'nomeMae',
            'telefoneMae',
            'restricaoSaude',
            'medicacao',
            'conheciaEscalada',
            'grupo',
            'status',
            'foto',
            'batizado',
            'primeira_comunhao',
            'crismado',
            'eh_violeiro',
            'canta',
            'is_neurodivergente',
            'tipo_neurodivergente',
            'idade_atual',
            'encontros_realizados',
            'historico_equipes',
            'historico_eventos',
        )
        read_only_fields = (
            'id',
            'idade_atual',
            'encontros_realizados',
            'historico_equipes',
            'historico_eventos',
        )

    def validate(self, attrs):
        if 'cpf' not in attrs:
            return attrs

        try:
            cpf = normalize_cpf(attrs['cpf'])
        except ValidationError as error:
            raise serializers.ValidationError({'cpf': error.messages}) from error

        if cpf is not None:
            formatted_cpf = f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'
            matches = Alpinista.objects.filter(cpf__in=(cpf, formatted_cpf))
            if self.instance is not None:
                matches = matches.exclude(pk=self.instance.pk)
            if matches.exists():
                raise serializers.ValidationError({'cpf': ['Este CPF já está cadastrado.']})

        attrs['cpf'] = cpf
        return attrs

    def get_idade_atual(self, obj):
        return calculate_age(obj.dataNascimento)

    def get_encontros_realizados(self, obj):
        participacoes = obj.participacoes_encontros.filter(funcao__tipo='encontrista')
        return [
            {
                "tipo": p.encontro.tipo,
                "nome_encontro": p.encontro.encontro,
                "data": p.encontro.data_referencia.strftime('%d/%m/%Y') if getattr(p.encontro, 'data_referencia', None) else None,
                "cor_grupo": p.cor_grupo
            } for p in participacoes
        ]
    
    def get_historico_equipes(self, obj):
        if obj.pessoa_id is None:
            return []
        trabalhos = (
            TrabalhoEncontro.objects
            .filter(
                pessoa_id=obj.pessoa_id,
                status=TrabalhoEncontro.Status.TRABALHOU,
            )
            .select_related(
                'encontro',
                'role_equipe__equipe_encontro',
            )
            .order_by('-encontro__data_referencia', '-id')
        )
        return [
            {
                'nome_encontro': trabalho.encontro.encontro,
                'equipe': trabalho.role_equipe.equipe_encontro.nome,
                'tipo_encontro': trabalho.encontro.tipo,
                'data': (
                    trabalho.encontro.data_referencia.strftime('%d/%m/%Y')
                    if trabalho.encontro.data_referencia
                    else None
                ),
                'cor_grupo': None,
            }
            for trabalho in trabalhos
        ]

        
    def get_historico_eventos(self, obj):
        participacoes = obj.eventos.filter(alpinista=obj)
        return [
            {
                "nome_evento": p.evento.nome if hasattr(p.evento, 'nome') else "Evento",
                "data": p.evento.data_evento.strftime('%d/%m/%Y') if p.evento.data_evento else None,
            } for p in participacoes
        ]


# Nome mantido como alias para compatibilidade com imports existentes.
AlpinistaSerializer = AlpinistaCompletoSerializer

class EncontroSerializer(serializers.ModelSerializer):
    status_encontro = serializers.SerializerMethodField()
    status = serializers.ChoiceField(
        required=False,
        choices=(
            Encontro.Status.EM_AGENDAMENTO,
            Encontro.Status.AGENDADO,
        )
    )

    class Meta:
        model = Encontro
        fields = (
            'id',
            'status_encontro',
            'encontro',
            'tipo',
            'data_referencia',
            'data_exato',
            'local',
            'status',
            'criado_em',
            'participantes',
        )
        read_only_fields = (
            'id',
            'status_encontro',
            'criado_em',
            'participantes',
        )
    
    def get_status_encontro(self, obj):
        hoje = date.today()

        if obj.data_referencia < hoje:
            return "Concluído"
        else:
            return "Em Breve"


class EncontroComunicacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Encontro
        fields = ('id', 'encontro', 'tipo', 'data_referencia')
        read_only_fields = fields


class PeriodoCalendarioQuerySerializer(StrictCommandSerializer):
    inicio = serializers.DateField(required=True)
    fim = serializers.DateField(required=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        inicio = attrs['inicio']
        fim = attrs['fim']
        if inicio > fim:
            raise serializers.ValidationError({
                'periodo': [
                    'A data inicial não pode ser posterior à data final.'
                ]
            })
        if (fim - inicio).days >= MAXIMO_DIAS_INTERVALO:
            raise serializers.ValidationError({
                'periodo': [
                    'O intervalo não pode ultrapassar um ano civil completo.'
                ]
            })
        return attrs


class PreviewCalendarioQuerySerializer(StrictCommandSerializer):
    escopo = serializers.ChoiceField(choices=('PUBLICO', 'INTERNO'))
    periodo = serializers.ChoiceField(choices=('MENSAL', 'ANUAL'))
    ano = serializers.IntegerField(min_value=2000, max_value=9999)
    mes = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
    )
    modelo_anual = serializers.ChoiceField(
        choices=('A', 'B'),
        required=False,
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs['periodo'] == 'MENSAL':
            if 'mes' not in attrs:
                raise serializers.ValidationError({
                    'mes': ['O preview mensal exige o mês.'],
                })
            if 'modelo_anual' in attrs:
                raise serializers.ValidationError({
                    'modelo_anual': [
                        'O modelo anual não se aplica ao preview mensal.'
                    ],
                })
        else:
            if 'mes' in attrs:
                raise serializers.ValidationError({
                    'mes': ['O preview anual não aceita mês.'],
                })
            if 'modelo_anual' not in attrs:
                raise serializers.ValidationError({
                    'modelo_anual': ['O preview anual exige o Modelo A ou B.'],
                })
        return attrs


class ConflitoCalendarioSerializer(serializers.Serializer):
    data = serializers.DateField(read_only=True)
    encontro_ids = serializers.ListField(
        child=serializers.IntegerField(),
        read_only=True,
    )
    quantidade = serializers.IntegerField(read_only=True)


class DiaCalendarioSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True, allow_null=True)
    data = serializers.DateField(read_only=True)
    ordem = serializers.IntegerField(read_only=True)
    rotulo = serializers.CharField(read_only=True)
    conflito = ConflitoCalendarioSerializer(read_only=True, allow_null=True)


class ItemAgendaEncontroSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    origem_id = serializers.IntegerField(read_only=True, allow_null=True)
    origem = serializers.CharField(read_only=True)
    data = serializers.DateField(read_only=True)
    titulo = serializers.CharField(read_only=True)
    subtitulo = serializers.CharField(read_only=True, allow_null=True)
    confirmacao = serializers.CharField(read_only=True, allow_null=True)
    publicavel_externamente = serializers.BooleanField(read_only=True)
    encontro_id = serializers.IntegerField(read_only=True)
    conflito = ConflitoCalendarioSerializer(read_only=True, allow_null=True)


class ItemCalendarioEncontroSerializer(serializers.Serializer):
    categoria = serializers.CharField(read_only=True)
    encontro_id = serializers.IntegerField(read_only=True)
    titulo = serializers.CharField(read_only=True)
    tipo = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    calendario_id = serializers.IntegerField(read_only=True, allow_null=True)
    calendario_versao = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    origem_agenda = serializers.CharField(read_only=True)
    confirmacao = serializers.CharField(read_only=True)
    dias = DiaCalendarioSerializer(many=True, read_only=True)
    agenda = ItemAgendaEncontroSerializer(many=True, read_only=True)
    pode_editar_calendario = serializers.SerializerMethodField()

    def get_pode_editar_calendario(self, obj):
        return self.context.get('pode_gerir_calendario', False)


class PeriodoCalendarioSerializer(serializers.Serializer):
    inicio = serializers.DateField(read_only=True)
    fim = serializers.DateField(read_only=True)


class ConsultaCalendarioInstitucionalSerializer(serializers.Serializer):
    periodo = PeriodoCalendarioSerializer(read_only=True)
    itens = ItemCalendarioEncontroSerializer(many=True, read_only=True)
    conflitos = ConflitoCalendarioSerializer(many=True, read_only=True)
    capabilities = serializers.SerializerMethodField()

    def get_capabilities(self, obj):
        pode_gerir = self.context.get('pode_gerir_calendario', False)
        return {
            'pode_visualizar': True,
            'pode_gerir_calendario': pode_gerir,
            'pode_criar_encontro': pode_gerir,
            'pode_publicar': pode_gerir,
        }


class AgendaEncontroSerializer(serializers.Serializer):
    encontro_id = serializers.IntegerField(read_only=True)
    itens = ItemAgendaEncontroSerializer(many=True, read_only=True)


class DiaCalendarioCommandSerializer(StrictCommandSerializer):
    ordem = serializers.IntegerField(min_value=1)
    data = serializers.DateField()
    rotulo = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=80,
        default='',
    )
    descricao = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        default='',
    )


class CriacaoEncontroCalendarioCommandSerializer(StrictCommandSerializer):
    encontro = serializers.CharField(max_length=255, allow_blank=False)
    tipo = serializers.ChoiceField(choices=Encontro.Tipo.choices)
    local = serializers.CharField(max_length=255, allow_blank=False)
    dias = DiaCalendarioCommandSerializer(many=True, allow_empty=False)
    reunioes = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    avaliacao = serializers.DictField(required=False, allow_null=True)

    def validate_reunioes(self, value):
        serializer = ReuniaoAgendaCriacaoCommandSerializer(data=value, many=True)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def validate_avaliacao(self, value):
        if value is None:
            return None
        serializer = AvaliacaoAgendaCommandSerializer(data=value)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class DadosBasicosCalendarioCommandSerializer(StrictCommandSerializer):
    encontro = serializers.CharField(
        required=False,
        max_length=255,
        allow_blank=False,
    )
    local = serializers.CharField(
        required=False,
        max_length=255,
        allow_blank=False,
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs:
            raise serializers.ValidationError({
                'non_field_errors': [
                    'Informe encontro ou local para alterar.'
                ]
            })
        return attrs


class PlanejamentoCalendarioCommandSerializer(StrictCommandSerializer):
    dias = DiaCalendarioCommandSerializer(many=True, allow_empty=False)


class RotuloDiaCalendarioCommandSerializer(StrictCommandSerializer):
    rotulo = serializers.CharField(allow_blank=True, max_length=80)


class CalendarioSemDadosCommandSerializer(StrictCommandSerializer):
    pass


class ReuniaoAgendaCriacaoCommandSerializer(StrictCommandSerializer):
    ordem = serializers.IntegerField(min_value=1)
    data = serializers.DateField()
    horario = serializers.TimeField()
    local = serializers.CharField(max_length=255, allow_blank=False)
    complemento = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        default='',
    )
    observacoes = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )


class ReuniaoAgendaEdicaoCommandSerializer(StrictCommandSerializer):
    ordem = serializers.IntegerField(required=False, min_value=1)
    data = serializers.DateField(required=False)
    horario = serializers.TimeField(required=False)
    local = serializers.CharField(
        required=False,
        max_length=255,
        allow_blank=False,
    )
    complemento = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )
    observacoes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs:
            raise serializers.ValidationError({
                'non_field_errors': ['Informe ao menos um campo para alterar.']
            })
        return attrs


class AvaliacaoAgendaCommandSerializer(StrictCommandSerializer):
    data = serializers.DateField()


class DiaResultadoComandoCalendarioSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    data = serializers.DateField(read_only=True)
    ordem = serializers.IntegerField(read_only=True)
    rotulo = serializers.CharField(read_only=True)


class ResultadoComandoCalendarioSerializer(serializers.Serializer):
    encontro_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    calendario_id = serializers.IntegerField(read_only=True, allow_null=True)
    calendario_versao = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    confirmacao = serializers.CharField(read_only=True, allow_null=True)
    dias = DiaResultadoComandoCalendarioSerializer(many=True, read_only=True)
    agenda = ItemAgendaEncontroSerializer(many=True, read_only=True)
    avisos_conflito = ConflitoCalendarioSerializer(many=True, read_only=True)


class FotoEncontroSerializer(serializers.ModelSerializer):
    imagem = serializers.ImageField(
        required=True,
        validators=[validate_image_upload_size],
    )

    class Meta:
        model = FotoEncontro
        fields = ('id', 'imagem')
        read_only_fields = ('id',)

    def validate(self, attrs):
        extra_fields = set(self.initial_data) - set(self.fields)
        if extra_fields:
            raise serializers.ValidationError({
                'campos_extras': [
                    f"Campos não permitidos: {', '.join(sorted(extra_fields))}."
                ]
            })
        return attrs

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['imagem'] = reverse(
            'encontro-foto-arquivo',
            kwargs={
                'pk': instance.encontro_id,
                'foto_id': instance.pk,
            },
            request=self.context.get('request'),
        )
        return representation


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ('id', 'nome', 'quantidade_disponivel')
        read_only_fields = ('id',)

    def validate_quantidade_disponivel(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'A quantidade disponível não pode ser negativa.'
            )
        return value


class EntregaMaterialSerializer(serializers.ModelSerializer):
    material_id = serializers.PrimaryKeyRelatedField(
        queryset=Material.objects.all(),
        source='material',
    )
    material_nome = serializers.CharField(source='material.nome', read_only=True)
    alpinista_id = serializers.PrimaryKeyRelatedField(
        queryset=Alpinista.objects.all(),
        source='alpinista',
    )
    alpinista_nome = serializers.CharField(source='alpinista.nome', read_only=True)

    class Meta:
        model = EntregaMaterial
        fields = (
            'id',
            'material_id',
            'material_nome',
            'alpinista_id',
            'alpinista_nome',
            'quantidade',
            'entregue_em',
        )
        read_only_fields = (
            'id',
            'material_nome',
            'alpinista_nome',
            'entregue_em',
        )

    def validate_quantidade(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'A quantidade da entrega deve ser maior que zero.'
            )
        return value

class EventoSerializer(serializers.ModelSerializer):
    status_evento = serializers.SerializerMethodField()
    total_participantes = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = (
            'id',
            'status_evento',
            'total_participantes',
            'nome',
            'data_evento',
            'local',
        )
        read_only_fields = ('id', 'status_evento', 'total_participantes')
    
    def get_status_evento(self, obj):
        hoje = date.today()

        if obj.data_evento < hoje:
            return "Concluído"
        elif obj.data_evento == hoje:
            return "Hoje"
        else:
            return "Em Breve"
    
    def get_total_participantes(self, obj):
        return obj.participacoes.count()

class FuncaoEncontroSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuncaoEncontro
        fields = (
            'id',
            'nome',
            'tipo',
            'descricao_faq',
            'ordem',
            'eh_violeiro',
        )
        read_only_fields = ('id',)

#Relacionamentos Many-to-Many

class AlpinistaParticipacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alpinista
        fields = ('id', 'nome')
        read_only_fields = fields


class ParticipacaoEncontroSerializer(serializers.ModelSerializer):
    alpinista = AlpinistaParticipacaoSerializer(read_only=True)
    encontro = EncontroSerializer(read_only=True)
    funcao = FuncaoEncontroSerializer(read_only=True)

    alpinista_id = serializers.PrimaryKeyRelatedField(
        queryset=Alpinista.objects.all(), source='alpinista', write_only=True
    )
    encontro_id = serializers.PrimaryKeyRelatedField(
        queryset=Encontro.objects.all(), source='encontro', write_only=True
    )
    funcao_id = serializers.PrimaryKeyRelatedField(
        queryset=FuncaoEncontro.objects.all(), source='funcao', write_only=True
    )

    class Meta:
        model = ParticipacaoEncontro
        fields = ['id', 'alpinista', 'alpinista_id', 'encontro', 'encontro_id', 'funcao', 'funcao_id', 'cor_grupo', 'coordenador']


def _erro_de_dominio(error):
    detalhe = getattr(error, 'message_dict', None) or {
        'non_field_errors': error.messages,
    }
    raise serializers.ValidationError(detalhe) from error


def _erro_de_trabalho(error):
    avaliacao = getattr(error, 'avaliacao', None)
    if avaliacao is None:
        _erro_de_dominio(error)
    raise serializers.ValidationError({
        'avaliacao': avaliacao.as_dict(),
        'erros': getattr(error, 'message_dict', {'comando': error.messages}),
    }) from error


def _avaliacao_da_instancia(instance):
    avaliacao = getattr(instance, 'avaliacao_elegibilidade', None)
    return avaliacao.as_dict() if avaliacao is not None else None


class InscricaoEncontroCommandSerializer(serializers.ModelSerializer):
    pessoa_id = serializers.PrimaryKeyRelatedField(
        source='pessoa',
        queryset=Pessoa.objects.all(),
    )

    class Meta:
        model = Inscricao
        fields = (
            'id',
            'pessoa_id',
            'tipo',
            'status',
            'criada_em',
            'cumprida_em',
        )
        read_only_fields = ('id', 'status', 'criada_em', 'cumprida_em')

    def create(self, validated_data):
        try:
            return participacao_services.criar_inscricao(**validated_data)
        except ValidationError as error:
            _erro_de_dominio(error)


class ConviteEncontroCommandSerializer(serializers.ModelSerializer):
    pessoa_id = serializers.PrimaryKeyRelatedField(
        source='pessoa',
        queryset=Pessoa.objects.all(),
    )
    encontro_id = serializers.PrimaryKeyRelatedField(
        source='encontro',
        queryset=Encontro.objects.all(),
    )
    inscricao_id = serializers.PrimaryKeyRelatedField(
        source='inscricao',
        queryset=Inscricao.objects.all(),
        required=False,
        allow_null=True,
    )
    role_trabalho_proposta_id = serializers.PrimaryKeyRelatedField(
        source='role_trabalho_proposta',
        queryset=RoleEquipeEncontro.objects.all(),
        required=False,
        allow_null=True,
    )
    confirmar_avisos = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    avaliacao = serializers.SerializerMethodField()

    class Meta:
        model = ConviteEncontro
        fields = (
            'id',
            'pessoa_id',
            'encontro_id',
            'finalidade',
            'status',
            'inscricao_id',
            'role_trabalho_proposta_id',
            'confirmar_avisos',
            'avaliacao',
            'criado_em',
        )
        read_only_fields = ('id', 'status', 'avaliacao', 'criado_em')

    def get_avaliacao(self, instance):
        return _avaliacao_da_instancia(instance)

    def create(self, validated_data):
        confirmar_avisos = validated_data.pop('confirmar_avisos', False)
        role_proposta = validated_data.pop('role_trabalho_proposta', None)
        try:
            if validated_data['finalidade'] == ConviteEncontro.Finalidade.TRABALHAR:
                if validated_data.get('inscricao') is not None:
                    raise ValidationError(
                        'Convite de trabalho não pode estar ligado a inscrição.'
                    )
                return trabalho_services.criar_convite_trabalho(
                    pessoa=validated_data['pessoa'],
                    encontro=validated_data['encontro'],
                    role_proposta=role_proposta,
                    confirmar_avisos=confirmar_avisos,
                )
            if role_proposta is not None:
                raise ValidationError(
                    'Role proposta pertence somente a convite de trabalho.'
                )
            return participacao_services.criar_convite(**validated_data)
        except ValidationError as error:
            _erro_de_trabalho(error)


class TrabalhoEncontroCommandSerializer(serializers.ModelSerializer):
    convite_id = serializers.PrimaryKeyRelatedField(
        source='convite',
        queryset=ConviteEncontro.objects.all(),
    )
    pessoa_id = serializers.IntegerField(read_only=True)
    encontro_id = serializers.IntegerField(read_only=True)
    role_equipe_id = serializers.IntegerField(read_only=True, allow_null=True)
    confirmar_avisos = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    avaliacao = serializers.SerializerMethodField()

    class Meta:
        model = TrabalhoEncontro
        fields = (
            'id',
            'pessoa_id',
            'encontro_id',
            'convite_id',
            'role_equipe_id',
            'status',
            'resultado_registrado_em',
            'confirmar_avisos',
            'avaliacao',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = (
            'id',
            'pessoa_id',
            'encontro_id',
            'role_equipe_id',
            'status',
            'resultado_registrado_em',
            'avaliacao',
            'criado_em',
            'atualizado_em',
        )

    def get_avaliacao(self, instance):
        return _avaliacao_da_instancia(instance)

    def create(self, validated_data):
        convite = validated_data['convite']
        try:
            return trabalho_services.iniciar_trabalho_confirmado(
                convite,
                confirmar_avisos=validated_data.get('confirmar_avisos', False),
            )
        except ValidationError as error:
            _erro_de_trabalho(error)


class AlocacaoTrabalhoCommandSerializer(serializers.Serializer):
    role_equipe_id = serializers.PrimaryKeyRelatedField(
        source='role_equipe',
        queryset=RoleEquipeEncontro.objects.all(),
    )
    confirmar_avisos = serializers.BooleanField(required=False, default=False)


class ResultadoTrabalhoCommandSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        TrabalhoEncontro.Status.TRABALHOU,
        TrabalhoEncontro.Status.FALTOU,
    ))


class SubstituicaoTrabalhoCommandSerializer(serializers.Serializer):
    trabalho_novo_id = serializers.PrimaryKeyRelatedField(
        source='trabalho_novo',
        queryset=TrabalhoEncontro.objects.all(),
    )
    role_equipe_id = serializers.PrimaryKeyRelatedField(
        source='role_equipe',
        queryset=RoleEquipeEncontro.objects.all(),
    )
    confirmar_avisos = serializers.BooleanField(required=False, default=False)


class RoleEquipeEncontroSerializer(serializers.ModelSerializer):
    trabalhos = serializers.SerializerMethodField()

    class Meta:
        model = RoleEquipeEncontro
        fields = (
            'id',
            'codigo',
            'nome',
            'ordem',
            'quantidade_estrutural',
            'concede_registro_presenca',
            'trabalhos',
        )
        read_only_fields = fields

    def get_trabalhos(self, instance):
        trabalhos = instance.trabalhos.select_related('pessoa').order_by('id')
        return [
            {
                'id': trabalho.pk,
                'pessoa_id': trabalho.pessoa_id,
                'pessoa_nome': trabalho.pessoa.nome,
                'status': trabalho.status,
            }
            for trabalho in trabalhos
        ]


class EquipeEncontroSerializer(serializers.ModelSerializer):
    encontro_id = serializers.IntegerField(read_only=True)
    roles = RoleEquipeEncontroSerializer(many=True, read_only=True)
    capacidade = serializers.SerializerMethodField()
    composicao = serializers.SerializerMethodField()

    class Meta:
        model = EquipeEncontro
        fields = (
            'id',
            'encontro_id',
            'codigo',
            'nome',
            'ordem',
            'capacidade_minima_recomendada',
            'capacidade_maxima_recomendada',
            'capacidade',
            'composicao',
            'roles',
        )
        read_only_fields = fields

    def get_capacidade(self, instance):
        return avaliar_capacidade_equipe(instance).as_dict()

    def get_composicao(self, instance):
        return avaliar_composicao_estrutural(instance).as_dict()


class ItemPropostaVioleirosSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='item.pk', read_only=True)
    perfil_alpinista_id = serializers.IntegerField(
        source='item.perfil_alpinista_id',
        read_only=True,
    )
    pessoa_id = serializers.IntegerField(
        source='item.perfil_alpinista.pessoa_id',
        read_only=True,
    )
    pessoa_nome = serializers.CharField(
        source='item.perfil_alpinista.pessoa.nome',
        read_only=True,
    )
    musica = serializers.SerializerMethodField()
    papel_sugerido = serializers.CharField(
        source='item.papel_sugerido',
        read_only=True,
    )
    posicao = serializers.IntegerField(source='item.posicao', read_only=True)
    vigente = serializers.BooleanField(source='item.vigente', read_only=True)
    retirado_em = serializers.DateTimeField(
        source='item.retirado_em',
        read_only=True,
        allow_null=True,
    )
    situacao = serializers.SerializerMethodField()
    disponivel = serializers.BooleanField(read_only=True)
    avaliacao = serializers.SerializerMethodField()
    criado_em = serializers.DateTimeField(
        source='item.criado_em',
        read_only=True,
    )

    def get_musica(self, resultado):
        perfil = resultado.item.perfil_alpinista
        return {
            'violeiro': perfil.violeiro,
            'canta': perfil.canta,
            'disponivel_mme': perfil.disponivel_mme,
        }

    def get_situacao(self, resultado):
        return resultado.situacao.value

    def get_avaliacao(self, resultado):
        avaliacao = resultado.avaliacao_elegibilidade
        return avaliacao.as_dict() if avaliacao is not None else None


class PropostaVioleirosSerializer(serializers.ModelSerializer):
    encontro_id = serializers.IntegerField(read_only=True)
    total_posicoes = serializers.SerializerMethodField()
    total_disponivel = serializers.SerializerMethodField()
    vagas_disponiveis = serializers.SerializerMethodField()
    completa = serializers.SerializerMethodField()
    precisa_completar = serializers.SerializerMethodField()
    itens = serializers.SerializerMethodField()

    class Meta:
        model = PropostaVioleiros
        fields = (
            'id',
            'encontro_id',
            'nome',
            'status',
            'encerrada_em',
            'total_posicoes',
            'total_disponivel',
            'vagas_disponiveis',
            'completa',
            'precisa_completar',
            'itens',
            'criada_em',
            'atualizada_em',
        )
        read_only_fields = fields

    def _resumo(self, proposta):
        if not hasattr(proposta, '_resumo_violeiros'):
            proposta._resumo_violeiros = (
                proposta_violeiros_services.resumir_proposta_violeiros(
                    proposta
                )
            )
        return proposta._resumo_violeiros

    def get_total_posicoes(self, proposta):
        return self._resumo(proposta).total_posicoes

    def get_total_disponivel(self, proposta):
        return self._resumo(proposta).total_disponivel

    def get_vagas_disponiveis(self, proposta):
        return self._resumo(proposta).vagas_disponiveis

    def get_completa(self, proposta):
        return self._resumo(proposta).completa

    def get_precisa_completar(self, proposta):
        return self._resumo(proposta).precisa_completar

    def get_itens(self, proposta):
        return ItemPropostaVioleirosSerializer(
            self._resumo(proposta).itens,
            many=True,
        ).data


class CriacaoPropostaVioleirosCommandSerializer(StrictCommandSerializer):
    encontro_id = serializers.PrimaryKeyRelatedField(
        source='encontro',
        queryset=Encontro.objects.all(),
    )
    nome = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=100,
    )


class EdicaoPropostaVioleirosCommandSerializer(StrictCommandSerializer):
    nome = serializers.CharField(
        required=True,
        allow_blank=True,
        max_length=100,
    )


class PreenchimentoPropostaVioleirosCommandSerializer(
    StrictCommandSerializer,
):
    perfil_alpinista_id = serializers.PrimaryKeyRelatedField(
        source='perfil_alpinista',
        queryset=PerfilAlpinista.objects.all(),
    )
    papel_sugerido = serializers.ChoiceField(
        choices=ItemPropostaVioleiros.PapelSugerido.choices,
    )
    posicao = serializers.IntegerField(min_value=1, max_value=4)


class ItemPropostaVioleirosCommandSerializer(StrictCommandSerializer):
    item_id = serializers.PrimaryKeyRelatedField(
        source='item',
        queryset=ItemPropostaVioleiros.objects.all(),
    )


class SubstituicaoPropostaVioleirosCommandSerializer(
    ItemPropostaVioleirosCommandSerializer,
):
    perfil_alpinista_id = serializers.PrimaryKeyRelatedField(
        source='perfil_alpinista',
        queryset=PerfilAlpinista.objects.all(),
    )


class AproveitamentoPropostaVioleirosCommandSerializer(
    ItemPropostaVioleirosCommandSerializer,
):
    role_equipe_id = serializers.PrimaryKeyRelatedField(
        source='role_equipe',
        queryset=RoleEquipeEncontro.objects.all(),
        required=False,
        allow_null=True,
    )
    confirmar_avisos = serializers.BooleanField(
        required=False,
        default=False,
    )


class RespostaConviteEncontroCommandSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            ConviteEncontro.Status.CONFIRMADO,
            ConviteEncontro.Status.RECUSADO,
            ConviteEncontro.Status.SEM_RESPOSTA,
        )
    )

    def create(self, validated_data):
        convite = validated_data.pop('convite')
        try:
            return participacao_services.responder_convite(
                convite,
                **validated_data,
            )
        except ValidationError as error:
            _erro_de_dominio(error)


class ResultadoParticipacaoCommandSerializer(serializers.ModelSerializer):
    pessoa_id = serializers.PrimaryKeyRelatedField(
        source='pessoa',
        queryset=Pessoa.objects.all(),
    )
    encontro_id = serializers.PrimaryKeyRelatedField(
        source='encontro',
        queryset=Encontro.objects.all(),
    )
    convite_id = serializers.PrimaryKeyRelatedField(
        source='convite',
        queryset=ConviteEncontro.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ResultadoParticipacaoEncontro
        fields = (
            'id',
            'pessoa_id',
            'encontro_id',
            'convite_id',
            'resultado',
            'tipo_encontro',
            'registrada_em',
        )
        read_only_fields = ('id', 'tipo_encontro', 'registrada_em')

    def create(self, validated_data):
        try:
            return participacao_services.registrar_resultado_participacao(
                **validated_data,
            )
        except ValidationError as error:
            _erro_de_dominio(error)


class PresencaPreparatoriaCommandSerializer(serializers.ModelSerializer):
    reuniao_id = serializers.PrimaryKeyRelatedField(
        source='reuniao',
        queryset=ReuniaoPreparatoriaEncontro.objects.all(),
    )
    trabalho_id = serializers.PrimaryKeyRelatedField(
        source='trabalho',
        queryset=TrabalhoEncontro.objects.all(),
    )
    registrada_por_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PresencaPreparatoria
        fields = (
            'id',
            'reuniao_id',
            'trabalho_id',
            'status',
            'justificativa',
            'registrada_por_id',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = (
            'id',
            'registrada_por_id',
            'criado_em',
            'atualizado_em',
        )

    def create(self, validated_data):
        try:
            return reuniao_services.registrar_presenca_preparatoria(
                **validated_data,
            )
        except ValidationError as error:
            _erro_de_dominio(error)


class CorrecaoPresencaPreparatoriaCommandSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=PresencaPreparatoria.Status.choices,
    )
    justificativa = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )


class ParticipacaoEventoSerializer(serializers.ModelSerializer):
    alpinista_nome = serializers.CharField(source='alpinista.nome', read_only=True)
    evento_nome = serializers.CharField(source='evento.nome', read_only=True)

    class Meta:
        model = ParticipacaoEvento
        fields = ['id', 'alpinista', 'alpinista_nome', 'evento', 'evento_nome']

class LogSistemaSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.username', read_only=True)

    criado_em = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S", read_only=True)
    class Meta:
        model = LogSistema
        fields = ['id', 'usuario', 'usuario_nome', 'acao', 'modulo', 'descricao', 'criado_em']
