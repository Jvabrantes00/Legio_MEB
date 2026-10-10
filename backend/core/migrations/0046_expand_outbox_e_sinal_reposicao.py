import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0045_alter_eventoauditoriaencontro_ator'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutboxEntregaConvite',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('segredo_criptografado', models.TextField(
                    blank=True,
                    null=True,
                )),
                ('status', models.CharField(
                    choices=[
                        ('pendente', 'Pendente'),
                        ('concluida', 'Concluída'),
                    ],
                    default='pendente',
                    max_length=20,
                )),
                ('proxima_tentativa_em', models.DateTimeField(
                    blank=True,
                    null=True,
                )),
                ('segredo_destruido_em', models.DateTimeField(
                    blank=True,
                    null=True,
                )),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('atualizada_em', models.DateTimeField(auto_now=True)),
                ('oportunidade', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='outbox_entrega',
                    to='core.oportunidadeconviteencontro',
                )),
            ],
            options={
                'indexes': [
                    models.Index(
                        fields=['status', 'proxima_tentativa_em'],
                        name='out_conv_status_retry_idx',
                    ),
                ],
                'constraints': [
                    models.CheckConstraint(
                        condition=models.Q(
                            ('status__in', ('pendente', 'concluida')),
                        ),
                        name='out_conv_status_valido',
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                ('segredo_criptografado__isnull', False),
                                ('segredo_destruido_em__isnull', True),
                                ('status', 'pendente'),
                            )
                            | models.Q(
                                ('segredo_criptografado__isnull', True),
                                ('segredo_destruido_em__isnull', False),
                                ('status', 'concluida'),
                            )
                        ),
                        name='out_conv_segredo_lifecycle',
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(('segredo_destruido_em__isnull', True))
                            | models.Q(
                                segredo_destruido_em__gte=models.F('criada_em')
                            )
                        ),
                        name='out_conv_destruicao_ordem',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='SinalReposicaoCampanha',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('status', models.CharField(
                    choices=[
                        ('pendente', 'Pendente'),
                        ('processado', 'Processado'),
                    ],
                    default='pendente',
                    max_length=20,
                )),
                ('motivo', models.CharField(
                    choices=[
                        ('confirmacao_liberada', 'Confirmação liberada'),
                        ('capacidade_aumentada', 'Capacidade aumentada'),
                    ],
                    max_length=30,
                )),
                ('processado_em', models.DateTimeField(
                    blank=True,
                    null=True,
                )),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('atualizada_em', models.DateTimeField(auto_now=True)),
                ('campanha', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='sinais_reposicao',
                    to='core.campanhaconvitesencontro',
                )),
            ],
            options={
                'indexes': [
                    models.Index(
                        fields=['status', 'criada_em'],
                        name='sin_rep_status_data_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        condition=models.Q(('status', 'pendente')),
                        fields=('campanha',),
                        name='sin_rep_pendente_unico_campanha',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ('status__in', ('pendente', 'processado')),
                        ),
                        name='sin_rep_status_valido',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                'motivo__in',
                                (
                                    'confirmacao_liberada',
                                    'capacidade_aumentada',
                                ),
                            ),
                        ),
                        name='sin_rep_motivo_valido',
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                ('processado_em__isnull', True),
                                ('status', 'pendente'),
                            )
                            | models.Q(
                                ('processado_em__isnull', False),
                                ('status', 'processado'),
                            )
                        ),
                        name='sin_rep_processamento_coerente',
                    ),
                ],
            },
        ),
    ]
