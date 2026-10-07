import os
from datetime import date, time, timedelta

from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from core.models import (
    Alpinista,
    AvaliacaoEncontro,
    ConfiguracaoGrupo,
    ConviteEncontro,
    CoordenacaoGrupo,
    EnderecoPessoa,
    Encontro,
    EquipeEncontro,
    Frequencia,
    Grupo,
    Inscricao,
    ItemPropostaVioleiros,
    PalestranteSessao,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
    PresencaPreparatoria,
    PropostaVioleiros,
    ReuniaoPreparatoriaEncontro,
    RoleEquipeEncontro,
    SessaoFormativa,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoConjugal,
    VinculoGrupo,
    VinculoUsuarioPessoa,
)
from core.roles import SiaRole
from core.services.avaliacoes_encontro import criar_avaliacao_encontro
from core.services.encontros import (
    criar_encontro_com_agenda,
    finalizar_encontro,
    iniciar_encontro,
    iniciar_preparacao,
    oficializar_agenda,
)
from core.services.grupos import (
    criar_configuracao_grupo,
    criar_vinculo_grupo,
    perfil_alpinista_ativo,
    registrar_frequencia,
)
from core.services.participacoes import (
    criar_convite,
    criar_inscricao,
    registrar_resultado_participacao,
    responder_convite,
)
from core.services.propostas_violeiros import (
    criar_proposta_violeiros,
    preencher_posicao_proposta,
)
from core.services.reunioes_preparatorias import (
    criar_reuniao_preparatoria,
    registrar_presenca_preparatoria,
)
from core.services.trabalhos import (
    criar_convite_trabalho,
    iniciar_trabalho_confirmado,
    preparar_equipes_encontro,
    registrar_resultado_trabalho,
)


DEMO_ENVIRONMENT = 'development'
DEMO_EMAIL_DOMAIN = 'example.invalid'
DEMO_REFERENCE_DATE = date(2026, 10, 7)

DEMO_ACCOUNTS = (
    ('demo.suporte', SiaRole.SUPORTE),
    ('demo.diretoria', SiaRole.DIRETORIA),
    ('demo.fichas', SiaRole.FICHAS),
    ('demo.mme', SiaRole.MME),
    ('demo.formacao', SiaRole.FORMACAO),
    ('demo.secretaria', SiaRole.SECRETARIA),
    ('demo.acao_social', SiaRole.ACAO_SOCIAL),
    ('demo.liturgia', SiaRole.LITURGIA),
    ('demo.eventos', SiaRole.EVENTOS),
    ('demo.comunicacao', SiaRole.COMUNICACAO),
    ('demo.sem_papel', None),
    ('demo.superuser', None),
)

DEMO_PERSON_NAMES = (
    'Ana Demo Almeida',
    'Bruno Demo Barbosa',
    'Carla Demo Costa',
    'Daniel Demo Dias',
    'Elisa Demo Esteves',
    'Felipe Demo Ferreira',
    'Gabriela Demo Gomes',
    'Henrique Demo Horizonte',
    'Isabela Demo Iglesias',
    'João Demo Jardim',
    'Karen Demo Kairós',
    'Lucas Demo Lima',
    'Marina Demo Martins',
    'Nicolas Demo Nogueira',
    'Olívia Demo Oliveira',
    'Paulo Demo Pereira',
    'Queila Demo Queiroz',
    'Rafael Demo Rocha',
    'Sofia Demo Santos',
    'Tiago Demo Teixeira',
    'Ursula Demo Uchoa',
    'Vitor Demo Vieira',
    'Waleska Demo Wanderley',
    'Yara Demo Ypiranga',
    'Arthur Demo Araújo',
    'Beatriz Demo Braga',
    'Caio Demo Cardoso',
    'Débora Demo Duarte',
    'Eduardo Demo Evangelista',
    'Flávia Demo Farias',
    'Gustavo Demo Guimarães',
    'Helena Demo Henriques',
    'Igor Demo Inácio',
    'Júlia Demo Junqueira',
    'Leandro Demo Lopes',
    'Mônica Demo Medeiros',
    'Natália Demo Neves',
    'Otávio Demo Ornelas',
    'Priscila Demo Pires',
    'Renato Demo Rezende',
)

DEMO_GROUP_NAMES = (
    '[DEMO] Betânia',
    '[DEMO] Emaús',
    '[DEMO] Sinai',
    '[DEMO] Tabor',
)

DEMO_ENCOUNTERS = (
    ('[DEMO] Escalada Serra Azul 2027', Encontro.Tipo.ESCALADA),
    ('[DEMO] Escalada Vale Verde 2027', Encontro.Tipo.ESCALADA),
    ('[DEMO] ESPPA Horizonte 2027', Encontro.Tipo.ESPPA),
    ('[DEMO] ESPPA Caminho 2026', Encontro.Tipo.ESPPA),
)

DEMO_TEMPLATE_SPECS = (
    ('demo-coordenacao-geral', '[DEMO] Coordenação Geral'),
    ('demo-acolhida', '[DEMO] Acolhida'),
    ('violeiros', '[DEMO] Violeiros'),
)
DEMO_TEMPLATE_CODES = tuple(code for code, _ in DEMO_TEMPLATE_SPECS)
DEMO_ROLE_CODES = (
    'demo-coordenador-geral',
    'demo-apoio-coordenacao',
    'demo-coordenador-acolhida',
    'demo-integrante-acolhida',
    'demo-coordenador-violeiros',
    'demo-violeiro',
)


def _demo_person_email(position):
    return f'pessoa.{position:02d}@{DEMO_EMAIL_DOMAIN}'


def _demo_person_filter():
    query = Q(pk__in=[])
    for position, name in enumerate(DEMO_PERSON_NAMES, start=1):
        query |= Q(nome=name, email=_demo_person_email(position))
    return query


def _demo_encounter_filter():
    query = Q(pk__in=[])
    for title, encounter_type in DEMO_ENCOUNTERS:
        query |= Q(encontro=title, tipo=encounter_type)
    return query


def _demo_template_filter():
    query = Q(pk__in=[])
    for encounter_type in (Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA):
        for code, name in DEMO_TEMPLATE_SPECS:
            query |= Q(
                tipo_encontro=encounter_type,
                codigo=code,
                nome=name,
            )
    return query


def _ensure_development_environment():
    environment = os.getenv('SIA_ENVIRONMENT', '').strip().lower()
    if not settings.DEBUG or environment != DEMO_ENVIRONMENT:
        raise CommandError(
            'seed_demo é bloqueado fora do desenvolvimento. '
            'Exige DEBUG=True e SIA_ENVIRONMENT=development.'
        )


def _delete_demo_dataset():
    users = User.objects.filter(
        username__in=[username for username, _ in DEMO_ACCOUNTS]
    )
    people = Pessoa.objects.filter(_demo_person_filter())
    profiles = PerfilAlpinista.objects.filter(pessoa__in=people)
    encounters = Encontro.objects.filter(_demo_encounter_filter())
    templates = TemplateEquipeEncontro.objects.filter(_demo_template_filter())
    template_scope = TemplateEquipeEncontro.objects.filter(
        tipo_encontro__in=(Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA),
        codigo__in=DEMO_TEMPLATE_CODES,
    )

    PalestranteSessao.objects.filter(
        sessao_formativa__encontro__in=encounters
    ).delete()
    SessaoFormativa.objects.filter(encontro__in=encounters).delete()
    PresencaPreparatoria.objects.filter(
        Q(reuniao__encontro__in=encounters)
        | Q(trabalho__encontro__in=encounters)
    ).delete()
    ItemPropostaVioleiros.objects.filter(
        proposta__encontro__in=encounters
    ).delete()
    PropostaVioleiros.objects.filter(encontro__in=encounters).delete()
    TrabalhoEncontro.objects.filter(encontro__in=encounters).delete()
    ParticipacaoEncontro.objects.filter(encontro__in=encounters).delete()
    ConviteEncontro.objects.filter(encontro__in=encounters).delete()
    Inscricao.objects.filter(pessoa__in=people).delete()
    ReuniaoPreparatoriaEncontro.objects.filter(
        encontro__in=encounters
    ).delete()
    AvaliacaoEncontro.objects.filter(encontro__in=encounters).delete()
    RoleEquipeEncontro.objects.filter(
        equipe_encontro__encontro__in=encounters
    ).delete()
    EquipeEncontro.objects.filter(encontro__in=encounters).delete()
    encounters.delete()

    Frequencia.objects.filter(perfil_alpinista__in=profiles).delete()
    CoordenacaoGrupo.objects.filter(perfil_alpinista__in=profiles).delete()
    VinculoGrupo.objects.filter(perfil_alpinista__in=profiles).delete()
    Alpinista.objects.filter(pessoa__in=people).delete()
    VinculoConjugal.objects.filter(
        Q(pessoa_a__in=people) | Q(pessoa_b__in=people)
    ).delete()
    VinculoUsuarioPessoa.objects.filter(
        Q(usuario__in=users) | Q(pessoa__in=people)
    ).delete()
    profiles.delete()
    people.delete()

    ConfiguracaoGrupo.objects.filter(
        grupo__nome__in=DEMO_GROUP_NAMES
    ).delete()
    Grupo.objects.filter(nome__in=DEMO_GROUP_NAMES).delete()

    TemplateRoleEquipe.objects.filter(
        template_equipe__in=template_scope,
        codigo__in=DEMO_ROLE_CODES,
    ).delete()
    templates.delete()
    users.delete()


def _create_people():
    people = []
    for position, name in enumerate(DEMO_PERSON_NAMES, start=1):
        is_minor = position >= 35
        person = Pessoa.objects.create(
            nome=name,
            apelido=f'Demo {position:02d}',
            data_nascimento=(
                date(2012 + (position % 3), (position % 12) + 1, 10)
                if is_minor
                else date(1985 + (position % 18), (position % 12) + 1, 10)
            ),
            cpf=None,
            email=_demo_person_email(position),
            estado_civil=(
                Pessoa.EstadoCivil.CASADO
                if position in {1, 2, 3, 4}
                else Pessoa.EstadoCivil.SOLTEIRO
            ),
            batismo=(position % 3 != 0),
            primeira_comunhao=(None if position % 4 == 0 else position % 2 == 0),
            crisma=(None if position % 5 == 0 else position % 3 == 0),
        )
        person.telefones.create(
            numero=f'+55 61 0000-{position:04d}',
            whatsapp=position % 2 == 0,
        )
        EnderecoPessoa.objects.create(
            pessoa=person,
            logradouro=f'[DEMO] Rua de Teste {position:02d}',
            numero=str(position),
            bairro='Bairro Demonstração',
            cidade='Brasília',
            estado='DF',
        )
        if is_minor:
            person.responsaveis.create(
                nome=f'Responsável Demo {position:02d}',
                parentesco='Responsável legal',
                telefone=f'+55 61 0001-{position:04d}',
                whatsapp=True,
                principal=True,
            )
        people.append(person)

    for left, right in ((people[0], people[1]), (people[2], people[3])):
        person_a, person_b = sorted((left, right), key=lambda item: item.pk)
        VinculoConjugal.objects.create(pessoa_a=person_a, pessoa_b=person_b)

    for position, person in enumerate(people[:30], start=1):
        PerfilAlpinista.objects.create(
            pessoa=person,
            violeiro=position <= 10,
            canta=position % 3 == 0,
            disponivel_mme=position <= 10,
        )
    return people


def _create_accounts(people, password):
    accounts = []
    for index, (username, role) in enumerate(DEMO_ACCOUNTS):
        is_superuser = username == 'demo.superuser'
        user = User.objects.create(
            username=username,
            email=f'{username}@{DEMO_EMAIL_DOMAIN}',
            is_staff=is_superuser,
            is_superuser=is_superuser,
            is_active=True,
        )
        user.set_password(password)
        user.save(update_fields=['password'])
        if role is not None:
            group, _ = AuthGroup.objects.get_or_create(name=role.value)
            user.groups.add(group)
        if not is_superuser:
            VinculoUsuarioPessoa.objects.create(
                usuario=user,
                pessoa=people[index],
            )
        accounts.append((user, role))
    return accounts


def _create_groups_and_frequency(people, recorder):
    groups = []
    for index, name in enumerate(DEMO_GROUP_NAMES):
        group = Grupo.objects.create(nome=name)
        criar_configuracao_grupo(
            grupo=group,
            vigente_desde=date(2026, 1, 1),
            local_reuniao=f'[DEMO] Salão {index + 1}',
            dia_semana=('quarta', 'quinta', 'sexta', 'domingo')[index],
            horario=time(19, 30),
        )
        groups.append(group)

    profiles = list(
        PerfilAlpinista.objects
        .filter(pessoa__in=people)
        .select_related('pessoa')
        .order_by('pessoa__nome')
    )
    today = DEMO_REFERENCE_DATE
    for index, profile in enumerate(profiles):
        group = groups[index % len(groups)]
        criar_vinculo_grupo(
            perfil_alpinista=profile,
            grupo=group,
            inicio=date(2026, 1, 1),
        )
        if index < 10:
            attendance_date = today - timedelta(days=30 + index)
        elif index < 20:
            attendance_date = today - timedelta(days=170 + (index - 10))
        elif index < 26:
            attendance_date = today - timedelta(days=220 + (index - 20))
        else:
            continue
        registrar_frequencia(
            perfil_alpinista=profile,
            data=attendance_date,
            grupo=group,
            registrada_por=recorder,
            data_atual=DEMO_REFERENCE_DATE,
        )
    return groups


def _days(*items):
    return [
        {
            'ordem': index,
            'data': day,
            'rotulo': label,
            'descricao': description,
        }
        for index, (day, label, description) in enumerate(items, start=1)
    ]


def _create_encounters():
    serra = criar_encontro_com_agenda(
        encontro=DEMO_ENCOUNTERS[0][0],
        tipo=Encontro.Tipo.ESCALADA,
        data_referencia=date(2027, 3, 12),
        data_exato='12, 13 e 14 de março de 2027',
        local='[DEMO] Casa Serra Azul',
        dias=_days(
            (date(2027, 3, 12), 'Sexta-feira', 'Abertura provisória'),
            (date(2027, 3, 13), 'Sábado', 'Programação provisória'),
            (date(2027, 3, 14), 'Domingo', 'Encerramento provisório'),
        ),
    )
    vale = criar_encontro_com_agenda(
        encontro=DEMO_ENCOUNTERS[1][0],
        tipo=Encontro.Tipo.ESCALADA,
        data_referencia=date(2027, 4, 16),
        data_exato='16, 17 e 18 de abril de 2027',
        local='[DEMO] Casa Vale Verde',
        dias=_days(
            (date(2027, 4, 16), 'Sexta-feira', 'Abertura'),
            (date(2027, 4, 17), 'Sábado', 'Programação principal'),
            (date(2027, 4, 18), 'Domingo', 'Encerramento'),
        ),
    )
    oficializar_agenda(vale)
    iniciar_preparacao(vale)

    horizonte = criar_encontro_com_agenda(
        encontro=DEMO_ENCOUNTERS[2][0],
        tipo=Encontro.Tipo.ESPPA,
        data_referencia=date(2027, 3, 14),
        data_exato='14, 15 e 16 de março de 2027',
        local='[DEMO] Centro Horizonte',
        dias=_days(
            (date(2027, 3, 14), 'Abertura', 'Conflito demonstrativo'),
            (date(2027, 3, 15), 'Formação', 'Programação principal'),
            (date(2027, 3, 16), 'Encerramento', 'Envio'),
        ),
    )
    oficializar_agenda(horizonte)

    caminho = criar_encontro_com_agenda(
        encontro=DEMO_ENCOUNTERS[3][0],
        tipo=Encontro.Tipo.ESPPA,
        data_referencia=date(2026, 6, 12),
        data_exato='12, 13 e 14 de junho de 2026',
        local='[DEMO] Centro Caminho',
        dias=_days(
            (date(2026, 6, 12), 'Sexta-feira', 'Abertura histórica'),
            (date(2026, 6, 13), 'Sábado', 'Programação histórica'),
            (date(2026, 6, 14), 'Domingo', 'Encerramento histórico'),
        ),
    )
    oficializar_agenda(caminho)
    iniciar_preparacao(caminho)
    iniciar_encontro(caminho)
    return {
        'serra': serra,
        'vale': vale,
        'horizonte': horizonte,
        'caminho': caminho,
    }


def _create_participation_flows(people, encounters):
    historical_results = (
        (people[0], ParticipacaoEncontro.Resultado.CONCLUIU),
        (people[1], ParticipacaoEncontro.Resultado.CONCLUIU),
        (people[2], ParticipacaoEncontro.Resultado.CONCLUIU),
        (people[30], ParticipacaoEncontro.Resultado.CONCLUIU),
        (people[31], ParticipacaoEncontro.Resultado.CONCLUIU),
        (people[3], ParticipacaoEncontro.Resultado.FALTOU),
        (people[4], ParticipacaoEncontro.Resultado.DESISTIU),
    )
    for person, result in historical_results:
        registration = criar_inscricao(
            pessoa=person,
            tipo=Encontro.Tipo.ESPPA,
        )
        invitation = criar_convite(
            pessoa=person,
            encontro=encounters['caminho'],
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            inscricao=registration,
        )
        responder_convite(
            invitation,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        registrar_resultado_participacao(
            pessoa=person,
            encontro=encounters['caminho'],
            resultado=result,
            convite=invitation,
        )

    future_flows = (
        (encounters['serra'], Encontro.Tipo.ESCALADA, people[32:36]),
        (encounters['horizonte'], Encontro.Tipo.ESPPA, people[7:11]),
    )
    statuses = (
        ConviteEncontro.Status.CONVIDADO,
        ConviteEncontro.Status.CONFIRMADO,
        ConviteEncontro.Status.RECUSADO,
        ConviteEncontro.Status.SEM_RESPOSTA,
    )
    for encounter, encounter_type, candidates in future_flows:
        for person, status in zip(candidates, statuses, strict=True):
            registration = criar_inscricao(pessoa=person, tipo=encounter_type)
            invitation = criar_convite(
                pessoa=person,
                encontro=encounter,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
                inscricao=registration,
            )
            if status != ConviteEncontro.Status.CONVIDADO:
                responder_convite(invitation, status=status)


def _create_legacy_alpinistas(people):
    profiles = {
        profile.pessoa_id: profile
        for profile in PerfilAlpinista.objects.filter(pessoa__in=people)
    }
    for position, person in enumerate(people, start=1):
        profile = profiles.get(person.pk)
        if profile is None:
            continue
        active = perfil_alpinista_ativo(
            profile,
            data_referencia=DEMO_REFERENCE_DATE,
        )
        Alpinista.objects.create(
            pessoa=person,
            nome=person.nome,
            dataNascimento=person.data_nascimento,
            email=f'alpinista.{position:02d}@{DEMO_EMAIL_DOMAIN}',
            telefone=f'+55 61 0002-{position:04d}',
            status=(
                Alpinista.Status.ATIVO
                if active
                else Alpinista.Status.INATIVO
            ),
            batizado=person.batismo,
            primeira_comunhao=person.primeira_comunhao,
            crismado=person.crisma,
            eh_violeiro=profile.violeiro,
            canta=profile.canta,
        )


def _prepare_mme_profiles(people):
    profiles = [
        PerfilAlpinista.objects.get(pessoa=people[index])
        for index in (0, 1, 2, 30, 31)
    ]
    for profile in profiles:
        profile.violeiro = True
        profile.disponivel_mme = True
        profile.save(
            update_fields=['violeiro', 'disponivel_mme', 'atualizado_em']
        )
    return profiles


def _create_team_templates():
    specifications = (
        (
            'demo-coordenacao-geral',
            '[DEMO] Coordenação Geral',
            1,
            (
                ('demo-coordenador-geral', 'Coordenador Geral', 1, True),
                ('demo-apoio-coordenacao', 'Apoio da Coordenação', 4, False),
            ),
        ),
        (
            'demo-acolhida',
            '[DEMO] Acolhida',
            2,
            (
                (
                    'demo-coordenador-acolhida',
                    'Coordenador da Acolhida',
                    1,
                    False,
                ),
                ('demo-integrante-acolhida', 'Integrante da Acolhida', 4, False),
            ),
        ),
        (
            'violeiros',
            '[DEMO] Violeiros',
            3,
            (
                (
                    'demo-coordenador-violeiros',
                    'Coordenador dos Violeiros',
                    1,
                    False,
                ),
                ('demo-violeiro', 'Violeiro', 4, False),
            ),
        ),
    )
    for encounter_type in (Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA):
        for code, name, order, roles in specifications:
            template, _ = TemplateEquipeEncontro.objects.get_or_create(
                tipo_encontro=encounter_type,
                codigo=code,
                defaults={
                    'nome': name,
                    'ordem': order,
                    'capacidade_minima_recomendada': 2,
                    'capacidade_maxima_recomendada': 5,
                },
            )
            for role_order, (role_code, role_name, quantity, attendance) in enumerate(
                roles,
                start=1,
            ):
                TemplateRoleEquipe.objects.get_or_create(
                    template_equipe=template,
                    codigo=role_code,
                    defaults={
                        'nome': role_name,
                        'ordem': role_order,
                        'quantidade_estrutural': quantity,
                        'concede_registro_presenca': attendance,
                    },
                )


def _role(encounter, team_code, role_code):
    return RoleEquipeEncontro.objects.get(
        equipe_encontro__encontro=encounter,
        equipe_encontro__codigo=team_code,
        codigo=role_code,
    )


def _create_work(person, encounter, role=None, final_status=None):
    invitation = criar_convite_trabalho(
        pessoa=person,
        encontro=encounter,
        role_proposta=role,
        confirmar_avisos=True,
    )
    responder_convite(invitation, status=ConviteEncontro.Status.CONFIRMADO)
    work = iniciar_trabalho_confirmado(invitation, confirmar_avisos=True)
    if final_status is not None:
        work = registrar_resultado_trabalho(work, status=final_status)
    return work


def _create_teams_work_and_mme(people, encounters, proposal_profiles):
    for encounter in (
        encounters['vale'],
        encounters['horizonte'],
        encounters['caminho'],
    ):
        preparar_equipes_encontro(encounter)

    proposal = criar_proposta_violeiros(
        encontro=encounters['vale'],
        nome='[DEMO] Proposta principal de Violeiros',
    )
    preencher_posicao_proposta(
        proposal,
        perfil_alpinista=proposal_profiles[0],
        papel_sugerido=ItemPropostaVioleiros.PapelSugerido.COORDENADOR,
        posicao=1,
    )
    for position, profile in enumerate(proposal_profiles[1:], start=1):
        preencher_posicao_proposta(
            proposal,
            perfil_alpinista=profile,
            papel_sugerido=ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
            posicao=position,
        )

    finalized_work_specs = (
        (
            people[0],
            'demo-coordenacao-geral',
            'demo-coordenador-geral',
            TrabalhoEncontro.Status.TRABALHOU,
        ),
        (
            people[1],
            'demo-coordenacao-geral',
            'demo-apoio-coordenacao',
            TrabalhoEncontro.Status.TRABALHOU,
        ),
        (
            people[2],
            'violeiros',
            'demo-coordenador-violeiros',
            TrabalhoEncontro.Status.TRABALHOU,
        ),
        (
            people[30],
            'violeiros',
            'demo-violeiro',
            TrabalhoEncontro.Status.TRABALHOU,
        ),
        (
            people[31],
            'demo-acolhida',
            'demo-coordenador-acolhida',
            TrabalhoEncontro.Status.TRABALHOU,
        ),
        (
            people[3],
            'demo-acolhida',
            'demo-integrante-acolhida',
            TrabalhoEncontro.Status.TRABALHOU,
        ),
        (
            people[4],
            'demo-coordenacao-geral',
            'demo-apoio-coordenacao',
            TrabalhoEncontro.Status.FALTOU,
        ),
    )
    for person, team_code, role_code, result in finalized_work_specs:
        _create_work(
            person,
            encounters['caminho'],
            _role(encounters['caminho'], team_code, role_code),
            result,
        )

    vale_works = [
        _create_work(
            people[1],
            encounters['vale'],
            _role(encounters['vale'], 'violeiros', 'demo-coordenador-violeiros'),
        ),
        _create_work(
            people[2],
            encounters['vale'],
            _role(
                encounters['vale'],
                'demo-acolhida',
                'demo-coordenador-acolhida',
            ),
        ),
        _create_work(
            people[5],
            encounters['vale'],
            _role(
                encounters['vale'],
                'demo-coordenacao-geral',
                'demo-coordenador-geral',
            ),
        ),
        _create_work(people[6], encounters['vale']),
    ]
    criar_convite_trabalho(
        pessoa=people[7],
        encontro=encounters['vale'],
        confirmar_avisos=True,
    )

    _create_work(
        people[11],
        encounters['horizonte'],
        _role(
            encounters['horizonte'],
            'demo-coordenacao-geral',
            'demo-coordenador-geral',
        ),
    )
    _create_work(
        people[12],
        encounters['horizonte'],
        _role(
            encounters['horizonte'],
            'demo-acolhida',
            'demo-integrante-acolhida',
        ),
    )
    criar_convite_trabalho(
        pessoa=people[13],
        encontro=encounters['horizonte'],
        confirmar_avisos=True,
    )

    proposal_profiles[-1].disponivel_mme = False
    proposal_profiles[-1].save(update_fields=['disponivel_mme', 'atualizado_em'])
    return proposal, vale_works


def _create_preparatory_meetings(encounter, works, recorder):
    meetings = (
        criar_reuniao_preparatoria(
            encontro=encounter,
            ordem=1,
            data=date(2026, 9, 10),
            horario=time(19, 30),
            local='[DEMO] Salão Vale Verde',
        ),
        criar_reuniao_preparatoria(
            encontro=encounter,
            ordem=2,
            data=date(2026, 9, 24),
            horario=time(19, 30),
            local='[DEMO] Salão Vale Verde',
        ),
        criar_reuniao_preparatoria(
            encontro=encounter,
            ordem=3,
            data=date(2026, 10, 1),
            horario=time(19, 30),
            local='[DEMO] Paróquia Vale Verde',
            complemento='Missa de Entrega',
        ),
    )
    statuses = (
        PresencaPreparatoria.Status.PRESENTE,
        PresencaPreparatoria.Status.AUSENTE_JUSTIFICADO,
        PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA,
    )
    for meeting_index, meeting in enumerate(meetings[:2]):
        for work_index, work in enumerate(works[:3]):
            status = statuses[(meeting_index + work_index) % len(statuses)]
            registrar_presenca_preparatoria(
                reuniao=meeting,
                trabalho=work,
                status=status,
                registrada_por=recorder,
                justificativa=(
                    'Compromisso previamente informado.'
                    if status == PresencaPreparatoria.Status.AUSENTE_JUSTIFICADO
                    else ''
                ),
            )
    return meetings


def _seed_dataset(password):
    people = _create_people()
    accounts = _create_accounts(people, password)
    recorder = next(user for user, role in accounts if role == SiaRole.FICHAS)
    encounters = _create_encounters()
    _create_participation_flows(people, encounters)
    groups = _create_groups_and_frequency(people, recorder)
    proposal_profiles = _prepare_mme_profiles(people)
    _create_legacy_alpinistas(people)
    _create_team_templates()
    proposal, vale_works = _create_teams_work_and_mme(
        people,
        encounters,
        proposal_profiles,
    )
    finalizar_encontro(encounters['caminho'])
    meetings = _create_preparatory_meetings(
        encounters['vale'],
        vale_works,
        recorder,
    )
    criar_avaliacao_encontro(
        encontro=encounters['vale'],
        data=date(2027, 4, 25),
    )
    return {
        'people': people,
        'accounts': accounts,
        'groups': groups,
        'encounters': encounters,
        'proposal': proposal,
        'meetings': meetings,
    }


class Command(BaseCommand):
    help = 'Cria ou remove o dataset controlado de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove somente o dataset demo reconhecido por allowlists exatas.',
        )
        parser.add_argument(
            '--password',
            help=(
                'Senha das contas demo. Prefira SIA_DEMO_PASSWORD para evitar '
                'exposição no histórico do shell.'
            ),
        )

    def handle(self, *args, **options):
        _ensure_development_environment()
        reset_only = options['reset']
        password = options.get('password') or os.getenv('SIA_DEMO_PASSWORD')
        if not reset_only and not password:
            raise CommandError(
                'Informe SIA_DEMO_PASSWORD ou --password para criar o dataset.'
            )

        with transaction.atomic():
            _delete_demo_dataset()
            if reset_only:
                self.stdout.write(self.style.SUCCESS('Dataset demo removido.'))
                return
            result = _seed_dataset(password)

        encounter_ids = [item.pk for item in result['encounters'].values()]
        people_ids = [person.pk for person in result['people']]
        self.stdout.write(self.style.SUCCESS('Dataset demo criado com sucesso.'))
        self.stdout.write(f'Pessoas: {len(result["people"])}')
        self.stdout.write(
            'Alpinistas (PerfilAlpinista): '
            f'{PerfilAlpinista.objects.filter(pessoa_id__in=people_ids).count()}'
        )
        self.stdout.write(f'Grupos: {len(result["groups"])}')
        self.stdout.write(f'Encontros: {len(result["encounters"])}')
        self.stdout.write(
            f'Inscrições: {Inscricao.objects.filter(pessoa_id__in=people_ids).count()}'
        )
        self.stdout.write(
            'Equipes/Trabalhos: '
            f'{EquipeEncontro.objects.filter(encontro_id__in=encounter_ids).count()}/'
            f'{TrabalhoEncontro.objects.filter(encontro_id__in=encounter_ids).count()}'
        )
        self.stdout.write(f'Preparatórias: {len(result["meetings"])}')
        self.stdout.write('Propostas MME: 1 (cinco slots ativos)')
        self.stdout.write(f'Contas demo: {len(result["accounts"])}')
        self.stdout.write('Contas e papéis:')
        for user, role in result['accounts']:
            if user.is_superuser:
                label = 'superuser técnico'
            elif role is None:
                label = 'sem papel de negócio'
            else:
                label = role.value
            self.stdout.write(f'- {user.username}: {label}')
