# Backend — Agent Guide

- Aplique primeiro as regras de `../AGENTS.md`.
- Stack: Python 3.12, Django 5.2, DRF, PostgreSQL e SimpleJWT.
- O projeto/settings fica em `setup`; domínio, API e legado ficam em `core`.
- Ambiente normal usa `setup/settings.py`; testes usam
  `setup/test_settings.py` e SQLite em memória.
- Não crie migrations sem mudança real de schema e necessidade comprovada.
- Confira migrations com `makemigrations --check --dry-run` antes de propor
  uma nova.
- Serializers de dados sensíveis devem preferir allowlists explícitas; não
  amplie `fields` por conveniência.
- Autorização é default deny. Consulte
  `../docs/AUTHORIZATION_MATRIX.md` antes de alterar permission, policy,
  action ou role.
- Superuser é bypass técnico; Suporte é papel de negócio.
- Preserve `400`, `401`, `403`, `404` e `405` conforme seus significados.
- Use `transaction.atomic` em operações com múltiplas escritas.
- Em concorrência de estoque, use bloqueio transacional apropriado, como
  `select_for_update`.
- Nunca exponha `MEDIA_ROOT` por uma rota pública `/media`.
- Arquivos protegidos devem continuar atrás das actions autenticadas.
- `django.contrib.auth.User` representa identidade; `Alpinista` representa a
  pessoa do domínio. Não misture ou una os dois conceitos.
- `core/legacy` é uma camada pura: sem ORM, conexão MySQL, escrita ou escolha
  de novas PKs.
- Não registre CPF, telefone, e-mail, credenciais, JWT ou conteúdo sensível em
  logs técnicos.

Comandos usuais:

```bash
./.venv/bin/python manage.py test --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
./.venv/bin/python manage.py showmigrations
```
