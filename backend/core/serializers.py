from datetime import date
from rest_framework import serializers
from .models import Alpinista, Encontro, Evento, ParticipacaoEncontro, ParticipacaoEvento, FuncaoEncontro, LogSistema

class AlpinistaSerializer(serializers.ModelSerializer):
    idade_atual = serializers.SerializerMethodField()
    encontros_realizados = serializers.SerializerMethodField()
    historico_equipes = serializers.SerializerMethodField()
    historico_eventos = serializers.SerializerMethodField()

    class Meta:
        model = Alpinista
        fields = '__all__' #Diz para converter todos os campos do modelo Alpinista em JSON

    def get_idade_atual(self, obj):
        if obj.dataNascimento:
            hoje = date.today()
            idade = hoje.year - obj.dataNascimento.year - ((hoje.month, hoje.day) < (obj.dataNascimento.month, obj.dataNascimento.day))
            return idade

    def get_encontros_realizados(self, obj):
        participacoes = obj.participacoes_encontros.filter(funcao__tipo='encontrista')
        return [
            {
                "tipo": p.encontro.tipo,
                "nome_encontro": p.encontro.encontro,
                "data": p.encontro.data_referencia.strftime('%d/%m/%Y') if getattr(p.encontro, 'data_referencia', None) else None,
                "cor_grupo": getattr(p, 'corGrupo', None) 
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
                "cor_grupo": getattr(p, 'corGrupo', None) if p.funcao and 'Dirigente' and 'Coordenador dos Dirigentes' in p.funcao.nome.lower() else None
            } for p in participacoes
        ]

        
    def get_historico_eventos(self, obj):
        participacoes = obj.eventos.filter(alpinista=obj)
        return [
            {
                "nome_evento": p.evento.nome if hasattr(p.evento, 'nome') else "Evento",
                "data": p.evento.dataEvento.strftime('%d/%m/%Y') if getattr(p.evento, 'dataEvento', None) else None,
            } for p in participacoes
        ]

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

        if obj.dataEvento < hoje:
            return "Concluído"
        elif obj.dataEvento == hoje:
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
        fields = ['id', 'alpinista', 'alpinista_id', 'encontro', 'encontro_id', 'funcao', 'funcao_id', 'corGrupo']
    
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