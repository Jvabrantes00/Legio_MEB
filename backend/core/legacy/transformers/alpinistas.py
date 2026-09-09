from collections.abc import Mapping
from typing import Any

from ..contracts import (
    CanonicalAddress,
    CanonicalLegacyAlpinista,
    CanonicalResponsible,
    TransformationResult,
)
from ..issues import IssueCode, IssueSeverity, MigrationIssue
from ..normalizers import (
    normalize_cep,
    normalize_cpf,
    normalize_email,
    normalize_legacy_date,
    normalize_legacy_id,
    normalize_media_reference,
    normalize_nullable_text,
    normalize_phone,
    normalize_sn_flag,
    normalize_uf,
)
from .common import safe_normalize, unknown_metadata


TABLE = 'alpinista'
CANONICAL_FIELDS = {
    'CD_REGISTRO', 'NO_ALPINISTA', 'DT_NASCIMENTO', 'TX_APELIDO',
    'TX_ENDERECO', 'CD_CEP', 'IN_BAIRRO', 'NO_CIDADE', 'SG_UF',
    'CD_DDD', 'NR_TELEFONE', 'NR_TELEFONE1', 'CD_EMAIL', 'NR_CPF',
    'NO_PAI', 'NR_PAITELEFONE', 'NO_MAE', 'NR_MAETELEFONE',
    'IN_VIOLEIRO', 'URL_FOTO', 'OBS_FICHAS',
}
DEFERRED_FIELDS = {
    'NO_ESCALADA', 'NO_ESPPA', 'NO_AVC', 'NO_ACAMPAMENTO',
    'IN_COR_GRUPO', 'CD_GRUPO', 'NR_GRUPO_FASE', 'NO_GRUPO',
    'NO_GRUPO_AVC', 'IN_ATUANTE', 'situacao', 'situacao_obs',
    'IN_AMIGO', 'AMIGO_CATEGORIA', 'AMIGO_CODIGO', 'AMIGO_BANCO',
    'AMIGO_TIPO_CONTRIBUICAO', 'AMIGO_AGENCIA', 'AMIGO_CONTA',
}


def transform_alpinista(row: Mapping[str, Any]) -> TransformationResult[CanonicalLegacyAlpinista]:
    issues: list[MigrationIssue] = []
    raw_id = normalize_nullable_text(row.get('CD_REGISTRO'))
    legacy_id = safe_normalize(
        normalize_legacy_id,
        row.get('CD_REGISTRO'),
        issues=issues,
        table=TABLE,
        legacy_id=raw_id,
        field='CD_REGISTRO',
    )
    name = normalize_nullable_text(row.get('NO_ALPINISTA'))
    if name is None:
        issues.append(MigrationIssue(
            code=IssueCode.MISSING_REQUIRED_NAME,
            severity=IssueSeverity.ERROR,
            table=TABLE,
            legacy_id=legacy_id or raw_id,
            field='NO_ALPINISTA',
            description='Alpinista legado não possui nome utilizável.',
        ))

    def normalized(normalizer, field, **kwargs):
        return safe_normalize(
            normalizer,
            row.get(field),
            issues=issues,
            table=TABLE,
            legacy_id=legacy_id or raw_id,
            field=field,
            **kwargs,
        )

    phones = []
    for field, ddd in (
        ('NR_TELEFONE', row.get('CD_DDD')),
        ('NR_TELEFONE1', row.get('CD_DDD')),
    ):
        phone = normalized(normalize_phone, field, ddd=ddd)
        if phone and phone not in phones:
            phones.append(phone)
    if len(phones) > 1:
        issues.append(MigrationIssue(
            code=IssueCode.PHONE_CONFLICT,
            severity=IssueSeverity.ERROR,
            table=TABLE,
            legacy_id=legacy_id or raw_id,
            field='NR_TELEFONE,NR_TELEFONE1',
            description='Dois telefones válidos e diferentes exigem decisão de migração.',
        ))

    responsibles = (
        CanonicalResponsible(
            relationship='PAI',
            name=normalize_nullable_text(row.get('NO_PAI')),
            phone=normalized(normalize_phone, 'NR_PAITELEFONE'),
        ),
        CanonicalResponsible(
            relationship='MAE',
            name=normalize_nullable_text(row.get('NO_MAE')),
            phone=normalized(normalize_phone, 'NR_MAETELEFONE'),
        ),
    )
    deferred = {
        field: row.get(field)
        for field in DEFERRED_FIELDS
        if field in row
    }
    dto = CanonicalLegacyAlpinista(
        legacy_id=legacy_id,
        name=name,
        birth_date=normalized(normalize_legacy_date, 'DT_NASCIMENTO'),
        nickname=normalize_nullable_text(row.get('TX_APELIDO')),
        address=CanonicalAddress(
            street=normalize_nullable_text(row.get('TX_ENDERECO')),
            cep=normalized(normalize_cep, 'CD_CEP'),
            district=normalize_nullable_text(row.get('IN_BAIRRO')),
            city=normalize_nullable_text(row.get('NO_CIDADE')),
            state=normalized(normalize_uf, 'SG_UF'),
        ),
        email=normalized(normalize_email, 'CD_EMAIL'),
        phones=tuple(phones),
        responsibles=responsibles,
        cpf=normalized(normalize_cpf, 'NR_CPF'),
        is_violeiro=normalized(normalize_sn_flag, 'IN_VIOLEIRO'),
        photo_reference=normalized(normalize_media_reference, 'URL_FOTO'),
        private_notes=normalize_nullable_text(row.get('OBS_FICHAS')),
        deferred=deferred,
        legacy_metadata=unknown_metadata(
            row,
            CANONICAL_FIELDS | DEFERRED_FIELDS,
        ),
    )
    return TransformationResult(value=dto, issues=tuple(issues))
