# Arquitetura do SIA/MEB

## Visão geral

```text
Browser
  → Next.js 16 / React 19
    → BFF em /api/auth/* e /api/sia/*
      → Django 5.2 / Django REST Framework
        → PostgreSQL
```

O browser não recebe JWT e não acessa a API Django diretamente. O Next.js é
a fronteira web: mantém a sessão em cookies, aplica CSRF e encaminha apenas
recursos explicitamente permitidos ao backend.

A Fase 0 encerrou esse baseline arquitetural com o gate 0J aprovado. A Fase 1
parte desta arquitetura estabilizada; não a substitui implicitamente durante a
remodelagem de domínio.

## Backend

- O projeto Django fica em `backend/setup`; o domínio atual está em
  `backend/core`.
- A API DRF usa autenticação JWT e permissões default deny.
- `core/roles.py` centraliza os papéis e grupos de capacidades.
- `core/permissions.py` resolve permissões por método/action e restringe
  filtros, busca e ordenação de Alpinistas.
- ViewSets escolhem serializers e querysets summary/full conforme o papel.
- PostgreSQL é o banco do ambiente normal; a suíte usa SQLite em memória por
  `setup/test_settings.py`.
- Operações multi-write devem usar `transaction.atomic`; concorrência de
  estoque deve usar bloqueio apropriado, como `select_for_update`.
- Logs de auditoria armazenam identificadores e descrições operacionais, sem
  substituir logging técnico estruturado.

Os contratos completos estão nos serializers, que usam allowlists explícitas
de campos.

## Frontend e BFF

- O frontend usa Next.js App Router, React e TypeScript.
- `siaFetch` é a camada HTTP do browser e aceita somente caminhos relativos.
- Requisições de negócio passam por `/api/sia/[...path]`.
- O proxy mantém uma allowlist de recursos, bloqueia caminhos/destinos
  arbitrários e preserva status e payloads do DRF.
- Referências paginadas e referências de mídia do backend são reescritas para
  o BFF quando pertencem à origem configurada.
- Capabilities controlam navegação, botões e seleção de contratos; não
  substituem autorização do backend.
- Summary/full é uma fronteira de dados. Ocultar um campo somente na UI não é
  proteção suficiente.

## Autenticação

1. O browser obtém o cookie double-submit em `/api/auth/csrf`.
2. O login é enviado ao BFF em `/api/auth/login`.
3. O BFF solicita o par JWT ao Django.
4. Access e refresh são gravados em cookies HttpOnly; o corpo não entrega os
   tokens ao JavaScript.
5. `/api/auth/me` resolve a identidade mínima e os papéis reconhecidos.
6. Em `401`, o BFF pode rotacionar o refresh e repetir a requisição uma única
   vez.
7. A rotação emite novo par e coloca o refresh anterior na blacklist.
8. Logout revoga o refresh quando possível e limpa cookies de autenticação e
   CSRF.

Um `403` não dispara refresh: ele representa identidade válida sem permissão.
O guard de rotas mantém páginas privadas fechadas quando Django está
indisponível ou a sessão é inválida.

## CSRF e Origin

- Mutações usam double-submit: cookie `sia_csrf` mais header
  `X-CSRF-Token`.
- O BFF exige igualdade entre os tokens e comparação exata do header
  `Origin` com `SIA_APP_ORIGIN`.
- `SIA_APP_ORIGIN` contém somente uma origem HTTP(S), sem caminho,
  credenciais, query ou fragmento.
- HTTP é aceito apenas para hosts locais explícitos; acesso remoto usa HTTPS.
- Em desenvolvimento, `allowedDevOrigins` é derivado do hostname dessa mesma
  origem.
- DevTunnel pode anunciar aliases diferentes. O navegador deve usar o alias
  exato configurado; não se adicionam wildcard nem exceções de CSRF.

## Autorização e privacidade

- A política é default deny e o superuser é um bypass técnico separado dos
  papéis de negócio.
- Requisições anônimas recebem `401`; usuários autenticados sem capacidade
  recebem `403`.
- Nested resources retornam `404` quando o filho não pertence ao pai, evitando
  IDOR e vazamento de existência.
- A matriz normativa atual está em `docs/AUTHORIZATION_MATRIX.md`.

## Mídia protegida

- Fotos de perfil e de Encontro são armazenadas via storage Django.
- Arquivos são entregues somente por actions autenticadas da API.
- O BFF reconhece apenas os dois formatos de path de mídia protegida.
- `/media` não é montado como rota pública no URLconf.
- Ausência de foto é representada por `null`; arquivo ausente retorna `404`.

## Paginação

- O DRF usa paginação por página com tamanho padrão 10.
- São paginados Alpinistas, Encontros, Eventos, Participações de Evento,
  Materiais, Entregas e Logs.
- Os endpoints atuais de Funções e Participações de Encontro retornam listas
  diretas, sem envelope de paginação.
- O frontend deve seguir `next`/`previous` ou carregar páginas explicitamente;
  nunca pode tratar a primeira página como o dataset inteiro.

## Legado

`backend/core/legacy` é uma anti-corruption layer pura:

- não usa ORM;
- não conecta ao MySQL;
- não grava registros;
- não escolhe PKs novas;
- transforma linhas raw em DTOs canônicos, issues e dados em quarentena.

O loader e o crosswalk persistente pertencem a trabalho futuro, depois do
profiling real e da estabilização do domínio.

## Infraestrutura de desenvolvimento

```text
Estação de trabalho
  → SSH / VS Code Remote SSH
    → notebook Ubuntu
      ├── PostgreSQL local
      ├── sia-backend.service
      ├── sia-frontend.service
      └── sia-tunnel.service → DevTunnel HTTPS → browser
```

Configurações locais e URLs do tunnel não pertencem ao Git. O frontend em
desenvolvimento precisa iniciar com `NODE_ENV=development` para aplicar
`allowedDevOrigins` derivado da origem configurada.

## Fronteiras para novas entidades

Novas entidades da Fase 1 devem manter o fluxo Browser → Next/BFF →
Django/DRF → PostgreSQL e respeitar autorização default deny, contratos
summary/full, mídia protegida, atomicidade, migrations incrementais e
compatibilidade explícita. Mudanças nessas fronteiras exigem decisão documentada
e testes antes da implementação.

## Limitações arquiteturais atuais

- A coordenação de refresh em memória funciona por processo; múltiplas
  instâncias exigiriam coordenação compartilhada.
- Banco, storage de arquivos e auditoria não formam uma transação distribuída.
- Falhas externas de storage ainda exigem reconciliação periódica de órfãos.
- A sessão não possui ainda uma política adicional de duração absoluta.
- A camada legada transforma dados, mas ainda não possui loader produtivo.
