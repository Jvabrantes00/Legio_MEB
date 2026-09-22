# SIA/MEB — Agent Guide

## Projeto

- Sistema de gestão interna do MEB.
- O nome oficial da pessoa no domínio é **Alpinista**.
- Não trate o sistema como um CRUD simples: há histórico, encontros, funções,
  autorização por papel e dados pessoais sensíveis.

## Stack

Backend:

- Python 3.12
- Django 5.2
- Django REST Framework
- PostgreSQL
- SimpleJWT

Frontend:

- Next.js 16 com App Router
- React 19
- TypeScript
- Tailwind CSS
- Vitest

## Estrutura

- `backend/`: API, domínio, autorização, auditoria e camada de legado.
- `frontend/`: interface, BFF, sessão e contratos de apresentação.
- `docs/`: estado, arquitetura e matriz de autorização.

## Estado atual

- Fase 0 em fechamento.
- Etapas 0A a 0H concluídas.
- 0G, integração frontend/API, concluída.
- 0I, limpeza dos débitos técnicos restantes, concluída.
- Próxima etapa: 0J, gate e auditoria final.
- A Fase 1 começa somente depois do gate final da Fase 0.
- Consulte `docs/PROJECT_STATE.md`; não replique o roadmap inteiro aqui.

## Regras críticas

- Autorização é **default deny**.
- Suporte é papel de negócio; superuser Django é bypass técnico separado.
- JWT nunca deve ser lido pelo client.
- O browser acessa Django por meio do BFF do Next.js.
- Access e refresh ficam em cookies HttpOnly.
- CSRF usa double-submit e comparação exata de Origin.
- Nunca relaxe CSRF para acomodar DevTunnel.
- Nunca hardcode URL de DevTunnel.
- `.env` e `.env.local` nunca entram no Git.
- Mídia protegida não pode ser publicada diretamente por `/media`.
- Contratos summary/full são fronteiras de privacidade, não conveniência de UI.
- Semântica HTTP preservada:
  - `400`: validação ou contrato inválido;
  - `401`: não autenticado;
  - `403`: autenticado sem permissão;
  - `404`: recurso ausente ou nested mismatch;
  - `405`: método não permitido.

## Fluxo de trabalho

Antes de qualquer tarefa, execute:

```bash
git status --short
git branch --show-current
git log -1 --oneline
```

- Não faça commit sem solicitação e revisão.
- Preserve mudanças existentes que não pertençam à tarefa.
- Evite `git add .`.
- Evite refatoração ampla fora do escopo.
- Não reabra decisões estabilizadas sem bug reproduzível ou nova evidência.
- Não invente regras de negócio.

## Testes

Backend:

```bash
cd backend
./.venv/bin/python manage.py test --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npx tsc --noEmit --incremental false
npm run build
```

## Documentação

- Arquitetura atual: `docs/ARCHITECTURE.md`.
- Estado, decisões e roadmap: `docs/PROJECT_STATE.md`.
- Autorização implementada: `docs/AUTHORIZATION_MATRIX.md`.
- Regras específicas adicionais: `backend/AGENTS.md` e
  `frontend/AGENTS.md`.

## Regra de contexto

Não faça varredura completa do repositório automaticamente.

Antes de ler muitos arquivos:

1. identifique o escopo da tarefa;
2. consulte somente os documentos relevantes;
3. leia os arquivos diretamente relacionados;
4. amplie a investigação apenas diante de evidência de necessidade.
