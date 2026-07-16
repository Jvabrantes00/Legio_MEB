from rest_framework import serializers
from .models import Alpinista, Encontro, Evento, ParticipacaoEncontro, ParticipacaoEvento

class EncontroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Encontro
        fields = '__all__' #Diz para converter todos os campos do modelo Alpinista em JSON

class EventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evento
        fields = '__all__'

class ParticipacaoEncontroSerializer(serializers.ModelSerializer):
    encontro = EncontroSerializer(read_only=True)
    encontro_id = serializers.PrimaryKeyRelatedField(
        queryset=Encontro.objects.all(), source='encontro', write_only=True
    )

    class Meta:
        model = ParticipacaoEncontro
        fields = ['id', 'alpinista', 'encontro', 'encontro_id', 'funcao', 'corGrupo']

class ParticipacaoEventoSerializer(serializers.ModelSerializer):
    evento = EventoSerializer(read_only=True)
    evento_id = serializers.PrimaryKeyRelatedField(
        queryset=Evento.objects.all(), source='evento', write_only=True
    )

    class Meta:
        model = ParticipacaoEvento
        fields = ['id', 'alpinista', 'evento', 'evento_id']

class AlpinistaSerializer(serializers.ModelSerializer):
    encontros = ParticipacaoEncontroSerializer(many=True, read_only=True)
    eventos = ParticipacaoEventoSerializer(many=True, read_only=True)

    class Meta:
        model = Alpinista
        fields = '__all__' #Diz para converter todos os campos do modelo Alpinista em JSON