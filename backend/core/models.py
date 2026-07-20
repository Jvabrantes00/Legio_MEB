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

class FuncaoEncontro(models.Model):
    TIPO_FUNCAO = [
        ('encontrista', 'Encontrista'),
        ('equipe', 'Equipe de trabalho'),
    ]

    nome = models.CharField(max_length=100, help_text="Ex: Dirigente, Palestrante")
    tipo = models.CharField(max_length=50, choices=TIPO_FUNCAO, default='')
    descricao_faq = models.TextField(
        blank=True,
        help_text="Explicacao do que a equipe faz (usado na tela de FAQ)"
    )

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    
class Encontro(models.Model):
    STATUS_CHOICES = [
        ('em_agendamento', 'Em Agendamento'),
        ('agendado', 'Agendado'),
    ]


    encontro = models.CharField(max_length=255, help_text = "Ex: Escalada 1 / AVC / Esppa")
    data_referencia= models.DateField(help_text = "O 1º dia do encontro")
    data_exato = models.CharField(max_length=150, help_text = "Ex: 19, 24, 25, 26 de Julho de XXXX")
    local = models.CharField(max_length=255, default = "Nova Betânia")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default = 'em_agendamento')

    criado_em = models.DateField(auto_now_add=True)

    participantes = models.ManyToManyField(
        'Alpinista',
        through='ParticipacaoEncontro',
        blank=True,
        related_name='encontro_participacao'
    )

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

    alpinista = models.ForeignKey('Alpinista', on_delete = models.CASCADE, related_name = 'participacoes_encontros')
    encontro = models.ForeignKey('Encontro', on_delete = models.CASCADE, related_name = 'participacoes')

    funcao = models.ForeignKey(FuncaoEncontro, on_delete=models.PROTECT)

    corGrupo = models.CharField(max_length = 50, null = True, blank = True)

    class Meta:
        unique_together = ('alpinista', 'encontro')

    def __str__(self):
        return f"{self.alpinista.nome} - {self.funcao.nome} no {self.encontro.encontro}"
    
class ParticipacaoEvento(models.Model):
    alpinista = models.ForeignKey(Alpinista, on_delete = models.CASCADE, related_name = 'eventos')
    evento = models.ForeignKey(Evento, on_delete = models.CASCADE, related_name = 'participacoes')
    
    def __str__(self):
        return f"{self.alpinista.nome} - {self.evento.nome}"

