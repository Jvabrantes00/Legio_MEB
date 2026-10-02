import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_nucleo_encontros'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameModel(
                    old_name='ParticipacaoEncontro',
                    new_name='VinculoEncontroLegado',
                ),
                migrations.AlterModelTable(
                    name='vinculoencontrolegado',
                    table='core_participacaoencontro',
                ),
            ],
        ),
        migrations.CreateModel(
            name='Inscricao',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'tipo',
                    models.CharField(
                        choices=[
                            ('Escalada', 'Escalada'),
                            ('Esppa', 'Esppa'),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pendente', 'Pendente'),
                            ('cumprida', 'Cumprida'),
                        ],
                        default='pendente',
                        max_length=20,
                    ),
                ),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('atualizada_em', models.DateTimeField(auto_now=True)),
                (
                    'cumprida_em',
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    'pessoa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='inscricoes_encontro',
                        to='core.pessoa',
                    ),
                ),
            ],
            options={
                'indexes': [
                    models.Index(
                        fields=['tipo', 'status', 'criada_em'],
                        name='inscr_fila_idx',
                    ),
                    models.Index(
                        fields=['pessoa', 'tipo', 'status'],
                        name='inscr_pessoa_tipo_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        condition=models.Q(('status', 'pendente')),
                        fields=('pessoa', 'tipo'),
                        name='inscricao_pendente_unica_pessoa_tipo',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ('tipo__in', ['Escalada', 'Esppa'])
                        ),
                        name='inscricao_tipo_valido',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ('status__in', ['pendente', 'cumprida'])
                        ),
                        name='inscricao_status_valido',
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                ('cumprida_em__isnull', True),
                                ('status', 'pendente'),
                            )
                            | models.Q(
                                ('cumprida_em__isnull', False),
                                ('status', 'cumprida'),
                            )
                        ),
                        name='inscricao_cumprimento_coerente',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='ConviteEncontro',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'finalidade',
                    models.CharField(
                        choices=[
                            ('participar', 'Participar'),
                            ('trabalhar', 'Trabalhar'),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('convidado', 'Convidado'),
                            ('confirmado', 'Confirmado'),
                            ('recusado', 'Recusado'),
                            ('sem_resposta', 'Sem resposta'),
                        ],
                        default='convidado',
                        max_length=20,
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                (
                    'encontro',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='convites',
                        to='core.encontro',
                    ),
                ),
                (
                    'inscricao',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='convites',
                        to='core.inscricao',
                    ),
                ),
                (
                    'pessoa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='convites_encontro',
                        to='core.pessoa',
                    ),
                ),
            ],
            options={
                'indexes': [
                    models.Index(
                        fields=['encontro', 'finalidade', 'status'],
                        name='conv_encontro_status_idx',
                    ),
                    models.Index(
                        fields=['pessoa', 'status'],
                        name='conv_pessoa_status_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('pessoa', 'encontro', 'finalidade'),
                        name='convite_unico_pessoa_encontro_finalidade',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ('finalidade__in', ['participar', 'trabalhar'])
                        ),
                        name='convite_finalidade_valida',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                'status__in',
                                [
                                    'convidado',
                                    'confirmado',
                                    'recusado',
                                    'sem_resposta',
                                ],
                            )
                        ),
                        name='convite_status_valido',
                    ),
                    models.CheckConstraint(
                        condition=(
                            ~models.Q(('finalidade', 'trabalhar'))
                            | models.Q(('inscricao__isnull', True))
                        ),
                        name='convite_trabalho_sem_inscricao',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='ParticipacaoEncontro',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'resultado',
                    models.CharField(
                        choices=[
                            ('concluiu', 'Concluiu'),
                            ('faltou', 'Faltou'),
                            ('desistiu', 'Desistiu'),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    'tipo_encontro',
                    models.CharField(
                        choices=[
                            ('Escalada', 'Escalada'),
                            ('AVC', 'AVC'),
                            ('Esppa', 'Esppa'),
                            ('Acampamento', 'Acampamento'),
                        ],
                        editable=False,
                        max_length=20,
                    ),
                ),
                ('registrada_em', models.DateTimeField(auto_now_add=True)),
                ('atualizada_em', models.DateTimeField(auto_now=True)),
                (
                    'convite',
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='participacao',
                        to='core.conviteencontro',
                    ),
                ),
                (
                    'encontro',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='resultados_participacao',
                        to='core.encontro',
                    ),
                ),
                (
                    'pessoa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='participacoes_encontro',
                        to='core.pessoa',
                    ),
                ),
            ],
            options={
                'db_table': 'core_participacaoencontro_resultado',
                'indexes': [
                    models.Index(
                        fields=['encontro', 'resultado'],
                        name='part_encontro_result_idx',
                    ),
                    models.Index(
                        fields=['pessoa', 'resultado'],
                        name='part_pessoa_result_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('pessoa', 'encontro'),
                        name='participacao_unica_pessoa_encontro',
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(('resultado', 'concluiu')),
                        fields=('pessoa', 'tipo_encontro'),
                        name='conclusao_unica_pessoa_tipo',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ('resultado__in', ['concluiu', 'faltou', 'desistiu'])
                        ),
                        name='participacao_resultado_valido',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                'tipo_encontro__in',
                                ['Escalada', 'AVC', 'Esppa', 'Acampamento'],
                            )
                        ),
                        name='participacao_tipo_valido',
                    ),
                ],
            },
        ),
    ]
