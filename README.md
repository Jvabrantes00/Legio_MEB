# SIA 2.0 — Movimento Escalada de Brasília

## Versões suportadas

- Python 3.12.3
- Node.js: utilize uma versão compatível com o Next.js declarada em
  `frontend/package.json`.

## Backend

`backend/requirements.txt` é a fonte única das dependências Python. Para
preparar o ambiente local:

1. Crie e ative um ambiente virtual com Python 3.12.3.
2. Instale as dependências com `python -m pip install -r backend/requirements.txt`.
3. Copie `backend/.env.example` para `backend/.env` e preencha os valores locais.
4. Execute os comandos Django a partir da pasta `backend`.

O arquivo `.python-version` registra a versão de Python usada pelo projeto.

## Frontend

`frontend/package.json` declara as dependências JavaScript e os scripts do
projeto. `frontend/package-lock.json` fixa a árvore exata instalada. Use
`npm ci` para reproduzir essa árvore e `npm run dev` para iniciar o frontend.

Verificações disponíveis:

- `npm run lint`
- `npx tsc --noEmit --incremental false`
- `npm run build`

## Testes de regressão do backend

A suíte usa um banco SQLite em memória, separado do PostgreSQL local:

`python manage.py test --settings=setup.test_settings`

Alguns testes documentam regressões conhecidas e devem falhar até que as
correções funcionais correspondentes sejam implementadas.

## Operação da autenticação

O Django é a fonte de verdade da sessão. O Next.js guarda `sia_access` e
`sia_refresh` em cookies HttpOnly e consulta `/api/auth/me/` no servidor; ele
não recebe a chave de assinatura e não valida JWT por conta própria.

Cada uso do refresh rotaciona o par: o refresh anterior entra na blacklist e
o novo refresh recebe sete dias a partir daquele momento. Portanto, a sessão
é deslizante enquanto houver atividade. Um limite absoluto de sessão, se
necessário, deverá ser definido em uma política futura.

Refreshes simultâneos são coordenados em memória dentro de um único processo
Next. Antes de escalar horizontalmente para múltiplas instâncias, será
necessária uma coordenação compartilhada ou outra estratégia compatível com
rotação.

As tabelas oficiais de tokens crescem ao longo do uso. Em produção, agende
periodicamente o comando oficial, fora do ciclo de requisição:

`python manage.py flushexpiredtokens`
