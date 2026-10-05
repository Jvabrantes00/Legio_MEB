from datetime import date
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.reverse import reverse
from .models import (
    Alpinista, ConviteEncontro, Encontro, EntregaMaterial, Evento,
    FotoEncontro, FuncaoEncontro, Inscricao, LogSistema, Material, Palestra,
    ParticipacaoEncontro as ResultadoParticipacaoEncontro, ParticipacaoEvento,
    Pessoa, PresencaPreparatoria, ReuniaoPreparatoriaEncontro,
    TrabalhoEncontro,
    VinculoEncontroLegado as ParticipacaoEncontro,
)
from .services import participacoes as participacao_services
from .services import reunioes_preparatorias as reuniao_services
from .validators import normalize_cpf, validate_image_upload_size
from .roles import recognized_user_roles


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
        participacoes = obj.participacoes_encontros.exclude(funcao__tipo='encontrista')
        return [
            {
                "nome_encontro": p.encontro.encontro,
                "equipe": p.funcao.nome,
                "tipo_encontro": p.encontro.tipo,
                "data": p.encontro.data_referencia.strftime('%d/%m/%Y') if getattr(p.encontro, 'data_referencia', None) else None,
                "cor_grupo": (
                    p.cor_grupo
                    if p.funcao
                    and "coordenador dos dirigentes" in p.funcao.nome.casefold()
                    else None
                )
            } for p in participacoes
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

    class Meta:
        model = ConviteEncontro
        fields = (
            'id',
            'pessoa_id',
            'encontro_id',
            'finalidade',
            'status',
            'inscricao_id',
            'criado_em',
        )
        read_only_fields = ('id', 'status', 'criado_em')

    def create(self, validated_data):
        try:
            return participacao_services.criar_convite(**validated_data)
        except ValidationError as error:
            _erro_de_dominio(error)


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
