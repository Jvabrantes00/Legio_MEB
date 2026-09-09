import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from core.validators import normalize_cpf as normalize_project_cpf

from .issues import IssueCode, LegacyNormalizationError


BRAZILIAN_STATES = frozenset({
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT',
    'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO',
    'RR', 'SC', 'SP', 'SE', 'TO',
})
PHONE_ALLOWED_PATTERN = re.compile(r'^[\d\s()+.\-]+$')
CEP_ALLOWED_PATTERN = re.compile(r'^[\d.\-\s]+$')
MONEY_PATTERNS = (
    (re.compile(r'^-?\d+(?:\.\d{1,2})?$'), '.', ''),
    (re.compile(r'^-?\d+(?:,\d{1,2})?$'), ',', ''),
    (re.compile(r'^-?\d{1,3}(?:\.\d{3})*,\d{1,2}$'), ',', '.'),
    (re.compile(r'^-?\d{1,3}(?:,\d{3})*\.\d{1,2}$'), '.', ','),
)


def normalize_nullable_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            value = value.decode('utf-8', errors='strict')
        except UnicodeDecodeError as error:
            raise LegacyNormalizationError(
                IssueCode.ENCODING_PROBLEM,
                'Texto legado não pôde ser decodificado com UTF-8.',
            ) from error
    normalized = unicodedata.normalize('NFC', str(value)).strip()
    return normalized or None


def normalize_unicode_text(value) -> str | None:
    return normalize_nullable_text(value)


def normalize_email(value) -> str | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    normalized = normalized.casefold()
    try:
        validate_email(normalized)
    except ValidationError as error:
        raise LegacyNormalizationError(
            IssueCode.INVALID_EMAIL,
            'E-mail legado inválido; valor bruto omitido do relatório.',
        ) from error
    return normalized


def _digits_from_phone(value) -> str | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    if not PHONE_ALLOWED_PATTERN.fullmatch(normalized):
        raise LegacyNormalizationError(
            IssueCode.INVALID_PHONE,
            'Telefone legado contém caracteres não reconhecidos.',
        )
    digits = re.sub(r'\D', '', normalized)
    if digits.startswith('55') and len(digits) in {12, 13}:
        digits = digits[2:]
    return digits


def normalize_phone(value, *, ddd=None) -> str | None:
    digits = _digits_from_phone(value)
    if digits is None:
        return None
    ddd_digits = _digits_from_phone(ddd)
    if ddd_digits is not None and len(ddd_digits) != 2:
        raise LegacyNormalizationError(
            IssueCode.INVALID_PHONE,
            'DDD legado deve possuir exatamente dois dígitos.',
        )
    if len(digits) in {8, 9} and ddd_digits:
        digits = f'{ddd_digits}{digits}'
    if len(digits) not in {8, 9, 10, 11}:
        raise LegacyNormalizationError(
            IssueCode.INVALID_PHONE,
            'Telefone legado possui quantidade de dígitos inválida.',
        )
    return digits


def normalize_phone_candidates(primary, secondary, *, ddd=None) -> tuple[tuple[str, ...], bool]:
    phones = []
    for value in (primary, secondary):
        phone = normalize_phone(value, ddd=ddd)
        if phone and phone not in phones:
            phones.append(phone)
    return tuple(phones), len(phones) > 1


def normalize_cpf(value) -> str | None:
    try:
        return normalize_project_cpf(value)
    except ValidationError as error:
        raise LegacyNormalizationError(
            IssueCode.INVALID_CPF,
            'CPF legado inválido; valor bruto omitido do relatório.',
        ) from error


def normalize_cep(value) -> str | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    if not CEP_ALLOWED_PATTERN.fullmatch(normalized):
        raise LegacyNormalizationError(
            IssueCode.INVALID_CEP,
            'CEP legado contém caracteres não reconhecidos.',
        )
    digits = re.sub(r'\D', '', normalized)
    if len(digits) != 8:
        raise LegacyNormalizationError(
            IssueCode.INVALID_CEP,
            'CEP legado deve possuir oito dígitos.',
        )
    return digits


def normalize_uf(value) -> str | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    normalized = normalized.upper()
    if normalized not in BRAZILIAN_STATES:
        raise LegacyNormalizationError(
            IssueCode.INVALID_UF,
            'UF legada não corresponde a uma unidade federativa brasileira.',
        )
    return normalized


def normalize_sn_flag(value) -> bool | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    normalized = normalized.upper()
    if normalized == 'S':
        return True
    if normalized == 'N':
        return False
    raise LegacyNormalizationError(
        IssueCode.UNKNOWN_BOOLEAN_VALUE,
        'Flag booleana legada desconhecida; somente S e N são aceitos.',
    )


def normalize_legacy_date(value) -> date | None:
    if value is None or normalize_nullable_text(value) is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    normalized = normalize_nullable_text(value)
    try:
        return datetime.strptime(normalized, '%Y-%m-%d').date()
    except (TypeError, ValueError) as error:
        raise LegacyNormalizationError(
            IssueCode.INVALID_DATE,
            'Data legada inválida ou em formato ainda não mapeado.',
        ) from error


def normalize_legacy_datetime(value) -> datetime | None:
    if value is None or normalize_nullable_text(value) is None:
        return None
    if isinstance(value, datetime):
        return value
    normalized = normalize_nullable_text(value)
    for date_format in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(normalized, date_format)
        except ValueError:
            continue
    raise LegacyNormalizationError(
        IssueCode.INVALID_DATE,
        'Data/hora legada inválida ou em formato ainda não mapeado.',
    )


def normalize_legacy_id(value) -> int | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    if isinstance(value, bool) or not re.fullmatch(r'\d+', normalized):
        raise LegacyNormalizationError(
            IssueCode.INVALID_ID,
            'Identificador legado deve ser um inteiro positivo.',
        )
    result = int(normalized)
    if result <= 0:
        raise LegacyNormalizationError(
            IssueCode.INVALID_ID,
            'Identificador legado deve ser maior que zero.',
        )
    return result


def normalize_legacy_money(value) -> Decimal | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    for pattern, decimal_separator, thousands_separator in MONEY_PATTERNS:
        if not pattern.fullmatch(normalized):
            continue
        canonical = normalized.replace(thousands_separator, '') if thousands_separator else normalized
        if decimal_separator == ',':
            canonical = canonical.replace(',', '.')
        try:
            return Decimal(canonical)
        except InvalidOperation:
            break
    raise LegacyNormalizationError(
        IssueCode.INVALID_MONEY,
        'Valor monetário legado é inválido ou ambíguo.',
    )


def normalize_legacy_decimal(value) -> Decimal | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    if not re.fullmatch(r'-?\d+(?:\.\d+)?', normalized):
        raise LegacyNormalizationError(
            IssueCode.INVALID_NUMBER,
            'Número decimal legado inválido ou em formato ainda não mapeado.',
        )
    try:
        return Decimal(normalized)
    except InvalidOperation as error:
        raise LegacyNormalizationError(
            IssueCode.INVALID_NUMBER,
            'Número decimal legado inválido.',
        ) from error


def normalize_media_reference(value) -> str | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    parsed = urlsplit(normalized)
    if parsed.scheme and parsed.scheme.lower() not in {'http', 'https'}:
        raise LegacyNormalizationError(
            IssueCode.INVALID_MEDIA_REFERENCE,
            'Referência de mídia usa protocolo não permitido.',
        )
    if not parsed.scheme and ('..' in parsed.path.split('/') or '\\' in normalized):
        raise LegacyNormalizationError(
            IssueCode.INVALID_MEDIA_REFERENCE,
            'Referência relativa de mídia contém caminho inseguro.',
        )
    return normalized
