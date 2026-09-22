# Frontend — Agent Guide

- Aplique primeiro as regras de `../AGENTS.md`.
- Stack: Next.js 16 App Router, React 19, TypeScript, Tailwind e Vitest.
- O browser não acessa Django diretamente; use o BFF e `siaFetch`.
- Nunca entregue JWT ao JavaScript e nunca crie autenticação em
  `localStorage` ou `sessionStorage`.
- Access e refresh permanecem em cookies HttpOnly.
- Capabilities controlam navegação, ações visíveis e contrato solicitado, mas
  não substituem autorização do backend.
- Não confunda summary e full; essa separação é uma fronteira de privacidade.
- Respeite `count`, `next`, `previous` e paginação explícita. Nunca suponha
  que a primeira página contém todo o dataset.
- Criação de Alpinista não envia status ativo; o backend cria como `pendente`.
- Atualização de Alpinista usa `PATCH`.
- Preserve payloads e status DRF, especialmente `400`, `401`, `403` e `404`.
- Não transforme `403` em tentativa de refresh.
- `SIA_APP_ORIGIN` é a única origem canônica configurada.
- Em DevTunnel, use o alias exato configurado; aliases anunciados não são
  automaticamente equivalentes.
- Nunca hardcode URL do tunnel e nunca adicione wildcard amplo a
  `allowedDevOrigins`.
- Não relaxe double-submit nem comparação exata de Origin.
- As imagens protegidas justificam atualmente dois warnings
  `@next/next/no-img-element`; não migre para um otimizador sem preservar o
  envio seguro da sessão.

Comandos usuais:

```bash
npm test
npm run lint
npx tsc --noEmit --incremental false
npm run build
```
