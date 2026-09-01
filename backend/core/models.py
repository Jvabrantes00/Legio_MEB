from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

class Alpinista(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'ativo'),
        ('pendente', 'pendente'),
        ('confirmado', 'confirmado'),
        ('inativo', 'inativo'),
    ]

    cpf = models.CharField(default = False, max_length = 14, unique = True, verbose_name = "CPF")
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
    #foto = models.URLField(null = True, blank = True)
    foto = models.ImageField(upload_to='fotos/', null=True, blank=True)

    is_neurodivergente = models.BooleanField(default=False, verbose_name="É neurodivergente?")
    tipo_neurodivergente = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de Neurodivergencia")

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

    ordem = models.IntegerField(default=99, verbose_name="Ordem de exibição")

    class Meta:
        ordering = ['ordem']

    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    
class Encontro(models.Model):
    STATUS_CHOICES = [
        ('em_agendamento', 'Em Agendamento'),
        ('agendado', 'Agendado'),
    ]

    TIPO_ENCONTRO_CHOICES = [
        ('Escalada', 'Escalada'),
        ('AVC', 'AVC'),
        ('Esppa', 'Esppa'),
        ('Acampamento', 'Acampamento'),
    ]


    encontro = models.CharField(max_length=255, help_text = "Ex: Escalada 1 / AVC / Esppa")
    tipo = models.CharField(max_length=20, choices=TIPO_ENCONTRO_CHOICES, default = 'Escalada')
    data_referencia= models.DateField(help_text = "O 1º dia do encontro")
    data_exato = models.CharField(max_length=150, help_text = "Ex: 19, 24, 25, 26 de Julho de XXXX")
    local = models.CharField(max_length=255, default = "Nova Betânia")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default = 'em_agendamento')

    criado_em = models.DateTimeField(auto_now_add=True)

    participantes = models.ManyToManyField(
        'Alpinista',
        through='ParticipacaoEncontro',
        blank=True,
        related_name='encontro_participacao'
    )

    def __str__(self):
        return self.encontro
    
class Evento(models.Model):
    nome = models.CharField(max_length=255)
    data_evento = models.DateField()
    local = models.CharField(max_length=255)

    def __str__(self):
        return self.nome

# Tabelas Intermediárias para relacionamentos Many-to-Many
class ParticipacaoEncontro(models.Model):

    alpinista = models.ForeignKey('Alpinista', on_delete = models.CASCADE, related_name = 'participacoes_encontros')
    encontro = models.ForeignKey('Encontro', on_delete = models.CASCADE, related_name = 'participacoes')

    funcao = models.ForeignKey(FuncaoEncontro, on_delete=models.PROTECT)

    cor_grupo = models.CharField(max_length = 50, null = True, blank = True)

    coordenador = models.BooleanField(default=False, verbose_name="É Coordenador?")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['alpinista', 'encontro'],
                name='unico_alpinista_por_encontro'
            )
        ]

    def __str__(self):
        return f"{self.alpinista.nome} - {self.funcao.nome} no {self.encontro.encontro}"
    
class ParticipacaoEvento(models.Model):
    alpinista = models.ForeignKey(Alpinista, on_delete = models.CASCADE, related_name = 'eventos')
    evento = models.ForeignKey(Evento, on_delete = models.CASCADE, related_name = 'participacoes')
    
    def __str__(self):
        return f"{self.alpinista.nome} - {self.evento.nome}"


@receiver(post_save, sender=ParticipacaoEncontro)
def alpinista_ativo_automatico(sender, instance, created, **kwargs):
    if created:
        alpinista = instance.alpinista
        if alpinista.status != 'Ativo':
            alpinista.status = 'Ativo'
            alpinista.save()
            print(f"Sistema: Status de {alpinista.nome} atualizado para Ativo!")


class LogSistema(models.Model):
    ACOES = [
        ('CREATE', 'Criação'),
        ('UPDATE', 'Atualização'),
        ('DELETE', 'Exclusão'),
        ('LOGIN', 'Acesso'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    acao = models.CharField(max_length=20, choices=ACOES)
    modulo= models.CharField(max_length=50, help_text="Ex: Alpinistas, Encontros, Fichas")
    descricao = models.TextField(help_text="Ex: Atualizou o status do alpinista")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

        def __str__(self):
            nome_usuario = self.usuario.username if self.usuario else "Sistema"
            return f"[{ self.criado_em.strftime('%d/%m/%Y %H:%M')}] { nome_usuario }: {self.descricao}"