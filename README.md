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
