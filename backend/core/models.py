from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .formacao_catalogo import TIPO_CONTEUDO_FORMATIVO_CHOICES
from .validators import normalize_cpf, validate_cpf, validate_image_upload_size


def calendario_publicacao_upload_to(instance, filename):
    del filename
    return (
        f'calendarios/divulgacoes/{instance.ano}/'
        f'{instance.periodo.lower()}/{uuid4().hex}.pdf'
    )

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


class VinculoUsuarioPessoa(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name='vinculo_pessoa',
    )
    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='vinculo_usuario',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Usuário {self.usuario_id} — Pessoa {self.pessoa_id}'


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


class Paroquia(models.Model):
    nome = models.CharField(max_length=255)
    regiao_administrativa = models.ForeignKey(
        RegiaoAdministrativa,
        on_delete=models.SET_NULL,
        related_name='paroquias',
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.nome


class Grupo(models.Model):
    nome = models.CharField(max_length=255)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


class ConfiguracaoGrupo(models.Model):
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name='configuracoes',
    )
    vigente_desde = models.DateField()
    vigente_ate = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    paroquia = models.ForeignKey(
        Paroquia,
        on_delete=models.SET_NULL,
        related_name='configuracoes_grupo',
        null=True,
        blank=True,
    )
    local_reuniao = models.CharField(max_length=255, blank=True, default='')
    dia_semana = models.CharField(max_length=20, blank=True, default='')
    horario = models.TimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(vigente_ate__isnull=True)
                    | models.Q(vigente_ate__gte=models.F('vigente_desde'))
                ),
                name='config_grupo_periodo_valido',
            ),
            models.UniqueConstraint(
                fields=['grupo'],
                condition=models.Q(vigente_ate__isnull=True),
                name='config_grupo_atual_unica',
            ),
        ]


class VinculoGrupo(models.Model):
    perfil_alpinista = models.ForeignKey(
        PerfilAlpinista,
        on_delete=models.PROTECT,
        related_name='vinculos_grupo',
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.PROTECT,
        related_name='vinculos',
    )
    inicio = models.DateField()
    fim = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(fim__isnull=True)
                    | models.Q(fim__gte=models.F('inicio'))
                ),
                name='vinculo_grupo_periodo_valido',
            ),
            models.UniqueConstraint(
                fields=['perfil_alpinista', 'grupo'],
                condition=models.Q(fim__isnull=True),
                name='vinculo_grupo_atual_unico',
            ),
        ]


class CoordenacaoGrupo(models.Model):
    class Tipo(models.TextChoices):
        JOVEM = 'jovem', 'Jovem'
        ADULTO = 'adulto', 'Adulto'

    perfil_alpinista = models.ForeignKey(
        PerfilAlpinista,
        on_delete=models.PROTECT,
        related_name='coordenacoes_grupo',
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.PROTECT,
        related_name='coordenacoes',
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    inicio = models.DateField()
    fim = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(fim__isnull=True)
                    | models.Q(fim__gte=models.F('inicio'))
                ),
                name='coordenacao_grupo_periodo_valido',
            ),
            models.UniqueConstraint(
                fields=['perfil_alpinista'],
                condition=models.Q(fim__isnull=True),
                name='coordenacao_grupo_atual_unica',
            ),
        ]


class Frequencia(models.Model):
    perfil_alpinista = models.ForeignKey(
        PerfilAlpinista,
        on_delete=models.PROTECT,
        related_name='frequencias',
    )
    data = models.DateField()
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.SET_NULL,
        related_name='frequencias',
        null=True,
        blank=True,
    )
    registrada_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='frequencias_registradas',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['perfil_alpinista', 'data'],
                name='frequencia_unica_perfil_data',
            )
        ]


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
    class Status(models.TextChoices):
        EM_AGENDAMENTO = 'em_agendamento', 'Em Agendamento'
        AGENDADO = 'agendado', 'Agendado'
        EM_PREPARACAO = 'em_preparacao', 'Em Preparação'
        EM_ANDAMENTO = 'em_andamento', 'Em Andamento'
        FINALIZADO = 'finalizado', 'Finalizado'
        ADIADO = 'adiado', 'Adiado'
        CANCELADO = 'cancelado', 'Cancelado'

    class Tipo(models.TextChoices):
        ESCALADA = 'Escalada', 'Escalada'
        AVC = 'AVC', 'AVC'
        ESPPA = 'Esppa', 'Esppa'
        ACAMPAMENTO = 'Acampamento', 'Acampamento'

    STATUS_CHOICES = Status.choices
    TIPO_ENCONTRO_CHOICES = Tipo.choices

    encontro = models.CharField(
        max_length=255,
        help_text='Ex: Escalada 1 / AVC / Esppa',
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_ENCONTRO_CHOICES,
        default=Tipo.ESCALADA,
    )
    data_referencia = models.DateField(help_text='O 1º dia do encontro')
    data_exato = models.CharField(
        max_length=150,
        help_text='Ex: 19, 24, 25, 26 de Julho de XXXX',
    )
    local = models.CharField(max_length=255, default='Nova Betânia')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=Status.EM_AGENDAMENTO,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    participantes = models.ManyToManyField(
        'Alpinista',
        through='VinculoEncontroLegado',
        blank=True,
        related_name='encontro_participacao',
    )

    def __str__(self):
        return self.encontro


class ConfiguracaoEncontristasEncontro(models.Model):
    public_id = models.UUIDField(
        default=uuid4,
        editable=False,
        unique=True,
    )
    encontro = models.OneToOneField(
        Encontro,
        on_delete=models.PROTECT,
        related_name='configuracao_encontristas',
    )
    capacidade = models.PositiveIntegerField()
    idade_minima = models.PositiveSmallIntegerField()
    idade_maxima = models.PositiveSmallIntegerField()
    inscricoes_abrem_em = models.DateTimeField()
    inscricoes_encerram_em = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacidade__gt=0),
                name='cfg_encontr_cap_positiva',
            ),
            models.CheckConstraint(
                condition=models.Q(idade_minima__lte=models.F('idade_maxima')),
                name='cfg_encontr_idades_coerentes',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    inscricoes_abrem_em__lt=models.F(
                        'inscricoes_encerram_em'
                    )
                ),
                name='cfg_encontr_janela_coerente',
            ),
        ]

    def __str__(self):
        return f'Configuração de encontristas — {self.encontro}'


class InscricaoEncontro(models.Model):
    class Status(models.TextChoices):
        ENVIADA = 'enviada', 'Enviada'
        CANCELADA = 'cancelada', 'Cancelada'

    class Origem(models.TextChoices):
        PUBLICA = 'publica', 'Pública'
        ADMINISTRATIVA = 'administrativa', 'Administrativa'

    identificador = models.UUIDField(
        default=uuid4,
        unique=True,
        editable=False,
    )
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='inscricoes_encontristas',
    )
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='inscricoes_por_encontro',
        null=True,
        blank=True,
    )
    origem = models.CharField(max_length=20, choices=Origem.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ENVIADA,
    )
    enviada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    cancelada_em = models.DateTimeField(null=True, blank=True)
    reativada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['encontro', 'status', 'origem'],
                name='insc_enc_status_origem_idx',
            ),
            models.Index(
                fields=['pessoa', 'encontro'],
                name='insc_pessoa_encontro_idx',
            ),
            models.Index(
                fields=['enviada_em'],
                name='insc_enviada_em_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['encontro', 'pessoa'],
                condition=models.Q(pessoa__isnull=False),
                name='insc_encontro_pessoa_unica',
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=('enviada', 'cancelada')),
                name='insc_encontro_status_valido',
            ),
            models.CheckConstraint(
                condition=models.Q(origem__in=('publica', 'administrativa')),
                name='insc_encontro_origem_valida',
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(status='cancelada')
                    | models.Q(cancelada_em__isnull=False)
                ),
                name='insc_cancelamento_coerente',
            ),
        ]

    def __str__(self):
        return f'Inscrição {self.identificador} — Encontro {self.encontro_id}'


class DadosDeclaradosInscricao(models.Model):
    class Sacramento(models.TextChoices):
        SIM = 'sim', 'Sim'
        NAO = 'nao', 'Não'
        NAO_SEI = 'nao_sei', 'Não sei'
        NAO_INFORMADO = 'nao_informado', 'Não informado'

    class ComoConheceu(models.TextChoices):
        INDICACAO = 'indicacao', 'Indicação de amigo ou familiar'
        PAROQUIA = 'paroquia', 'Paróquia'
        REDES_SOCIAIS = 'redes_sociais', 'Redes sociais'
        JA_CONHECIA = 'ja_conhecia', 'Já conhecia o Movimento Escalada'
        OUTRO = 'outro', 'Outro'

    inscricao = models.OneToOneField(
        InscricaoEncontro,
        on_delete=models.CASCADE,
        related_name='dados_declarados',
    )
    nome_completo = models.CharField(max_length=255)
    apelido = models.CharField(max_length=255, blank=True, default='')
    data_nascimento = models.DateField()
    cpf = models.CharField(
        max_length=14,
        null=True,
        blank=True,
        validators=[validate_cpf],
    )
    email = models.EmailField(blank=True, default='')
    telefone_whatsapp = models.CharField(
        max_length=20,
        blank=True,
        default='',
    )
    cep = models.CharField(max_length=9)
    logradouro = models.CharField(max_length=255)
    numero = models.CharField(max_length=20)
    complemento = models.CharField(max_length=255, blank=True, default='')
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    como_conheceu = models.CharField(
        max_length=30,
        choices=ComoConheceu.choices,
    )
    como_conheceu_outro = models.CharField(
        max_length=255,
        blank=True,
        default='',
    )
    batismo = models.CharField(
        max_length=20,
        choices=Sacramento.choices,
        default=Sacramento.NAO_INFORMADO,
    )
    primeira_comunhao = models.CharField(
        max_length=20,
        choices=Sacramento.choices,
        default=Sacramento.NAO_INFORMADO,
    )
    crisma = models.CharField(
        max_length=20,
        choices=Sacramento.choices,
        default=Sacramento.NAO_INFORMADO,
    )
    snapshot_schema_version = models.PositiveSmallIntegerField(default=1)
    snapshot_atual = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['cpf'], name='dados_insc_cpf_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(email='')
                    | ~models.Q(telefone_whatsapp='')
                ),
                name='dados_insc_contato_presente',
            ),
            models.CheckConstraint(
                condition=models.Q(snapshot_schema_version__gt=0),
                name='dados_insc_schema_positivo',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    como_conheceu__in=(
                        'indicacao',
                        'paroquia',
                        'redes_sociais',
                        'ja_conhecia',
                        'outro',
                    )
                ),
                name='dados_insc_origem_valida',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        batismo__in=(
                            'sim',
                            'nao',
                            'nao_sei',
                            'nao_informado',
                        )
                    )
                    & models.Q(
                        primeira_comunhao__in=(
                            'sim',
                            'nao',
                            'nao_sei',
                            'nao_informado',
                        )
                    )
                    & models.Q(
                        crisma__in=(
                            'sim',
                            'nao',
                            'nao_sei',
                            'nao_informado',
                        )
                    )
                ),
                name='dados_insc_sacramentos_validos',
            ),
        ]

    def __str__(self):
        return f'Dados declarados da inscrição {self.inscricao_id}'


class ResponsavelDeclaradoInscricao(models.Model):
    inscricao = models.OneToOneField(
        InscricaoEncontro,
        on_delete=models.CASCADE,
        related_name='responsavel_declarado',
    )
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(
        max_length=14,
        null=True,
        blank=True,
        validators=[validate_cpf],
    )
    parentesco = models.CharField(max_length=100)
    telefone_whatsapp = models.CharField(max_length=20)
    email = models.EmailField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Responsável declarado da inscrição {self.inscricao_id}'


class DadosCuidadoInscricao(models.Model):
    class RespostaBinaria(models.TextChoices):
        NAO = 'nao', 'Não'
        SIM = 'sim', 'Sim'

    class RespostaApoio(models.TextChoices):
        NAO = 'nao', 'Não'
        SIM = 'sim', 'Sim'
        PREFERE_NAO_INFORMAR = (
            'prefere_nao_informar',
            'Prefere não informar',
        )

    inscricao = models.OneToOneField(
        InscricaoEncontro,
        on_delete=models.CASCADE,
        related_name='dados_cuidado',
    )
    possui_alergias = models.CharField(
        max_length=3,
        choices=RespostaBinaria.choices,
        null=True,
        blank=True,
    )
    alergias = models.TextField(blank=True, default='')
    possui_restricoes_intolerancias = models.CharField(
        max_length=3,
        choices=RespostaBinaria.choices,
        null=True,
        blank=True,
    )
    restricoes_intolerancias = models.TextField(blank=True, default='')
    usa_medicamentos = models.CharField(
        max_length=3,
        choices=RespostaBinaria.choices,
        null=True,
        blank=True,
    )
    medicamentos = models.TextField(blank=True, default='')
    horarios_medicamentos = models.TextField(blank=True, default='')
    observacoes_medicamentos = models.TextField(blank=True, default='')
    neurodivergencia_apoio = models.CharField(
        max_length=25,
        choices=RespostaApoio.choices,
        null=True,
        blank=True,
    )
    neurodivergencia_condicao = models.TextField(blank=True, default='')
    necessidades_apoio = models.TextField(blank=True, default='')
    sensibilidades_desconfortos = models.TextField(blank=True, default='')
    o_que_ajuda = models.TextField(blank=True, default='')
    outras_informacoes = models.TextField(blank=True, default='')
    observacoes = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(possui_alergias__isnull=True)
                        | models.Q(
                            possui_alergias__in=('nao', 'sim')
                        )
                    )
                    & (
                        models.Q(
                            possui_restricoes_intolerancias__isnull=True
                        )
                        | models.Q(
                            possui_restricoes_intolerancias__in=('nao', 'sim')
                        )
                    )
                    & (
                        models.Q(usa_medicamentos__isnull=True)
                        | models.Q(
                            usa_medicamentos__in=('nao', 'sim')
                        )
                    )
                    & (
                        models.Q(neurodivergencia_apoio__isnull=True)
                        | models.Q(
                            neurodivergencia_apoio__in=(
                                'nao',
                                'sim',
                                'prefere_nao_informar',
                            )
                        )
                    )
                ),
                name='dados_cuidado_respostas_validas',
            ),
        ]

    def __str__(self):
        return f'Dados de cuidado da inscrição {self.inscricao_id}'


class DadosEsppaInscricao(models.Model):
    class EstadoCivil(models.TextChoices):
        SOLTEIRO = 'solteiro', 'Solteiro'
        CASADO = 'casado', 'Casado'
        VIUVO = 'viuvo', 'Viúvo'
        DIVORCIADO = 'divorciado', 'Divorciado'

    class RelacaoReferencia(models.TextChoices):
        PAI_MAE = 'pai_mae', 'Pai ou mãe'
        IRMAO_IRMA = 'irmao_irma', 'Irmão ou irmã'
        OUTRO_FAMILIAR = 'outro_familiar', 'Outro familiar'
        AMIGO = 'amigo', 'Amigo(a)'
        OUTRO = 'outro', 'Outro'

    inscricao = models.OneToOneField(
        InscricaoEncontro,
        on_delete=models.CASCADE,
        related_name='dados_esppa',
    )
    estado_civil = models.CharField(
        max_length=20,
        choices=EstadoCivil.choices,
    )
    nome_conjuge = models.CharField(max_length=255, blank=True, default='')
    telefone_conjuge = models.CharField(max_length=20, blank=True, default='')
    nome_referencia = models.CharField(max_length=255, blank=True, default='')
    relacao_referencia = models.CharField(
        max_length=30,
        choices=RelacaoReferencia.choices,
        blank=True,
        default='',
    )
    telefone_referencia = models.CharField(
        max_length=20,
        blank=True,
        default='',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estado_civil__in=(
                        'solteiro',
                        'casado',
                        'viuvo',
                        'divorciado',
                    )
                ),
                name='dados_esppa_estado_civil_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(relacao_referencia='')
                    | models.Q(
                        relacao_referencia__in=(
                            'pai_mae',
                            'irmao_irma',
                            'outro_familiar',
                            'amigo',
                            'outro',
                        )
                    )
                ),
                name='dados_esppa_relacao_valida',
            ),
        ]

    def __str__(self):
        return f'Dados ESPPA da inscrição {self.inscricao_id}'


class CorrespondenciaCadastralInscricao(models.Model):
    class Status(models.TextChoices):
        SUGERIDA = 'sugerida', 'Sugerida'
        REJEITADA = 'rejeitada', 'Rejeitada'
        ACEITA = 'aceita', 'Aceita'

    inscricao = models.ForeignKey(
        InscricaoEncontro,
        on_delete=models.CASCADE,
        related_name='correspondencias_cadastrais',
    )
    pessoa_candidata = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='correspondencias_inscricao',
    )
    origem_sinal = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUGERIDA,
    )
    decidida_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='correspondencias_cadastrais_decididas',
        null=True,
        blank=True,
    )
    decidida_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['inscricao', 'pessoa_candidata'],
                name='corresp_insc_pessoa_unica',
            ),
            models.UniqueConstraint(
                fields=['inscricao'],
                condition=models.Q(status='aceita'),
                name='corresp_insc_aceita_unica',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=('sugerida', 'rejeitada', 'aceita')
                ),
                name='corresp_insc_status_valido',
            ),
            models.CheckConstraint(
                condition=~models.Q(origem_sinal=''),
                name='corresp_insc_origem_nao_vazia',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status='sugerida',
                        decidida_por__isnull=True,
                        decidida_em__isnull=True,
                    )
                    | models.Q(
                        status__in=('rejeitada', 'aceita'),
                        decidida_por__isnull=False,
                        decidida_em__isnull=False,
                    )
                ),
                name='corresp_insc_decisao_coerente',
            ),
        ]

    def __str__(self):
        return (
            f'Correspondência {self.pk or "nova"} — '
            f'inscrição {self.inscricao_id}'
        )


class CalendarioEncontro(models.Model):
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.CASCADE,
        related_name='calendarios',
    )
    versao = models.PositiveIntegerField()
    vigente = models.BooleanField(default=True)
    oficializado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    substituido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(versao__gt=0),
                name='calendario_encontro_versao_positiva',
            ),
            models.UniqueConstraint(
                fields=['encontro', 'versao'],
                name='calendario_encontro_versao_unica',
            ),
            models.UniqueConstraint(
                fields=['encontro'],
                condition=models.Q(vigente=True),
                name='calendario_encontro_vigente_unico',
            ),
        ]


class DiaEncontro(models.Model):
    calendario = models.ForeignKey(
        CalendarioEncontro,
        on_delete=models.CASCADE,
        related_name='dias',
    )
    ordem = models.PositiveIntegerField()
    data = models.DateField()
    rotulo = models.CharField(max_length=80, blank=True, default='')
    descricao = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['data'], name='dia_encontro_data_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ordem__gt=0),
                name='dia_encontro_ordem_positiva',
            ),
            models.UniqueConstraint(
                fields=['calendario', 'ordem'],
                name='dia_encontro_ordem_unica',
            ),
            models.UniqueConstraint(
                fields=['calendario', 'data'],
                name='dia_encontro_data_unica',
            ),
        ]


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


class SessaoFormativa(models.Model):
    class Status(models.TextChoices):
        PLANEJADA = 'planejada', 'Planejada'
        REALIZADA = 'realizada', 'Realizada'
        CANCELADA = 'cancelada', 'Cancelada'

    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='sessoes_formativas',
    )
    tema_codigo = models.SlugField(max_length=100)
    tipo_conteudo = models.CharField(
        max_length=20,
        choices=TIPO_CONTEUDO_FORMATIVO_CHOICES,
    )
    titulo_snapshot = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANEJADA,
    )
    realizada_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['encontro', 'id']
        indexes = [
            models.Index(
                fields=['encontro', 'status'],
                name='sess_form_enc_status_idx',
            ),
            models.Index(
                fields=['tema_codigo', 'status'],
                name='sess_form_tema_status_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    tipo_conteudo__in=('palestra', 'bate_papo'),
                ),
                name='sessao_formativa_tipo_valido',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=('planejada', 'realizada', 'cancelada'),
                ),
                name='sessao_formativa_status_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status='realizada',
                        realizada_em__isnull=False,
                    )
                    | models.Q(
                        status__in=('planejada', 'cancelada'),
                        realizada_em__isnull=True,
                    )
                ),
                name='sessao_formativa_realizacao_coerente',
            ),
        ]

    def __str__(self):
        return f'{self.titulo_snapshot} — {self.encontro.encontro}'


class PalestranteSessao(models.Model):
    class Status(models.TextChoices):
        PREVISTO = 'previsto', 'Previsto'
        MINISTROU = 'ministrou', 'Ministrou'
        NAO_MINISTROU = 'nao_ministrou', 'Não ministrou'

    sessao_formativa = models.ForeignKey(
        SessaoFormativa,
        on_delete=models.PROTECT,
        related_name='palestrantes',
    )
    perfil_alpinista = models.ForeignKey(
        PerfilAlpinista,
        on_delete=models.PROTECT,
        related_name='atuacoes_formativas',
        null=True,
        blank=True,
    )
    nome_externo = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PREVISTO,
    )
    ministrou_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sessao_formativa', 'id']
        indexes = [
            models.Index(
                fields=['sessao_formativa', 'status'],
                name='pal_sessao_status_idx',
            ),
            models.Index(
                fields=['perfil_alpinista', 'status'],
                name='pal_perfil_status_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=('previsto', 'ministrou', 'nao_ministrou'),
                ),
                name='palestrante_sessao_status_valido',
            ),
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(perfil_alpinista__isnull=False)
                        & models.Q(nome_externo='')
                    )
                    | (
                        models.Q(perfil_alpinista__isnull=True)
                        & ~models.Q(nome_externo='')
                    )
                ),
                name='palestrante_sessao_origem_xor',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status='ministrou',
                        ministrou_em__isnull=False,
                    )
                    | models.Q(
                        status__in=('previsto', 'nao_ministrou'),
                        ministrou_em__isnull=True,
                    )
                ),
                name='palestrante_sessao_atuacao_coerente',
            ),
            models.UniqueConstraint(
                fields=['sessao_formativa', 'perfil_alpinista'],
                condition=models.Q(perfil_alpinista__isnull=False),
                name='palestrante_alpinista_unico_sessao',
            ),
        ]

    def __str__(self):
        identidade = (
            f'Perfil {self.perfil_alpinista_id}'
            if self.perfil_alpinista_id is not None
            else self.nome_externo
        )
        return f'{identidade} — Sessão {self.sessao_formativa_id}'


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


# Fundação estrutural de equipes e trabalho em Encontros.
class TemplateEquipeEncontro(models.Model):
    tipo_encontro = models.CharField(
        max_length=20,
        choices=Encontro.Tipo.choices,
    )
    codigo = models.SlugField(max_length=50)
    nome = models.CharField(max_length=100)
    ordem = models.PositiveIntegerField(default=99)
    capacidade_minima_recomendada = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    capacidade_maxima_recomendada = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tipo_encontro', 'ordem', 'id']
        indexes = [
            models.Index(
                fields=['tipo_encontro', 'ativo', 'ordem'],
                name='tmpl_eq_tipo_ativo_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_encontro', 'codigo'],
                name='template_equipe_codigo_unico_tipo',
            ),
            models.CheckConstraint(
                condition=models.Q(tipo_encontro__in=Encontro.Tipo.values),
                name='template_equipe_tipo_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(capacidade_minima_recomendada__isnull=True)
                    | models.Q(capacidade_maxima_recomendada__isnull=True)
                    | models.Q(
                        capacidade_minima_recomendada__lte=models.F(
                            'capacidade_maxima_recomendada'
                        )
                    )
                ),
                name='template_equipe_capacidade_coerente',
            ),
        ]

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_encontro_display()})'


class TemplateRoleEquipe(models.Model):
    template_equipe = models.ForeignKey(
        TemplateEquipeEncontro,
        on_delete=models.PROTECT,
        related_name='roles',
    )
    codigo = models.SlugField(max_length=50)
    nome = models.CharField(max_length=100)
    ordem = models.PositiveIntegerField(default=99)
    quantidade_estrutural = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    concede_registro_presenca = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_equipe', 'ordem', 'id']
        indexes = [
            models.Index(
                fields=['template_equipe', 'ativo', 'ordem'],
                name='tmpl_role_eq_ativo_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['template_equipe', 'codigo'],
                name='template_role_codigo_unico_equipe',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(quantidade_estrutural__isnull=True)
                    | models.Q(quantidade_estrutural__gt=0)
                ),
                name='template_role_quantidade_positiva',
            ),
        ]

    def __str__(self):
        return f'{self.nome} — {self.template_equipe.nome}'


class EquipeEncontro(models.Model):
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='equipes',
    )
    template_origem = models.ForeignKey(
        TemplateEquipeEncontro,
        on_delete=models.PROTECT,
        related_name='snapshots',
    )
    codigo = models.SlugField(max_length=50)
    nome = models.CharField(max_length=100)
    ordem = models.PositiveIntegerField(default=99)
    capacidade_minima_recomendada = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    capacidade_maxima_recomendada = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['encontro', 'ordem', 'id']
        indexes = [
            models.Index(
                fields=['encontro', 'ordem'],
                name='equipe_enc_ordem_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['encontro', 'codigo'],
                name='equipe_encontro_codigo_unico',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(capacidade_minima_recomendada__isnull=True)
                    | models.Q(capacidade_maxima_recomendada__isnull=True)
                    | models.Q(
                        capacidade_minima_recomendada__lte=models.F(
                            'capacidade_maxima_recomendada'
                        )
                    )
                ),
                name='equipe_encontro_capacidade_coerente',
            ),
        ]

    def __str__(self):
        return f'{self.nome} — {self.encontro.encontro}'


class RoleEquipeEncontro(models.Model):
    equipe_encontro = models.ForeignKey(
        EquipeEncontro,
        on_delete=models.PROTECT,
        related_name='roles',
    )
    template_origem = models.ForeignKey(
        TemplateRoleEquipe,
        on_delete=models.PROTECT,
        related_name='snapshots',
    )
    codigo = models.SlugField(max_length=50)
    nome = models.CharField(max_length=100)
    ordem = models.PositiveIntegerField(default=99)
    quantidade_estrutural = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    concede_registro_presenca = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['equipe_encontro', 'ordem', 'id']
        indexes = [
            models.Index(
                fields=['equipe_encontro', 'ordem'],
                name='role_eq_enc_ordem_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['equipe_encontro', 'codigo'],
                name='role_equipe_codigo_unico',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(quantidade_estrutural__isnull=True)
                    | models.Q(quantidade_estrutural__gt=0)
                ),
                name='role_equipe_quantidade_positiva',
            ),
        ]

    def __str__(self):
        return f'{self.nome} — {self.equipe_encontro.nome}'


# Domínio de inscrição, convite e resultado de participação.
class Inscricao(models.Model):
    class Tipo(models.TextChoices):
        ESCALADA = 'Escalada', 'Escalada'
        ESPPA = 'Esppa', 'Esppa'

    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        CUMPRIDA = 'cumprida', 'Cumprida'

    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='inscricoes_encontro',
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    cumprida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['tipo', 'status', 'criada_em'],
                name='inscr_fila_idx',
            ),
            models.Index(
                fields=['pessoa', 'tipo', 'status'],
                name='inscr_pessoa_tipo_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['pessoa', 'tipo'],
                condition=models.Q(status='pendente'),
                name='inscricao_pendente_unica_pessoa_tipo',
            ),
            models.CheckConstraint(
                condition=models.Q(tipo__in=('Escalada', 'Esppa')),
                name='inscricao_tipo_valido',
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=('pendente', 'cumprida')),
                name='inscricao_status_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status='pendente',
                        cumprida_em__isnull=True,
                    )
                    | models.Q(
                        status='cumprida',
                        cumprida_em__isnull=False,
                    )
                ),
                name='inscricao_cumprimento_coerente',
            ),
        ]


class ConviteEncontro(models.Model):
    class Finalidade(models.TextChoices):
        PARTICIPAR = 'participar', 'Participar'
        TRABALHAR = 'trabalhar', 'Trabalhar'

    class Status(models.TextChoices):
        CONVIDADO = 'convidado', 'Convidado'
        CONFIRMADO = 'confirmado', 'Confirmado'
        RECUSADO = 'recusado', 'Recusado'
        SEM_RESPOSTA = 'sem_resposta', 'Sem resposta'

    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='convites_encontro',
    )
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='convites',
    )
    finalidade = models.CharField(
        max_length=20,
        choices=Finalidade.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONVIDADO,
    )
    inscricao = models.ForeignKey(
        Inscricao,
        on_delete=models.PROTECT,
        related_name='convites',
        null=True,
        blank=True,
    )
    role_trabalho_proposta = models.ForeignKey(
        RoleEquipeEncontro,
        on_delete=models.PROTECT,
        related_name='convites_propostos',
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['encontro', 'finalidade', 'status'],
                name='conv_encontro_status_idx',
            ),
            models.Index(
                fields=['pessoa', 'status'],
                name='conv_pessoa_status_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['pessoa', 'encontro', 'finalidade'],
                name='convite_unico_pessoa_encontro_finalidade',
            ),
            models.CheckConstraint(
                condition=models.Q(finalidade__in=('participar', 'trabalhar')),
                name='convite_finalidade_valida',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        'convidado',
                        'confirmado',
                        'recusado',
                        'sem_resposta',
                    )
                ),
                name='convite_status_valido',
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(finalidade='trabalhar')
                    | models.Q(inscricao__isnull=True)
                ),
                name='convite_trabalho_sem_inscricao',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(finalidade='trabalhar')
                    | models.Q(role_trabalho_proposta__isnull=True)
                ),
                name='convite_role_apenas_trabalho',
            ),
        ]


class CampanhaConvitesEncontro(models.Model):
    class Status(models.TextChoices):
        ATIVA = 'ativa', 'Ativa'
        AGUARDANDO_DECISAO = 'aguardando_decisao', 'Aguardando decisão'
        ENCERRADA = 'encerrada', 'Encerrada'

    encontro = models.OneToOneField(
        Encontro,
        on_delete=models.PROTECT,
        related_name='campanha_convites',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVA,
    )
    iniciada_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='campanhas_convites_iniciadas',
    )
    iniciada_em = models.DateTimeField(default=timezone.now)
    prazo_confirmacao = models.DateTimeField()
    encerrada_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['status', 'prazo_confirmacao'],
                name='camp_conv_status_prazo_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=('ativa', 'aguardando_decisao', 'encerrada')
                ),
                name='camp_conv_status_valido',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    prazo_confirmacao__gt=models.F('iniciada_em')
                ),
                name='camp_conv_prazo_coerente',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status='encerrada', encerrada_em__isnull=False)
                    | (
                        ~models.Q(status='encerrada')
                        & models.Q(encerrada_em__isnull=True)
                    )
                ),
                name='camp_conv_encerramento_coerente',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(encerrada_em__isnull=True)
                    | models.Q(encerrada_em__gte=models.F('iniciada_em'))
                ),
                name='camp_conv_datas_coerentes',
            ),
        ]

    def __str__(self):
        return f'Campanha de convites — {self.encontro}'


class RodadaConvitesEncontro(models.Model):
    class Tipo(models.TextChoices):
        INICIAL = 'inicial', 'Inicial'
        REPOSICAO = 'reposicao', 'Reposição'
        PRORROGACAO = 'prorrogacao', 'Prorrogação'

    class Status(models.TextChoices):
        ABERTA = 'aberta', 'Aberta'
        ENCERRADA = 'encerrada', 'Encerrada'

    campanha = models.ForeignKey(
        CampanhaConvitesEncontro,
        on_delete=models.PROTECT,
        related_name='rodadas',
    )
    sequencia = models.PositiveIntegerField()
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABERTA,
    )
    aberta_em = models.DateTimeField(default=timezone.now)
    encerrada_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['campanha_id', 'sequencia']
        indexes = [
            models.Index(
                fields=['campanha', 'status', 'aberta_em'],
                name='rod_conv_camp_status_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['campanha', 'sequencia'],
                name='rod_conv_camp_sequencia_unica',
            ),
            models.CheckConstraint(
                condition=models.Q(sequencia__gt=0),
                name='rod_conv_sequencia_positiva',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    tipo__in=('inicial', 'reposicao', 'prorrogacao')
                ),
                name='rod_conv_tipo_valido',
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=('aberta', 'encerrada')),
                name='rod_conv_status_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status='encerrada', encerrada_em__isnull=False)
                    | (
                        models.Q(status='aberta')
                        & models.Q(encerrada_em__isnull=True)
                    )
                ),
                name='rod_conv_encerramento_coerente',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(encerrada_em__isnull=True)
                    | models.Q(encerrada_em__gte=models.F('aberta_em'))
                ),
                name='rod_conv_datas_coerentes',
            ),
        ]

    def __str__(self):
        return f'Rodada {self.sequencia} — Campanha {self.campanha_id}'


class OportunidadeConviteEncontro(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        CONSUMIDA = 'consumida', 'Consumida'
        INVALIDADA = 'invalidada', 'Invalidada'
        EXPIRADA = 'expirada', 'Expirada'
        SUSPENSA = 'suspensa', 'Suspensa'

    rodada = models.ForeignKey(
        RodadaConvitesEncontro,
        on_delete=models.PROTECT,
        related_name='oportunidades',
    )
    convite = models.ForeignKey(
        ConviteEncontro,
        on_delete=models.PROTECT,
        related_name='oportunidades',
    )
    token_digest = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        validators=[
            RegexValidator(
                regex=r'^[0-9a-f]{64}$',
                message='Use um digest SHA-256 hexadecimal em minúsculas.',
            ),
        ],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    expira_em = models.DateTimeField()
    consumida_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['rodada', 'status'],
                name='op_conv_rod_status_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['rodada', 'convite'],
                name='op_conv_rod_convite_unica',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        'pendente',
                        'consumida',
                        'invalidada',
                        'expirada',
                        'suspensa',
                    )
                ),
                name='op_conv_status_valido',
            ),
            models.CheckConstraint(
                condition=models.Q(token_digest__regex=r'^[0-9a-f]{64}$'),
                name='op_conv_digest_sha256',
            ),
            models.CheckConstraint(
                condition=models.Q(expira_em__gt=models.F('criada_em')),
                name='op_conv_expiracao_coerente',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status='consumida', consumida_em__isnull=False)
                    | (
                        ~models.Q(status='consumida')
                        & models.Q(consumida_em__isnull=True)
                    )
                ),
                name='op_conv_consumo_coerente',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(consumida_em__isnull=True)
                    | models.Q(
                        consumida_em__gte=models.F('criada_em'),
                        consumida_em__lte=models.F('expira_em'),
                    )
                ),
                name='op_conv_consumo_no_prazo',
            ),
        ]

    def __str__(self):
        return f'Oportunidade {self.pk} — Convite {self.convite_id}'


class EntregaConviteEncontro(models.Model):
    class Canal(models.TextChoices):
        EMAIL = 'email', 'E-mail'
        WHATSAPP = 'whatsapp', 'WhatsApp'

    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        ENVIANDO = 'enviando', 'Enviando'
        ENTREGUE = 'entregue', 'Entregue'
        FALHOU = 'falhou', 'Falhou'

    oportunidade = models.ForeignKey(
        OportunidadeConviteEncontro,
        on_delete=models.PROTECT,
        related_name='entregas',
    )
    canal = models.CharField(max_length=20, choices=Canal.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    chave_idempotencia = models.UUIDField(
        default=uuid4,
        unique=True,
        editable=False,
    )
    tentativas = models.PositiveSmallIntegerField(default=0)
    primeira_tentativa_em = models.DateTimeField(null=True, blank=True)
    ultima_tentativa_em = models.DateTimeField(null=True, blank=True)
    entregue_em = models.DateTimeField(null=True, blank=True)
    proxima_tentativa_em = models.DateTimeField(null=True, blank=True)
    codigo_erro = models.CharField(max_length=100, blank=True, default='')
    erro_tecnico = models.CharField(max_length=500, blank=True, default='')
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['oportunidade', 'status'],
                name='ent_conv_op_status_idx',
            ),
            models.Index(
                fields=['status', 'proxima_tentativa_em'],
                name='ent_conv_retry_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['oportunidade', 'canal'],
                name='ent_conv_op_canal_unica',
            ),
            models.CheckConstraint(
                condition=models.Q(canal__in=('email', 'whatsapp')),
                name='ent_conv_canal_valido',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=('pendente', 'enviando', 'entregue', 'falhou')
                ),
                name='ent_conv_status_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        tentativas=0,
                        primeira_tentativa_em__isnull=True,
                        ultima_tentativa_em__isnull=True,
                    )
                    | models.Q(
                        tentativas__gt=0,
                        primeira_tentativa_em__isnull=False,
                        ultima_tentativa_em__isnull=False,
                    )
                ),
                name='ent_conv_tentativas_coerentes',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(ultima_tentativa_em__isnull=True)
                    | models.Q(
                        ultima_tentativa_em__gte=models.F(
                            'primeira_tentativa_em'
                        )
                    )
                ),
                name='ent_conv_tentativas_ordem',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status='entregue',
                        entregue_em__isnull=False,
                        tentativas__gt=0,
                    )
                    | (
                        ~models.Q(status='entregue')
                        & models.Q(entregue_em__isnull=True)
                    )
                ),
                name='ent_conv_entrega_coerente',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(primeira_tentativa_em__isnull=True)
                    | models.Q(
                        primeira_tentativa_em__gte=models.F('criada_em')
                    )
                ),
                name='ent_conv_primeira_tentativa_ordem',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(entregue_em__isnull=True)
                    | models.Q(
                        entregue_em__gte=models.F('primeira_tentativa_em')
                    )
                ),
                name='ent_conv_entrega_ordem',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(proxima_tentativa_em__isnull=True)
                    | models.Q(
                        tentativas__gt=0,
                        ultima_tentativa_em__isnull=False,
                        proxima_tentativa_em__gte=models.F(
                            'ultima_tentativa_em'
                        )
                    )
                ),
                name='ent_conv_retry_ordem',
            ),
        ]

    def __str__(self):
        return f'{self.get_canal_display()} — Oportunidade {self.oportunidade_id}'


class TrabalhoEncontro(models.Model):
    class Status(models.TextChoices):
        AGUARDANDO_ALOCACAO = (
            'aguardando_alocacao',
            'Aguardando alocação',
        )
        ALOCADO = 'alocado', 'Alocado'
        TRABALHOU = 'trabalhou', 'Trabalhou'
        FALTOU = 'faltou', 'Faltou'
        RETIRADO = 'retirado', 'Retirado'

    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='trabalhos_encontro',
    )
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='trabalhos',
    )
    convite = models.OneToOneField(
        ConviteEncontro,
        on_delete=models.PROTECT,
        related_name='trabalho',
    )
    role_equipe = models.ForeignKey(
        RoleEquipeEncontro,
        on_delete=models.PROTECT,
        related_name='trabalhos',
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.AGUARDANDO_ALOCACAO,
    )
    resultado_registrado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['encontro', 'status'],
                name='trab_encontro_status_idx',
            ),
            models.Index(
                fields=['pessoa', 'status'],
                name='trab_pessoa_status_idx',
            ),
            models.Index(
                fields=['role_equipe', 'status'],
                name='trab_role_status_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['pessoa', 'encontro'],
                name='trabalho_unico_pessoa_encontro',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        'aguardando_alocacao',
                        'alocado',
                        'trabalhou',
                        'faltou',
                        'retirado',
                    )
                ),
                name='trabalho_status_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status='aguardando_alocacao',
                        role_equipe__isnull=True,
                    )
                    | models.Q(
                        status__in=('alocado', 'trabalhou', 'faltou'),
                        role_equipe__isnull=False,
                    )
                    | models.Q(status='retirado')
                ),
                name='trabalho_alocacao_coerente',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=('trabalhou', 'faltou'),
                        resultado_registrado_em__isnull=False,
                    )
                    | models.Q(
                        status__in=(
                            'aguardando_alocacao',
                            'alocado',
                            'retirado',
                        ),
                        resultado_registrado_em__isnull=True,
                    )
                ),
                name='trabalho_resultado_coerente',
            ),
        ]

    def __str__(self):
        return f'{self.pessoa.nome} — {self.encontro.encontro}'


# Fundação estrutural de propostas de Violeiros do MME.
class PropostaVioleiros(models.Model):
    class Status(models.TextChoices):
        ABERTA = 'aberta', 'Aberta'
        ENCERRADA = 'encerrada', 'Encerrada'

    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='propostas_violeiros',
    )
    nome = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABERTA,
    )
    encerrada_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['encontro', 'criada_em', 'id']
        indexes = [
            models.Index(
                fields=['encontro', 'status'],
                name='prop_vio_enc_status_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=('aberta', 'encerrada')),
                name='proposta_violeiros_status_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status='aberta', encerrada_em__isnull=True)
                    | models.Q(status='encerrada', encerrada_em__isnull=False)
                ),
                name='proposta_violeiros_encerramento_coerente',
            ),
        ]

    def __str__(self):
        return self.nome or str(self.pk)


class ItemPropostaVioleiros(models.Model):
    class PapelSugerido(models.TextChoices):
        COORDENADOR = 'coordenador', 'Coordenador'
        INTEGRANTE = 'integrante', 'Integrante'

    proposta = models.ForeignKey(
        PropostaVioleiros,
        on_delete=models.PROTECT,
        related_name='itens',
    )
    perfil_alpinista = models.ForeignKey(
        PerfilAlpinista,
        on_delete=models.PROTECT,
        related_name='itens_propostas_violeiros',
    )
    papel_sugerido = models.CharField(
        max_length=20,
        choices=PapelSugerido.choices,
    )
    posicao = models.PositiveSmallIntegerField()
    vigente = models.BooleanField(default=True)
    retirado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            'proposta',
            '-vigente',
            'papel_sugerido',
            'posicao',
            'id',
        ]
        indexes = [
            models.Index(
                fields=['proposta', 'vigente', 'papel_sugerido', 'posicao'],
                name='item_prop_slot_idx',
            ),
            models.Index(
                fields=['perfil_alpinista', 'vigente'],
                name='item_prop_perfil_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    papel_sugerido__in=('coordenador', 'integrante')
                ),
                name='item_proposta_papel_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(papel_sugerido='coordenador', posicao=1)
                    | models.Q(
                        papel_sugerido='integrante',
                        posicao__gte=1,
                        posicao__lte=4,
                    )
                ),
                name='item_proposta_slot_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(vigente=True, retirado_em__isnull=True)
                    | models.Q(vigente=False, retirado_em__isnull=False)
                ),
                name='item_proposta_vigencia_coerente',
            ),
            models.UniqueConstraint(
                fields=['proposta', 'papel_sugerido', 'posicao'],
                condition=models.Q(vigente=True),
                name='item_proposta_slot_vigente_unico',
            ),
            models.UniqueConstraint(
                fields=['proposta', 'perfil_alpinista'],
                condition=models.Q(vigente=True),
                name='item_proposta_perfil_vigente_unico',
            ),
        ]

    def __str__(self):
        return (
            f'{self.get_papel_sugerido_display()} {self.posicao} — '
            f'{self.perfil_alpinista.pessoa.nome}'
        )


class ReuniaoPreparatoriaEncontro(models.Model):
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='reunioes_preparatorias',
    )
    ordem = models.PositiveIntegerField()
    data = models.DateField()
    horario = models.TimeField()
    local = models.CharField(max_length=255)
    complemento = models.CharField(max_length=255, blank=True, default='')
    observacoes = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['encontro', 'ordem', 'id']
        indexes = [
            models.Index(
                fields=['encontro', 'ordem'],
                name='reun_enc_ordem_idx',
            ),
            models.Index(
                fields=['encontro', 'data'],
                name='reun_enc_data_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['encontro', 'ordem'],
                name='reuniao_ordem_unica_encontro',
            ),
            models.CheckConstraint(
                condition=models.Q(ordem__gt=0),
                name='reuniao_ordem_positiva',
            ),
        ]

    def __str__(self):
        return f'{self.encontro.encontro} — reunião {self.ordem}'


class AvaliacaoEncontro(models.Model):
    encontro = models.OneToOneField(
        Encontro,
        on_delete=models.PROTECT,
        related_name='avaliacao_agenda',
    )
    data = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['data', 'id']
        indexes = [
            models.Index(fields=['data'], name='aval_encontro_data_idx'),
        ]

    def __str__(self):
        return f'Avaliação — {self.encontro.encontro}'


class PublicacaoCalendarioInstitucional(models.Model):
    class Escopo(models.TextChoices):
        PUBLICO = 'PUBLICO', 'Público'
        INTERNO = 'INTERNO', 'Interno'

    class Periodo(models.TextChoices):
        MES = 'MENSAL', 'Mês'
        ANO = 'ANUAL', 'Ano'

    class Layout(models.TextChoices):
        MENSAL = 'MENSAL', 'Mensal'
        ANUAL_RESUMIDO = 'ANUAL_RESUMIDO', 'Anual resumido'

    escopo = models.CharField(max_length=10, choices=Escopo.choices)
    periodo = models.CharField(max_length=10, choices=Periodo.choices)
    layout = models.CharField(
        max_length=20,
        choices=Layout.choices,
        default=Layout.MENSAL,
    )
    ano = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField(null=True, blank=True)
    publicado_em = models.DateTimeField(default=timezone.now, editable=False)
    publicado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='publicacoes_calendario_institucional',
    )
    snapshot_schema_version = models.PositiveSmallIntegerField(default=1)
    snapshot = models.JSONField()
    arquivo_pdf = models.FileField(
        upload_to=calendario_publicacao_upload_to,
        max_length=255,
    )
    sha256 = models.CharField(max_length=64)

    class Meta:
        ordering = ['-publicado_em', '-id']
        indexes = [
            models.Index(
                fields=['periodo', 'ano', 'mes', 'publicado_em'],
                name='pub_cal_periodo_idx',
            ),
            models.Index(
                fields=['periodo', 'layout', 'ano', 'mes', 'publicado_em'],
                name='pub_cal_layout_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(escopo__in=['PUBLICO', 'INTERNO']),
                name='pub_cal_escopo_valido',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        periodo='MENSAL',
                        mes__gte=1,
                        mes__lte=12,
                    )
                    | models.Q(periodo='ANUAL', mes__isnull=True)
                ),
                name='pub_cal_periodo_mes_coerente',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(periodo='MENSAL', layout='MENSAL')
                    | models.Q(
                        periodo='ANUAL',
                        layout__in=['MENSAL', 'ANUAL_RESUMIDO'],
                    )
                ),
                name='pub_cal_periodo_layout_valido',
            ),
        ]

    def __str__(self):
        periodo = f'{self.mes:02d}/{self.ano}' if self.mes else str(self.ano)
        return (
            f'{self.get_escopo_display()} '
            f'{self.get_periodo_display()} / {self.get_layout_display()} '
            f'— {periodo}'
        )

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                'Uma publicação do Calendário Institucional é imutável.'
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            'Uma publicação do Calendário Institucional não pode ser removida.'
        )


class PresencaPreparatoria(models.Model):
    class Status(models.TextChoices):
        PRESENTE = 'presente', 'Presente'
        AUSENTE_JUSTIFICADO = (
            'ausente_justificado',
            'Ausente justificado',
        )
        AUSENTE_SEM_JUSTIFICATIVA = (
            'ausente_sem_justificativa',
            'Ausente sem justificativa',
        )

    reuniao = models.ForeignKey(
        ReuniaoPreparatoriaEncontro,
        on_delete=models.PROTECT,
        related_name='presencas',
    )
    trabalho = models.ForeignKey(
        TrabalhoEncontro,
        on_delete=models.PROTECT,
        related_name='presencas_preparatorias',
    )
    status = models.CharField(max_length=30, choices=Status.choices)
    justificativa = models.TextField(blank=True, default='')
    registrada_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='presencas_preparatorias_registradas',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['reuniao', 'trabalho', 'id']
        indexes = [
            models.Index(
                fields=['reuniao', 'status'],
                name='pres_reun_status_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['reuniao', 'trabalho'],
                name='presenca_unica_reuniao_trabalho',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        'presente',
                        'ausente_justificado',
                        'ausente_sem_justificativa',
                    )
                ),
                name='presenca_preparatoria_status_valido',
            ),
        ]

    def __str__(self):
        return f'{self.trabalho} — reunião {self.reuniao.ordem}'


class ParticipacaoEncontro(models.Model):
    class Resultado(models.TextChoices):
        CONCLUIU = 'concluiu', 'Concluiu'
        FALTOU = 'faltou', 'Faltou'
        DESISTIU = 'desistiu', 'Desistiu'

    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='participacoes_encontro',
    )
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='resultados_participacao',
    )
    convite = models.OneToOneField(
        ConviteEncontro,
        on_delete=models.PROTECT,
        related_name='participacao',
        null=True,
        blank=True,
    )
    resultado = models.CharField(max_length=20, choices=Resultado.choices)
    tipo_encontro = models.CharField(
        max_length=20,
        choices=Encontro.Tipo.choices,
        editable=False,
    )
    registrada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_participacaoencontro_resultado'
        indexes = [
            models.Index(
                fields=['encontro', 'resultado'],
                name='part_encontro_result_idx',
            ),
            models.Index(
                fields=['pessoa', 'resultado'],
                name='part_pessoa_result_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['pessoa', 'encontro'],
                name='participacao_unica_pessoa_encontro',
            ),
            models.UniqueConstraint(
                fields=['pessoa', 'tipo_encontro'],
                condition=models.Q(resultado='concluiu'),
                name='conclusao_unica_pessoa_tipo',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    resultado__in=('concluiu', 'faltou', 'desistiu')
                ),
                name='participacao_resultado_valido',
            ),
            models.CheckConstraint(
                condition=models.Q(tipo_encontro__in=Encontro.Tipo.values),
                name='participacao_tipo_valido',
            ),
        ]


class EventoAuditoriaEncontroQuerySet(models.QuerySet):
    def update(self, **kwargs):
        del kwargs
        raise ValidationError(
            'Eventos de auditoria de Encontro são imutáveis.'
        )

    def delete(self):
        raise ValidationError(
            'Eventos de auditoria de Encontro não podem ser removidos.'
        )

    def bulk_update(self, objs, fields, batch_size=None):
        del objs, fields, batch_size
        raise ValidationError(
            'Eventos de auditoria de Encontro são imutáveis.'
        )


class EventoAuditoriaEncontro(models.Model):
    encontro = models.ForeignKey(
        Encontro,
        on_delete=models.PROTECT,
        related_name='eventos_auditoria',
    )
    ator = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='eventos_auditoria_encontro',
    )
    fato = models.CharField(max_length=100)
    entidade = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=100)
    valor_anterior = models.JSONField(default=dict)
    valor_novo = models.JSONField(default=dict)
    justificativa = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True, editable=False)

    objects = EventoAuditoriaEncontroQuerySet.as_manager()

    class Meta:
        ordering = ['-criado_em', '-id']
        indexes = [
            models.Index(
                fields=['encontro', 'criado_em'],
                name='aud_enc_data_idx',
            ),
            models.Index(
                fields=['entidade', 'objeto_id', 'criado_em'],
                name='aud_objeto_data_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(fato=''),
                name='aud_fato_nao_vazio',
            ),
            models.CheckConstraint(
                condition=~models.Q(entidade=''),
                name='aud_entidade_nao_vazia',
            ),
            models.CheckConstraint(
                condition=~models.Q(objeto_id=''),
                name='aud_objeto_id_nao_vazio',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                'Eventos de auditoria de Encontro são imutáveis.'
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        del args, kwargs
        raise ValidationError(
            'Eventos de auditoria de Encontro não podem ser removidos.'
        )

    def __str__(self):
        return (
            f'{self.fato} — Encontro {self.encontro_id} — '
            f'{self.entidade} {self.objeto_id}'
        )


# Relação legada preservada para os contratos atuais de encontristas/equipes.
class VinculoEncontroLegado(models.Model):

    alpinista = models.ForeignKey('Alpinista', on_delete = models.CASCADE, related_name = 'participacoes_encontros')
    encontro = models.ForeignKey('Encontro', on_delete = models.CASCADE, related_name = 'participacoes')

    funcao = models.ForeignKey(FuncaoEncontro, on_delete=models.PROTECT)

    cor_grupo = models.CharField(max_length = 50, null = True, blank = True)

    coordenador = models.BooleanField(default=False, verbose_name="É Coordenador?")

    class Meta:
        db_table = 'core_participacaoencontro'
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
