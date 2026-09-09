from datetime import date, datetime
from decimal import Decimal
import unicodedata

from django.test import SimpleTestCase

from core.legacy.issues import IssueCode, LegacyNormalizationError
from core.legacy.normalizers import (
    normalize_cep,
    normalize_cpf,
    normalize_email,
    normalize_legacy_date,
    normalize_legacy_datetime,
    normalize_legacy_decimal,
    normalize_legacy_id,
    normalize_legacy_money,
    normalize_media_reference,
    normalize_nullable_text,
    normalize_phone,
    normalize_sn_flag,
    normalize_uf,
)


class LegacyNormalizerTests(SimpleTestCase):
    def assert_issue(self, expected_code, callable_, *args, **kwargs):
        with self.assertRaises(LegacyNormalizationError) as context:
            callable_(*args, **kwargs)
        self.assertEqual(context.exception.code, expected_code)
        return context.exception

    def test_texto_remove_espacos_e_preserva_acentos_em_nfc(self):
        decomposed = '  Jose\u0301 da Conceição  '

        result = normalize_nullable_text(decomposed)

        self.assertEqual(result, 'José da Conceição')
        self.assertTrue(unicodedata.is_normalized('NFC', result))

    def test_texto_vazio_vira_ausencia(self):
        for value in (None, '', '   '):
            with self.subTest(value=value):
                self.assertIsNone(normalize_nullable_text(value))

    def test_encoding_invalido_gera_issue_sem_expor_bytes(self):
        error = self.assert_issue(
            IssueCode.ENCODING_PROBLEM,
            normalize_nullable_text,
            b'\xff\xfe',
        )
        self.assertNotIn('ff', error.safe_description)

    def test_email_e_normalizado_e_validado(self):
        self.assertEqual(
            normalize_email('  PESSOA@EXAMPLE.COM  '),
            'pessoa@example.com',
        )
        self.assert_issue(IssueCode.INVALID_EMAIL, normalize_email, 'invalido')

    def test_telefone_com_e_sem_ddd(self):
        self.assertEqual(normalize_phone('98888-7777', ddd='61'), '61988887777')
        self.assertEqual(normalize_phone('(61) 98888-7777'), '61988887777')
        self.assertEqual(normalize_phone('8888-7777'), '88887777')
        self.assert_issue(IssueCode.INVALID_PHONE, normalize_phone, 'telefone?')

    def test_cpf_formatado_e_invalido(self):
        self.assertEqual(normalize_cpf('529.982.247-25'), '52998224725')
        self.assertIsNone(normalize_cpf('  '))
        self.assert_issue(IssueCode.INVALID_CPF, normalize_cpf, '111.111.111-11')

    def test_flags_s_n_sao_estritas(self):
        self.assertIs(normalize_sn_flag(' s '), True)
        self.assertIs(normalize_sn_flag('N'), False)
        self.assertIsNone(normalize_sn_flag(''))
        self.assert_issue(
            IssueCode.UNKNOWN_BOOLEAN_VALUE,
            normalize_sn_flag,
            'talvez',
        )

    def test_datas_validas_e_zero_date(self):
        self.assertEqual(normalize_legacy_date('2020-02-29'), date(2020, 2, 29))
        self.assertEqual(
            normalize_legacy_datetime('2020-02-29 12:30:45'),
            datetime(2020, 2, 29, 12, 30, 45),
        )
        self.assert_issue(
            IssueCode.INVALID_DATE,
            normalize_legacy_date,
            '0000-00-00',
        )
        self.assert_issue(
            IssueCode.INVALID_DATE,
            normalize_legacy_date,
            '31/12/2020',
        )

    def test_cep_uf_e_id(self):
        self.assertEqual(normalize_cep('70.000-000'), '70000000')
        self.assertEqual(normalize_uf(' df '), 'DF')
        self.assertEqual(normalize_legacy_id('0012'), 12)
        self.assert_issue(IssueCode.INVALID_CEP, normalize_cep, '123')
        self.assert_issue(IssueCode.INVALID_UF, normalize_uf, 'XX')
        self.assert_issue(IssueCode.INVALID_ID, normalize_legacy_id, '0')

    def test_valores_monetarios_e_decimais_sem_fallback_ambiguo(self):
        self.assertEqual(normalize_legacy_money('1.234,56'), Decimal('1234.56'))
        self.assertEqual(normalize_legacy_money('1234.56'), Decimal('1234.56'))
        self.assertEqual(normalize_legacy_decimal('12.50'), Decimal('12.50'))
        self.assert_issue(IssueCode.INVALID_MONEY, normalize_legacy_money, '1,234')
        self.assert_issue(IssueCode.INVALID_NUMBER, normalize_legacy_decimal, '1,2')

    def test_referencia_de_midia_e_preservada_sem_acesso_a_arquivo(self):
        self.assertEqual(
            normalize_media_reference(' https://legacy.example/foto.jpg '),
            'https://legacy.example/foto.jpg',
        )
        self.assertEqual(normalize_media_reference('fotos/arquivo.jpg'), 'fotos/arquivo.jpg')
        self.assert_issue(
            IssueCode.INVALID_MEDIA_REFERENCE,
            normalize_media_reference,
            '../segredo',
        )
