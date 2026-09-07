import re

from django.core.exceptions import ValidationError


CPF_DIGITS_PATTERN = re.compile(r'^\d{11}$')
CPF_FORMATTED_PATTERN = re.compile(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$')


def normalize_cpf(value):
    """Return an optional CPF as 11 digits, after validating its check digits."""
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    if CPF_FORMATTED_PATTERN.fullmatch(value):
        digits = re.sub(r'\D', '', value)
    elif CPF_DIGITS_PATTERN.fullmatch(value):
        digits = value
    else:
        raise ValidationError('Informe um CPF com 11 dígitos, com ou sem pontuação.')

    if len(set(digits)) == 1:
        raise ValidationError('Informe um CPF válido.')

    for digit_index in (9, 10):
        weight = digit_index + 1
        total = sum(
            int(digit) * (weight - index)
            for index, digit in enumerate(digits[:digit_index])
        )
        remainder = (total * 10) % 11
        expected_digit = 0 if remainder == 10 else remainder
        if expected_digit != int(digits[digit_index]):
            raise ValidationError('Informe um CPF válido.')

    return digits


def validate_cpf(value):
    normalize_cpf(value)
