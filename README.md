# SIA 2.0 — Movimento Escalada de Brasília

Sistema de gestão interna do MEB, com histórico, Encontros, funções,
autorização por papel e dados pessoais sensíveis. A pessoa no domínio é o
Alpinista. Em 24/11/2026, GE-2A, GE-2B-1 e GE-2B-2 estão implementados na
branch de desenvolvimento; a publicação foi verificada pelo ARCH. Não houve
merge na main nem implantação em produção, conforme evidência fornecida.

## Estrutura e tecnologias

- `backend/`: API, domínio, autorização, auditoria e camada de legado `core/legacy`.
- `frontend/`: interface, BFF, sessão e contratos de apresentação.
- `docs/`: arquitetura, estado, autorização e planos.

Python 3.12.3 (`.python-version`), Django 5.2.16, DRF 3.17.1, SimpleJWT
5.5.1, PostgreSQL, Celery 5.6.3, WeasyPrint 70.0 e Pillow. O arquivo
`backend/requirements.txt` é a fonte única das dependências Python. Frontend:
Next.js ^16.3.3, React 19.2.4, TypeScript 5, Tailwind CSS, Vitest 4 e ESLint 9;
`frontend/package-lock.json` fixa a árvore instalada. Node v20.20.2, npm 10.8.2
e PostgreSQL 16.15 foram observados no ambiente; `package.json` não declara
engines.

## Preparação e execução local

Para desenvolvimento com containers, consulte o [guia Docker Compose](docker/README.md).

O caminho padrão com PostgreSQL **não foi executado nesta revisão**. Crie um
ambiente virtual Python 3.12 em `backend/.venv` e instale as dependências, a
partir da raiz:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

Copie `backend/.env.example` para `backend/.env` e preencha os valores locais:
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`,
`POSTGRES_PORT`, `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`, `DJANGO_DEBUG`,
`DJANGO_ALLOWED_HOSTS`, configurações CORS/CSRF e variáveis `SIA_*` e
`CELERY_*` do exemplo. A partir de `backend/`:

```bash
./.venv/bin/python manage.py migrate
SIA_ENVIRONMENT=development SIA_DEMO_PASSWORD='<senha-local>' ./.venv/bin/python manage.py seed_demo
./.venv/bin/python manage.py runserver 127.0.0.1:8000
```

O seed exige `settings.DEBUG` verdadeiro e `SIA_ENVIRONMENT=development`. `settings.DEBUG` vem de `DJANGO_DEBUG` no `backend/.env` (`DJANGO_DEBUG=True`, como no `.env.example`; também valem `1`, `yes` e `on`; sem a variável o padrão é falso e o seed se recusa); veja [dataset de demonstração](docs/workplans/DEV_SEED.md).

A partir de `frontend/`, execute `npm ci`, copie `frontend/.env.example` para
`frontend/.env.local` e configure `SIA_BACKEND_URL` para o backend e
`SIA_APP_ORIGIN` para a origem do browser, sem prefixo `NEXT_PUBLIC_`. Depois:

```bash
npm run dev
```

O CSRF compara a Origin exatamente: use o mesmo host (`127.0.0.1` ou
`localhost`) no browser e em `SIA_APP_ORIGIN`. A mesma regra vale para
DevTunnel; não relaxe o CSRF nem fixe URL de túnel no código.

## Segurança e operação da autenticação

Autorização é default deny; Suporte é papel de negócio e superuser Django é
bypass técnico separado. O browser acessa Django pelo BFF, nunca lê JWT;
access e refresh ficam em cookies HttpOnly. CSRF usa double-submit e Origin
exata. Mídia protegida não é servida por `/media`; summary/full são fronteiras
de privacidade.

Django é a fonte de verdade da sessão. Next.js guarda `sia_access` e
`sia_refresh` em cookies HttpOnly e consulta `/api/auth/me/` no servidor;
não recebe a chave de assinatura nem valida JWT por conta própria. Cada
refresh rotaciona o par, coloca o anterior na blacklist e concede sete dias
ao novo refresh: a sessão é deslizante; limite absoluto exige política futura.
Refreshes simultâneos são coordenados em memória em um processo Next;
escala horizontal exige coordenação compartilhada ou estratégia compatível.
Para conter o crescimento das tabelas de tokens, agende em produção, fora das
requisições, `python manage.py flushexpiredtokens`.

## Validações

Por política, suítes completas e testes PostgreSQL são manuais em checkpoints.
A suíte de regressão com `setup.test_settings` usa SQLite em memória; testes
condicionados a PostgreSQL ou concorrência podem ser pulados. A partir de
`backend/`:

```bash
./.venv/bin/python manage.py test --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

A partir de `frontend/`:

```bash
npm test
npm run lint
npx tsc --noEmit --incremental false
npm run build
```

O ARCH verificou 153/154 verificações HTTP GE-2B-2; a divergência aceita é
auditoria redundante em desalocação idempotente. DEV/QA relataram 1116 testes
backend OK, 75 pulados em SQLite, e 471 testes frontend aprovados; resultados
não reexecutados pelo ARCH. Suíte PostgreSQL completa e build no HEAD atual
permanecem não verificados. Consulte o [handoff](docs/HANDOFF.md).

## Limitações e documentação

A meta aprovada é substituir o legado preservando os dados históricos; a
estratégia de migração ainda não foi homologada. O catálogo real de equipes e
funções não foi aprovado, o novo fluxo de entrega de convites (C5) tem apenas o schema B1 implementado e não está ativado, e há telas operacionais e
ações de trabalho ainda incompletas. Produção, backup e homologação com
usuários reais permanecem pendentes.

- [Roteador da documentação](docs/00_HOME.md)
- [Arquitetura](docs/ARCHITECTURE.md) e [matriz de autorização](docs/AUTHORIZATION_MATRIX.md)
- [Estado do projeto](docs/PROJECT_STATE.md) e [handoff](docs/HANDOFF.md)
- [GE-2 — equipe canônica](docs/workplans/GE_2_EQUIPE_CANONICA.md) e [seed de desenvolvimento](docs/workplans/DEV_SEED.md)
- [Guia geral](AGENTS.md), [backend](backend/AGENTS.md) e [frontend](frontend/AGENTS.md)
