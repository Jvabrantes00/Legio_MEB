from enum import Enum


class SiaRole(str, Enum):
    SUPORTE = 'Suporte'
    DIRETORIA = 'Diretoria'
    FICHAS = 'Fichas'
    MME = 'MME'
    FORMACAO = 'Formação'
    SECRETARIA = 'Secretaria'
    ACAO_SOCIAL = 'Ação Social'
    LITURGIA = 'Liturgia'
    EVENTOS = 'Eventos'
    COMUNICACAO = 'Comunicação'


RECOGNIZED_ROLES = tuple(role.value for role in SiaRole)

# Papéis com administração ampla dos recursos atuais do SIA.
FULL_ADMIN_ROLES = (SiaRole.SUPORTE, SiaRole.DIRETORIA)

# Administração de pessoas e da operação dos encontros.
FICHAS_MANAGEMENT_ROLES = (*FULL_ADMIN_ROLES, SiaRole.FICHAS)

# Gestão das características musicais e do histórico de Violeiro.
MUSIC_MANAGEMENT_ROLES = (*FICHAS_MANAGEMENT_ROLES, SiaRole.MME)

# Consulta do histórico de palestras, sem conceder escrita à Formação.
FORMATION_HISTORY_ROLES = (*FICHAS_MANAGEMENT_ROLES, SiaRole.FORMACAO)

# Administração do domínio existente de Eventos e suas participações.
EVENT_MANAGEMENT_ROLES = (*FULL_ADMIN_ROLES, SiaRole.EVENTOS)

# Foto de perfil é parte da ficha; Comunicação recebe somente a action dedicada.
PROFILE_PHOTO_MANAGEMENT_ROLES = (
    *FICHAS_MANAGEMENT_ROLES,
    SiaRole.COMUNICACAO,
)

# Galeria de Encontro é um subrecurso próprio, sem conceder CRUD do Encontro.
ENCOUNTER_PHOTO_MANAGEMENT_ROLES = (*FULL_ADMIN_ROLES, SiaRole.COMUNICACAO)
ENCOUNTER_READ_ROLES = (*FICHAS_MANAGEMENT_ROLES, SiaRole.COMUNICACAO)


def role_name(role):
    return role.value if isinstance(role, SiaRole) else str(role)


def user_has_role(user, role):
    if not getattr(user, 'is_authenticated', False):
        return False
    return user.groups.filter(name=role_name(role)).exists()


def user_has_any_role(user, *roles):
    if not getattr(user, 'is_authenticated', False) or not roles:
        return False
    names = {role_name(role) for role in roles}
    return user.groups.filter(name__in=names).exists()
