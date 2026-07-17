from django.db import models

class Alpinista(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'ativo'),
        ('pendente', 'pendente'),
        ('inativo', 'inativo'),
    ]

    nome = models.CharField(max_length = 255)
    dataNascimento = models.DateField(null = True, blank = True)
    endereco = models.CharField(max_length = 255, null = True, blank = True)
    email = models.EmailField(unique = True)
    telefone = models.CharField(max_length = 20)
    nomePai = models.CharField(max_length = 255, null = True, blank = True)
    telefonePai = models.CharField(max_length = 20, null = True, blank = True)
    nomeMae = models.CharField(max_length = 255, null = True, blank = True)
    telefoneMae = models.CharField(max_length = 20, null = True, blank = True)
    restricaoSaude = models.CharField(max_length = 255, null = True, blank = True)
    medicacao = models.CharField(max_length = 255, null = True, blank = True)
    conheciaEscalada = models.CharField(max_length = 100, null = True, blank = True)
    grupo = models.CharField(max_length = 100, null = True, blank = True)
    status = models.CharField(max_length = 20, choices = STATUS_CHOICES, default = 'Pendente')
    foto = models.URLField(null = True, blank = True)

    def __str__(self):
        return self.nome
    
class Encontro(models.Model):
    STATUS_CHOICES = [
        ('em_agendamento', 'Em Agendamento'),
        ('agendado', 'Agendado'),
    ]


    encontro = models.CharField(max_length=255, help_text = "Ex: Escalada 1 / AVC / Esppa")
    data_encontro = models.DateField(help_text = "Data do encontro")
    local = models.CharField(max_length=255, default = "Nova Betânia")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default = 'em_agendamento')

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome
    
class Evento(models.Model):
    nome = models.CharField(max_length=255)
    dataEvento = models.DateField()
    local = models.CharField(max_length=255)

    def __str__(self):
        return self.nome

# Tabelas Intermediárias para relacionamentos Many-to-Many
class ParticipacaoEncontro(models.Model):
    FUNCAO_CHOICES = [
        ('ENCONTRISTA', 'Encontrista'),
        ('EQUIPE', 'Equipe'),
        ('PALESTRANTE', 'Palestrante'),
    ]

    alpinista = models.ForeignKey(Alpinista, on_delete = models.CASCADE, related_name = 'encontros')
    encontro = models.ForeignKey(Encontro, on_delete = models.CASCADE, related_name = 'participacoes')
    funcao = models.CharField(max_length = 50, choices = FUNCAO_CHOICES)
    corGrupo = models.CharField(max_length = 50, null = True, blank = True)

    def __str__(self):
        return f"{self.alpinista.nome} - {self.funcao} no {self.encontro.nome}"
    
class ParticipacaoEvento(models.Model):
    alpinista = models.ForeignKey(Alpinista, on_delete = models.CASCADE, related_name = 'eventos')
    evento = models.ForeignKey(Evento, on_delete = models.CASCADE, related_name = 'participacoes')
    
    def __str__(self):
        return f"{self.alpinista.nome} - {self.evento.nome}"