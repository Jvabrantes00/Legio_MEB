from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .validators import normalize_cpf, validate_cpf, validate_image_upload_size

class Pessoa(models.Model):
    class EstadoCivil(models.TextChoices):
        SOLTEIRO = 'solteiro', 'Solteiro'
        CASADO = 'casado', 'Casado'
        VIUVO = 'viuvo', 'Viúvo'
        DIVORCIADO = 'divorciado', 'Divorciado'

    nome = models.CharField(max_length=255)
    apelido = models.CharField(max_length=255, blank=True, default='')
    data_nascimento = models.DateField(null=True, blank=True)
    cpf = models.CharField(
        max_length=14,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_cpf],
        verbose_name='CPF',
    )
    email = models.EmailField(null=True, blank=True)
    foto = models.ImageField(
        upload_to='fotos/',
        null=True,
        blank=True,
        validators=[validate_image_upload_size],
    )
    estado_civil = models.CharField(
        max_length=10,
        choices=EstadoCivil.choices,
        null=True,
        blank=True,
    )
    batismo = models.BooleanField(null=True, blank=True)
    primeira_comunhao = models.BooleanField(null=True, blank=True)
    crisma = models.BooleanField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        self.cpf = normalize_cpf(self.cpf)


class RegiaoAdministrativa(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    ativa = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class TelefonePessoa(models.Model):
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='telefones',
    )
    numero = models.CharField(max_length=20)
    whatsapp = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['pessoa', 'numero'],
                name='telefone_unico_por_pessoa',
            )
        ]

    def __str__(self):
        return self.numero


class EnderecoPessoa(models.Model):
    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='endereco',
    )
    cep = models.CharField(max_length=9, blank=True, default='')
    logradouro = models.CharField(max_length=255, blank=True, default='')
    numero = models.CharField(max_length=20, blank=True, default='')
    complemento = models.CharField(max_length=255, blank=True, default='')
    bairro = models.CharField(max_length=100, blank=True, default='')
    cidade = models.CharField(max_length=100, blank=True, default='')
    regiao_administrativa = models.ForeignKey(
        RegiaoAdministrativa,
        on_delete=models.SET_NULL,
        related_name='enderecos',
        null=True,
        blank=True,
    )
    estado = models.CharField(max_length=2, blank=True, default='')

    def __str__(self):
        return self.logradouro or f'Endereço da Pessoa {self.pessoa_id}'


class ResponsavelPessoa(models.Model):
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='responsaveis',
    )
    nome = models.CharField(max_length=255)
    parentesco = models.CharField(max_length=100, blank=True, default='')
    telefone = models.CharField(max_length=20, blank=True, default='')
    whatsapp = models.BooleanField(default=False)
    principal = models.BooleanField(default=False)

    def __str__(self):
        return self.nome


class DadosSaudePessoa(models.Model):
    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='dados_saude',
    )
    alergias = models.TextField(blank=True, default='')
    intolerancias = models.TextField(blank=True, default='')
    restricoes_alimentares = models.TextField(blank=True, default='')
    neurodivergencia = models.TextField(blank=True, default='')
    medicamentos = models.TextField(blank=True, default='')
    condicao_medica = models.TextField(blank=True, default='')
    observacoes = models.TextField(blank=True, default='')


class VinculoConjugal(models.Model):
    pessoa_a = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='vinculos_como_pessoa_a',
    )
    pessoa_b = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='vinculos_como_pessoa_b',
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(pessoa_a=models.F('pessoa_b')),
                name='vinculo_pessoas_distintas',
            ),
            models.CheckConstraint(
                condition=models.Q(pessoa_a__lt=models.F('pessoa_b')),
                name='vinculo_ordem_canonica',
            ),
            models.UniqueConstraint(
                fields=['pessoa_a', 'pessoa_b'],
                name='vinculo_conjugal_unico',
            ),
        ]


class PerfilAlpinista(models.Model):
    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='perfil_alpinista',
    )
    violeiro = models.BooleanField(default=False)
    canta = models.BooleanField(default=False)
    disponivel_mme = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)


class Alpinista(models.Model):
    class Status(models.TextChoices):
        ATIVO = 'ativo', 'ativo'
        PENDENTE = 'pendente', 'pendente'
        CONFIRMADO = 'confirmado', 'confirmado'
        INATIVO = 'inativo', 'inativo'

    cpf = models.CharField(
        max_length=14,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_cpf],
        verbose_name="CPF",
    )
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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    #foto = models.URLField(null = True, blank = True)
    foto = models.ImageField(
        upload_to='fotos/',
        null=True,
        blank=True,
        validators=[validate_image_upload_size],
    )
    batizado = models.BooleanField(null=True, blank=True)
    primeira_comunhao = models.BooleanField(null=True, blank=True)
    crismado = models.BooleanField(null=True, blank=True)
    eh_violeiro = models.BooleanField(default=False)
    canta = models.BooleanField(default=False)

    is_neurodivergente = models.BooleanField(default=False, verbose_name="É neurodivergente?")
    tipo_neurodivergente = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de Neurodivergencia")

    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='alpinista_legado',
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        self.cpf = normalize_cpf(self.cpf)

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
    eh_violeiro = models.BooleanField(default=False)

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


class Palestra(models.Model):
    alpinista = models.ForeignKey(
        Alpinista,
        on_delete=models.CASCADE,
        related_name='palestras',
    )
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.CASCADE,
        related_name='palestras',
    )
    titulo = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['alpinista', 'encontro', 'titulo'],
                name='unica_palestra_por_alpinista_encontro_titulo',
            )
        ]

    def __str__(self):
        return f'{self.titulo} - {self.alpinista.nome} em {self.encontro.encontro}'


class FotoEncontro(models.Model):
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.CASCADE,
        related_name='fotos',
    )
    imagem = models.ImageField(
        upload_to='encontros/',
        validators=[validate_image_upload_size],
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'Foto {self.pk} do Encontro {self.encontro_id}'


class Material(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    quantidade_disponivel = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['nome', 'id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade_disponivel__gte=0),
                name='material_quantidade_nao_negativa',
            )
        ]

    def __str__(self):
        return self.nome


class EntregaMaterial(models.Model):
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='entregas',
    )
    alpinista = models.ForeignKey(
        Alpinista,
        on_delete=models.PROTECT,
        related_name='entregas_materiais',
    )
    quantidade = models.PositiveIntegerField()
    entregue_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-entregue_em', '-id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade__gt=0),
                name='entrega_material_quantidade_positiva',
            )
        ]

    def __str__(self):
        return f'Entrega {self.pk} do Material {self.material_id}'

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
        if alpinista.status != Alpinista.Status.ATIVO:
            alpinista.status = Alpinista.Status.ATIVO
            alpinista.save(update_fields=['status'])


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
