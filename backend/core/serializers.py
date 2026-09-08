from datetime import date
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers
from .models import Alpinista, Encontro, Evento, Palestra, ParticipacaoEncontro, ParticipacaoEvento, FuncaoEncontro, LogSistema
from .validators import normalize_cpf


def calculate_age(birth_date):
    if birth_date is None:
        return None

    today = timezone.localdate()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


class AlpinistaResumoSerializer(serializers.ModelSerializer):
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


class AlpinistaCompletoSerializer(serializers.ModelSerializer):
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
        fields = '__all__' #Diz para converter todos os campos do modelo Alpinista em JSON

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
                "cor_grupo": p.cor_grupo if p.funcao and 'Dirigente' and "Coordenador dos Dirigentes" in p.funcao.nome.lower() else None
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

    class Meta:
        model = Encontro
        fields = '__all__' #Diz para converter todos os campos do modelo Alpinista em JSON
    
    def get_status_encontro(self, obj):
        hoje = date.today()

        if obj.data_referencia < hoje:
            return "Concluído"
        else:
            return "Em Breve"

class EventoSerializer(serializers.ModelSerializer):
    status_evento = serializers.SerializerMethodField()
    total_participantes = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = '__all__'
    
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
        fields = '__all__'

#Relacionamentos Many-to-Many

class ParticipacaoEncontroSerializer(serializers.ModelSerializer):
    alpinista = AlpinistaSerializer(read_only=True)
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
    
    def validate(self, data):
        alpinista = data.get('alpinista')
        encontro = data.get('encontro')
        funcao = data.get('funcao')

        if funcao and funcao.tipo == 'encontrista':
            ja_fez = ParticipacaoEncontro.objects.filter(
                alpinista=alpinista,
                funcao__tipo='encontrista',
                encontro__tipo=encontro.tipo
            ).exists()

            if ja_fez:
                raise serializers.ValidationError(
                    f"Bloqueado: Este alpinista já participou de um encontro do tipo '{encontro.tipo}' como encontrista."
                )
        return data

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
