# Fase 1B.3D.6 — Calendário Institucional: Encontros

## Status geral

D.6A–D.6E concluídas e D.6F tecnicamente concluída. Projeção, leitura,
comandos, Agenda canônica e frontend personalizado estão implementados.
Aguardando revisão visual humana antes da D.6G.

## Objetivo

Implementar a fatia de Encontros do Calendário Institucional como projeção do
domínio canônico, com consultas, comandos, autorização, frontend
personalizado, PDFs mensal/anual e preservação das versões divulgadas,
conforme o [[../decisions/ADR-001-calendario-institucional|ADR-001]] e
[[../domain/INSTITUTIONAL_CALENDAR|Calendário Institucional]].

## Escopo

- Projeção institucional de `Encontro`, `CalendarioEncontro` e `DiaEncontro`.
- Consultas e API da fatia de Encontros.
- Criação e edição pelo Calendário usando o domínio canônico.
- Autorização de leitura e gestão.
- Avisos consultivos de conflitos.
- Frontend personalizado aprovado em checkpoint humano.
- PDF mensal e anual em linguagem visual de calendário.
- Histórico imutável das versões efetivamente divulgadas.
- Integração, regressão e fechamento.

## Fora de escopo

- Domínio de Eventos ou API simulada de Eventos.
- Compromissos institucionais genéricos.
- Saúde e fonte canônica de atividade.
- Frontend canônico das D.2–D.5.
- Exportação Excel, importação de planilha ou calendário externo.
- Redesenho geral do sistema ou aplicação antecipada de nova paleta.

## Blocos

### D.6A — Auditoria e desenho técnico da projeção

Status: concluída em 2026-10-06.

Auditou models, services, serializers, views, rotas, autorização, frontend,
testes, migrations, private media e dependências. Fechou o desenho da
projeção, comandos expostos, conflitos, exportação e histórico, sem
implementar.

### D.6B — Projeção, consultas e API

Status: concluída em 2026-10-06.

Implementou query service, DTOs imutáveis, serializer allowlist, consulta
inclusiva por período, conflito consultivo, capabilities e índice de data,
sem comandos de escrita nem tabela duplicada de calendário.

### D.6C — Comandos, criação/edição e autorização

Status: concluída em 2026-10-06.

Expôs comandos explícitos de criação, dados básicos, planejamento,
oficialização, reprogramação, adiamento, novo planejamento e cancelamento,
delegando aos services canônicos com auditoria transacional.

### D.6D — Definição de UX/UI

Status: concluída em 2026-10-06.

O checkpoint humano aprovou visões, navegação, criação, Agenda agregada,
identidade, responsividade, filtros e modalidades de PDF. A escolha do modelo
anual definitivo permanece como checkpoint posterior entre dois protótipos.

### D.6E — Suporte backend à Agenda aprovada

Status: concluída em 2026-10-06.

Implementou os deltas técnicos revelados pela D.6D: rótulos públicos,
reuniões preparatórias na projeção/Agenda, avaliação simples, agregação
canônica, visibilidade e contrato heterogêneo, antes do frontend.

### D.6F — Frontend personalizado

Status: tecnicamente concluída em 2026-10-06.

Implementou a especificação visual aprovada na D.6D sobre os contratos
entregues em D.6B–D.6E. A implementação está pronta para revisão visual
humana; eventuais ajustes visuais devem preceder D.6G.

### D.6G — PDF mensal/anual e histórico de divulgação

Status: pendente.

Começará pelo spike dos dois modelos anuais com os mesmos dados e checkpoint
humano antes do renderer anual definitivo. Depois implementará PDFs públicos
e internos, preview, publicação e histórico imutável.

### D.6H — Integração, PostgreSQL, regressão e fechamento

Status: pendente.

Validará integração, migrations, os cinco testes concorrentes preparados na
D.6C, publicação/storage e regressão backend/frontend.

## Resultado da D.6B

### Projeção, período e performance

- `core.services.calendario_institucional` concentra a projeção em DTOs
  imutáveis; views e serializers não reconstruem regras de agenda.
- A consulta recebe `inicio` e `fim` inclusivos, suporta mês, ano e intervalos
  arbitrários e limita a resposta a no máximo 366 datas inclusivas.
- Um Encontro forma um único item com os seus dias pertencentes ao período.
  A ordenação por data, ordem, título, Encontro e dia é determinística.
- A consulta canônica parte de `DiaEncontro.data`, filtra agenda vigente e usa
  `select_related`. O fallback é uma segunda consulta constante; o teste de
  desempenho confirma duas queries, sem N+1.

### Agenda, fallback e conflitos

- Agenda vigente canônica prevalece sempre. `oficializado_em` distingue
  `PROVISORIA` de `OFICIAL`; a projeção usa somente o lifecycle `status`.
- Somente Encontro sem qualquer calendário usa `data_referencia`, com origem
  `LEGADO`, confirmação `INDETERMINADA` e sem interpretar `data_exato`.
- Agenda histórica não vigente não é projetada. Assim, `ADIADO` sem agenda
  atual permanece fora do intervalo, enquanto `CANCELADO` e `FINALIZADO` com
  agenda vigente continuam visíveis com seu status canônico.
- Conflitos são derivados em memória das mesmas ocorrências, agrupam
  Encontros distintos por data e aparecem na coleção global e no dia afetado.
  Não persistem dados, não alteram domínio e não bloqueiam operações.

### API e autorização

- `GET /api/calendario-institucional/?inicio=YYYY-MM-DD&fim=YYYY-MM-DD`
  retorna `periodo`, `itens`, `conflitos` e `capabilities`, sem paginação.
- Serializers explícitos expõem somente identificação, nome, tipo, status,
  agenda, confirmação, dias, conflitos e capabilities. Dados pessoais e
  operacionais permanecem ausentes.
- Formatos inválidos, parâmetros ausentes/extras, intervalo invertido ou
  excessivo retornam `400`; métodos não expostos retornam `405`.
- Todos os papéis reconhecidos e o superuser leem. Usuário autenticado sem
  role recebe `403` e anônimo recebe `401`. A leitura não amplia permissões do
  endpoint de Encontros.
- Capabilities de gestão refletem a política aprovada para Suporte/Diretoria e
  superuser; nenhum comando de escrita foi criado nesta etapa.

### Migration, testes e compatibilidade

- `0035_diaencontro_data_index` adiciona somente o índice B-tree
  `dia_encontro_data_idx` em `DiaEncontro.data`, sem dados, `RunPython` ou
  backfill.
- Foram adicionados 16 testes de projeção, período, agenda/fallback,
  reprogramação, estados, conflitos, query count, contrato, HTTP e roles.
- A suíte backend encerrou com 506 testes aprovados e 14 skips preexistentes.
  `manage.py check` passou; `makemigrations --check --dry-run` retornou
  `No changes detected`, com apenas o aviso esperado de PostgreSQL inacessível
  na sandbox.
- Endpoints e serializers legados não foram alterados. Não houve dual-write,
  backfill, frontend, PDF, publicação nem acesso ao PostgreSQL.

### Arquivos alterados na D.6B

- `backend/core/services/calendario_institucional.py`;
- `backend/core/models.py`;
- `backend/core/roles.py`;
- `backend/core/serializers.py`;
- `backend/core/views.py`;
- `backend/core/urls.py`;
- `backend/core/migrations/0035_diaencontro_data_index.py`;
- `backend/core/tests/test_calendario_institucional.py`;
- `docs/00_HOME.md`;
- `docs/AUTHORIZATION_MATRIX.md`;
- `docs/workplans/PHASE_1B_D6.md`.

## Resultado da D.6C

### Comandos e endpoints

O command viewset em `/api/calendario-institucional/encontros/` expõe apenas:

- `POST /` — criar Encontro com agenda inicial provisória;
- `PATCH /{id}/dados-basicos/` — alterar nome e/ou local;
- `PATCH /{id}/planejamento/` — substituir dias provisórios in-place;
- `POST /{id}/oficializar/` — oficializar a agenda vigente;
- `POST /{id}/reprogramar/` — preservar a versão anterior e criar oficial;
- `POST /{id}/adiar/` — retirar vigência sem inventar novas datas;
- `POST /{id}/iniciar-planejamento/` — criar nova versão provisória;
- `POST /{id}/cancelar/` — cancelar sem remover Encontro ou agenda.

Não há listagem/detalhe duplicado, CRUD de calendário/dia, delete, transições
operacionais de preparação/início/finalização nem comandos de participantes,
equipes, formação ou MME.

### Reutilização, transações e auditoria

- `core.services.comandos_calendario` é uma camada fina de orquestração sobre
  os services temporais de Encontro. Lifecycle, vigência, oficialização,
  versionamento e locks não foram copiados para serializers/views.
- `editar_dados_basicos` foi acrescentado ao service canônico de Encontro e
  aceita somente nome/local sob `select_for_update`.
- Cada endpoint envolve comando e `LogSistema` no mesmo `transaction.atomic`.
  Os logs usam somente o ID do Encontro e a operação; falha de auditoria
  reverte criação e objetos temporais.
- Escritas com dias sincronizam `data_referencia` e uma representação
  determinística em `data_exato` apenas para consumidores legados. A fonte de
  verdade permanece `CalendarioEncontro`/`DiaEncontro`.
- Respostas trazem status, agenda/versão vigente, confirmação, dias e
  `avisos_conflito`; conflitos reutilizam o detector central, incluem legado
  sem calendário, não persistem e nunca bloqueiam o comando.

### Autorização e capabilities

- Suporte, Diretoria e superuser executam todos os comandos. Fichas, MME,
  Formação, Secretaria, Ação Social, Liturgia, Eventos e Comunicação continuam
  somente leitura; usuário sem role e anônimo permanecem negados.
- A projeção agora inclui `pode_gerir_calendario`, derivada da mesma constante
  de roles usada pelo command viewset. As capabilities existentes permanecem
  alinhadas à política aprovada.
- Métodos e campos não expostos retornam `405`/`400`; recurso ausente retorna
  `404`; transições inválidas dos services retornam `400`.

### Compatibilidade e cutover

- Os novos writes usam exclusivamente services e estrutura canônicos; não há
  fallback de escrita, dual-write temporal, backfill ou registro visual.
- O CRUD legado de Encontro foi preservado. Seu payload informa apenas
  `data_referencia` e `data_exato` textual, logo converter múltiplos dias seria
  heurístico e inseguro. Esses registros podem continuar sem agenda e entram
  somente no fallback de leitura D.6B.
- Exclusão e edição direta do endpoint legado permanecem como débito de
  compatibilidade até existir contrato estruturado e plano de cutover. Não
  houve quebra dos consumidores atuais.

### Concorrência, testes e validação

- Os services existentes bloqueiam Encontro e agenda vigente. Edições são
  serializadas; oficialização concorrente rejeita a segunda transição;
  reprogramações preservam versões; edição concorrente com oficialização ou
  cancelamento não produz agenda parcial.
- Cinco testes reais de concorrência foram preparados e condicionados a
  PostgreSQL: edição simultânea, oficialização simultânea, reprogramação
  simultânea, edição versus oficialização e edição versus cancelamento. Sua
  execução fica reservada à D.6H.
- A D.6C adicionou 19 testes, dos quais 14 passaram em SQLite e cinco foram
  corretamente ignorados. A suíte backend total passou com 525 testes e 19
  skips. `manage.py check` passou e `makemigrations --check --dry-run` retornou
  `No changes detected`, com o aviso esperado de PostgreSQL inacessível na
  sandbox.
- Nenhuma migration nova foi necessária. Frontend, PDF, publicação e
  PostgreSQL não foram executados.

### Arquivos alterados na D.6C

- `backend/core/services/encontros.py`;
- `backend/core/services/comandos_calendario.py`;
- `backend/core/services/calendario_institucional.py`;
- `backend/core/serializers.py`;
- `backend/core/views.py`;
- `backend/core/urls.py`;
- `backend/core/tests/test_calendario_institucional_commands.py`;
- `docs/00_HOME.md`;
- `docs/AUTHORIZATION_MATRIX.md`;
- `docs/workplans/PHASE_1B_D6.md`.

## Resultado da D.6E

### Schema e migration expansiva

- `DiaEncontro.rotulo` é um texto curto opcional de até 80 caracteres. O campo
  é independente de `descricao`, não possui choices e não infere valor por
  ordem ou tipo do Encontro.
- `ReuniaoPreparatoriaEncontro.complemento` preserva um subtítulo curto de
  agenda sem expor nem reinterpretar `observacoes`, que continua operacional.
- `AvaliacaoEncontro` é a modelagem mínima aprovada: uma avaliação por
  Encontro, data, timestamps e FK 1:1 com `PROTECT`. Não possui participantes,
  presença, trabalho, frequência ou vínculo com outros módulos.
- O índice `aval_encontro_data_idx` atende a projeção institucional por
  período; a unicidade 1:1 impede duas avaliações para o mesmo Encontro.
- A migration expansiva `0036_expand_agenda_encontro` adiciona os dois campos
  e a nova tabela. Não contém `RunPython`, seed, backfill, remoção ou alteração
  destrutiva. O teste de migration preserva dias, descrições, reuniões e
  observações anteriores com os novos campos vazios.

### Agenda agregada e contrato

- `consultar_agenda_encontro` reúne cronologicamente a agenda vigente do
  Encontro, reuniões reais e avaliação, sem tabela visual, cópia ou
  dual-write. Encontro sem calendário mantém o fallback legado explícito.
- O DTO imutável e allowlisted expõe identificador estável, ID e tipo da fonte,
  data, título, subtítulo opcional, confirmação quando aplicável, indicador
  `publicavel_externamente`, `encontro_id` e conflito consultivo.
- Os tipos são `DIA_ENCONTRO`, `REUNIAO_PREPARATORIA` e `AVALIACAO`. Na mesma
  data, a ordenação técnica determinística usa essa ordem, seguida de título e
  ID da fonte; não depende da ordem casual do banco.
- Dias são publicáveis externamente. Reuniões e avaliação são internas por
  derivação da fonte, sem booleanos redundantes persistidos.
- Rótulo de dia e complemento de reunião entram no DTO; `descricao`,
  `observacoes` e qualquer dado pessoal ou operacional ficam fora.
- `GET /api/calendario-institucional/encontros/{id}/agenda/` fornece a agenda
  canônica para todas as roles de leitura, sem ampliar permissão de gestão.

### Projeção, conflitos e compatibilidade

- O endpoint institucional preserva todos os campos D.6B/D.6C e acrescenta
  `agenda` a cada Encontro e `rotulo` às ocorrências de dia.
- Reunião ou avaliação dentro do intervalo projeta o Encontro mesmo quando
  nenhum dia próprio cai no período. Um Encontro continua sendo um único item
  agregado, com vínculo explícito em todas as ocorrências.
- O detector central considera dias vigentes, reuniões, avaliações e fallback
  legado. Duas fontes do mesmo Encontro na mesma data não geram conflito entre
  si; Encontros distintos geram aviso consultivo, nunca bloqueio.
- O fallback legado e os contratos antigos permanecem. Não houve backfill,
  interpretação de `data_exato`, mudança destrutiva nem remoção de API.

### Comandos, transações e auditoria

- A criação pelo Calendário aceita opcionalmente múltiplas reuniões e uma
  avaliação junto dos dias. Uma transação cria Encontro, calendário, dias,
  reuniões canônicas e avaliação; falha em qualquer fonte reverte tudo.
- Reuniões criadas ou editadas pela Agenda delegam aos services da D.3, com os
  locks e a unicidade de ordem existentes. Presenças permanecem ligadas ao
  mesmo objeto canônico e não são copiadas.
- Avaliação possui services mínimos para criar, editar e remover. Todos
  bloqueiam o Encontro; criação concorrente também depende da unicidade 1:1.
- Os comandos foram expostos como ações semânticas aninhadas do Encontro:
  criar/editar reunião e criar/editar/remover avaliação. Nested mismatch
  retorna `404`; validação de domínio retorna `400`.
- Diretoria, Suporte e superuser técnico gerem esses comandos. As demais roles
  continuam somente leitura. Cada operação administrativa usa `LogSistema`
  dentro da mesma transação e registra apenas IDs e operação.
- Edição e versionamento de dias continuam nos services temporais D.6C;
  rótulos acompanham o payload estruturado sem criar caminho paralelo.

### Testes, validação e concorrência

- Foram acrescentados 14 testes para rótulos, agregação, ordenação na mesma
  data, identificadores, visibilidade, projeção, conflitos, avaliação 1:1,
  integridade referencial, criação completa, rollback, comandos, allowlist,
  autorização, migration e efeitos nulos em participação, trabalho e
  frequência.
- Os testes existentes de Calendário, commands e reuniões preparatórias
  passaram junto dos novos. A suíte backend completa encerrou com 539 testes
  aprovados e 20 skips.
- `manage.py check` passou. `makemigrations --check --dry-run` retornou
  `No changes detected`, além do aviso esperado de PostgreSQL inacessível na
  sandbox.
- Um teste condicional novo cobre duas criações concorrentes da avaliação sob
  PostgreSQL. Com os cinco testes temporais da D.6C, a D.6H passa a ter seis
  cenários concorrentes pendentes de execução real.
- PostgreSQL não foi necessário nesta etapa. Frontend, PDF, renderer,
  publicação e histórico não foram iniciados.

### Débitos e arquivos alterados

- A remoção de reunião não ganhou endpoint: o domínio D.3 não possui comando
  canônico para isso e presenças históricas usam `PROTECT`. Definir essa
  semântica exigiria decisão própria; criação e edição aprovadas estão cobertas.
- Sugestões visuais de rótulo permanecem para a D.6F, sem catálogo ou choices
  persistidos.
- Os débitos legados de `data_referencia`, `data_exato`, `status_encontro` e
  CRUD antigo permanecem inalterados.
- Arquivos alterados: `backend/core/models.py`,
  `backend/core/services/encontros.py`,
  `backend/core/services/reunioes_preparatorias.py`,
  `backend/core/services/avaliacoes_encontro.py`,
  `backend/core/services/calendario_institucional.py`,
  `backend/core/services/comandos_calendario.py`,
  `backend/core/serializers.py`, `backend/core/views.py`,
  `backend/core/urls.py`,
  `backend/core/migrations/0036_expand_agenda_encontro.py`,
  `backend/core/tests/test_calendario_institucional.py`,
  `backend/core/tests/test_calendario_institucional_agenda.py`,
  `docs/00_HOME.md` e `docs/workplans/PHASE_1B_D6.md`.

## Resultado da D.6F

### Rota, navegação e autorização visual

- `/calendario` é a rota canônica no App Router e também integra a navegação
  desktop/mobile. O BFF permite somente a raiz explícita
  `calendario-institucional`; JWT, cookies HttpOnly e CSRF permanecem
  inalterados.
- Todas as roles reconhecidas podem abrir o calendário. Novo compromisso,
  `+` contextual e edição exigem simultaneamente a policy local centralizada e
  a capability real da resposta. Diretoria, Suporte e superuser técnico são os
  únicos gestores; read-only não recebe controles de escrita.
- Eventos e Outros permanecem visíveis e desabilitados. Exportar possui lugar
  reservado, também desabilitado e acessível, sem download ou PDF fictício.

### Mês, ano e identidade

- A entrada usa o mês civil atual na visão mensal. A grade é segunda–domingo,
  mantém 42 células e dias adjacentes esmaecidos, destaca somente o número do
  dia atual e limita cada célula a dois mini-cards antes do `+N` acessível.
- No mobile, a célula usa indicador compacto e a seleção abre a lista completa
  do dia abaixo da grade. O mesmo fluxo de criação recebe a data selecionada.
- A visão anual apresenta 12 mini-calendários em 3 × 4 no desktop amplo, duas
  colunas em largura intermediária e uma no mobile. Mês atual, atividade e
  contagem são indicados sem repetir nomes completos; selecionar um mês volta
  à visão mensal.
- Tokens escopados ao Calendário aplicam a paleta aprovada sem alterar o tema
  global. Mini-cards usam superfície azul leve, detalhe de categoria,
  elevação curta e `prefers-reduced-motion`.
- `EncounterCategoryIcon` é um SVG local próprio, simples e baseado em
  `currentColor`; usa título quando informativo e `aria-hidden` quando
  decorativo. Não cria marca ou catálogo artificial de ícones.

### Drawer, criação, edição e Agenda

- O compromisso abre drawer lateral no desktop e painel de largura total no
  mobile. Ele carrega a Agenda agregada, agrupa Dias do Encontro, Preparação e
  Pós-Encontro, oferece link canônico ao Encontro e expõe edição somente a
  gestores.
- O formulário único cria Encontro e Agenda inicial com múltiplos dias e
  rótulos editáveis, múltiplas preparatórias com horário/local/complemento e
  avaliação opcional. O `+` de um dia usa o mesmo componente e preenche apenas
  a primeira data. Somente as quatro sugestões aprovadas de Escalada existem.
- A edição chama os comandos semânticos canônicos para dados básicos,
  planejamento ou reprogramação, reuniões, avaliação, oficialização,
  adiamento e cancelamento. Não há CRUD direto de models nem lifecycle
  reconstruído no frontend. Avisos de conflito vêm do backend e são
  consultivos.
- A página canônica de Encontro ganhou a seção Agenda para contratos summary e
  full, lendo o endpoint agregado e sem copiar dados para estado persistente.

### Datas, responsividade e acessibilidade

- Utilities de data civil fazem parse, grade, comparação e formatação de
  `YYYY-MM-DD` em UTC controlado, sem usar o parse implícito que desloca o dia
  conforme timezone.
- Controles usam botões/links reais, labels, foco visível, estados
  loading/vazio/erro/retry, comunicação textual da categoria e da
  provisoriedade, Escape, foco inicial/restaurado e contenção de Tab nos dois
  dialogs.
- O shell ganhou navegação compacta para mobile sem alterar os módulos ou o
  conteúdo das páginas existentes.

### Testes e validação

- A suíte frontend passou com 124 testes em 10 arquivos. A cobertura inclui
  datas civis, segunda–domingo, adjacências, hoje, navegação de mês, projeção,
  mini-card e `*`, `+N`, lista do dia, ano com 12 meses, Agenda agrupada,
  payload completo, data contextual, drawer/capabilities, SVG, navegação e
  allowlist do BFF.
- TypeScript passou com `npx tsc --noEmit --incremental false`.
- ESLint passou sem erros e sem avisos novos. Permanecem somente os dois avisos
  preexistentes e documentados de `<img>` protegido na tela de Alpinistas.
- O build Next de produção passou com Webpack, incluindo a geração de
  `/calendario` e das 11 rotas. O Turbopack padrão não pôde abrir sua porta de
  processo auxiliar neste ambiente (`Operation not permitted`); não houve
  erro de código e nenhuma configuração foi alterada para contornar a
  proteção do host.
- Backend, schema, migrations, PostgreSQL, PDF e publicação não foram tocados.

### Refinamento visual pós-revisão humana

- O drawer recebeu largura útil moderadamente maior, mais espaçamento e grid
  responsivo por largura disponível, evitando compressão das seções e dos
  itens da Agenda em desktop, tablet e mobile.
- No contexto de preparação de Encontros, a nomenclatura visível foi ajustada
  de Reunião para Preparatória. Identificadores técnicos, payloads e contratos
  permanecem inalterados.
- Dias do Encontro não repetem mais o nome já contextualizado no topo do
  drawer. Complementos informativos das preparatórias permanecem visíveis.
- A ordenação continua estritamente cronológica pelas datas canônicas e ganhou
  cobertura explícita contra ordenação pelo rótulo ou número da preparatória.

### Débitos e arquivos alterados

- A validação visual definitiva continua humana. Ajustes de densidade,
  tipografia ou comportamento em dispositivos reais podem ser feitos antes da
  D.6G sem reabrir as decisões de produto congeladas.
- PDF, preview, publicação e histórico continuam integralmente na D.6G;
  Eventos e Outros permanecem expansões futuras sem dados simulados.
- Arquivos novos: `frontend/src/app/(painel)/calendario/page.tsx`,
  `frontend/src/components/CalendarEncounterDrawer.tsx`,
  `frontend/src/components/CalendarEncounterEditor.tsx`,
  `frontend/src/components/CalendarEncounterForm.tsx`,
  `frontend/src/components/EncounterAgendaSection.tsx`,
  `frontend/src/components/InstitutionalCalendarHeader.tsx`,
  `frontend/src/components/InstitutionalCalendarViews.tsx`,
  `frontend/src/components/icons/EncounterCategoryIcon.tsx`,
  `frontend/src/lib/dialog-focus.ts`,
  `frontend/src/lib/institutional-calendar.ts` e seu teste.
- Arquivos ajustados: página canônica de Encontro, layout, Sidebar, estilos
  globais escopados, proxy/BFF, capabilities, navegação e testes associados,
  além deste workplan e do roteador `docs/00_HOME.md`.

Implementação pronta para revisão visual humana.

Aguardando revisão visual humana antes da D.6G.

## Decisões da fase

- O ADR-001 permanece a decisão arquitetural principal e não será duplicado.
- A D.6 implementa somente a categoria `ENCONTRO` e preserva extensibilidade
  futura para Eventos e compromissos.
- SIA é a única fonte de verdade; PDFs são artefatos de divulgação.
- Agenda vigente e agenda oficial não são sinônimos.
- Lifecycle é manual e a interface nova não usará `status_encontro` como
  status administrativo.
- Conflitos produzem avisos, não bloqueios automáticos.
- Diretoria e Suporte gerem pelo Calendário; todas as roles funcionais leem;
  superuser permanece bypass técnico.
- PDFs mensal/anual usam linguagem de grade de calendário. Data provisória
  recebe `*` e legenda.
- PDFs possuem modalidades pública e interna, sem ampliar acesso a dados
  pessoais ou sensíveis.
- Publicações efetivas são históricas e não podem ser sobrescritas.
- D.6E concluiu o gate técnico da Agenda; o frontend D.6F pode consumir o
  contrato canônico aprovado.
- O renderer anual depende de checkpoint humano entre os modelos A e B na
  D.6G.

## Descobertas técnicas da D.6A — baseline auditado

### Models e semântica temporal real

- `Encontro` possui lifecycle completo em `status`, mas conserva obrigatórios
  `data_referencia` e `data_exato`. Esses dois campos continuam sendo a fonte
  do contrato legado, dashboard e frontend atual.
- `CalendarioEncontro` guarda `versao`, `vigente`, `oficializado_em`,
  `criado_em` e `substituido_em`. Há unicidade de versão por Encontro e
  unicidade parcial de uma agenda vigente por Encontro.
- `vigente=True` significa agenda atualmente selecionada. Oficialidade deriva
  exclusivamente de `oficializado_em` não nulo; os dois conceitos não são
  equivalentes no código.
- `DiaEncontro` preserva ordem, data e descrição. Constraints garantem ordem
  positiva e impedem ordem ou data repetida dentro da mesma agenda. Não há
  limite, continuidade ou exigência de dias consecutivos.
- As FKs de agenda e dias usam `CASCADE`, coerente com a dependência do
  Encontro, mas a API nova não deverá oferecer exclusão do calendário como
  operação normal.
- Na auditoria D.6A não existia índice iniciado por `DiaEncontro.data`; a
  migration `0035` o adicionou na D.6B para as buscas globais por intervalo.
- Não existem constraints SQL cruzando status do Encontro, vigência e
  oficialização. Essas invariantes são corretamente mantidas pelos services,
  pois dependem de objetos relacionados e transições.

### Services existentes

- `criar_encontro_com_agenda` cria atomicamente Encontro em
  `EM_AGENDAMENTO`, agenda v1 vigente e dias.
- `editar_planejamento` substitui os dias na mesma agenda vigente ainda não
  oficial, somente em `EM_AGENDAMENTO`.
- `oficializar_agenda` marca a agenda vigente e muda o Encontro para
  `AGENDADO`.
- `reprogramar_agenda` preserva a agenda oficial anterior, cria nova versão
  oficial vigente e aceita Encontro `AGENDADO` ou `ADIADO`.
- `adiar_encontro` torna a agenda oficial histórica e deixa o Encontro sem
  agenda vigente. `iniciar_novo_planejamento` cria uma nova versão provisória;
  a reprogramação direta cria uma nova versão oficial.
- Preparação, início, finalização e cancelamento são transições manuais.
  Cancelamento preserva agenda e dias existentes.
- Todos os comandos usam `transaction.atomic`; alterações bloqueiam o
  Encontro e, quando aplicável, a agenda vigente com `select_for_update`.
- Os services não geram `LogSistema`; hoje a auditoria existe apenas nos
  wrappers da API legada e não cobre os comandos temporais porque eles ainda
  não estão expostos.

### API, autorização e frontend atuais

- Não existe serializer, endpoint, rota ou capability para
  `CalendarioEncontro`, `DiaEncontro`, projeção institucional, conflito ou
  publicação.
- `EncontroViewSet` é CRUD genérico e grava diretamente pelo
  `ModelSerializer`; portanto criação e edição atuais não usam os services
  temporais nem criam agenda canônica.
- O serializer legado limita escrita de status a `EM_AGENDAMENTO` e
  `AGENDADO`, expõe `status_encontro` calculado pela passagem da data e mantém
  `data_referencia`/`data_exato`. Registros sem `CalendarioEncontro` continuam
  explicitamente válidos.
- A matriz atual de Encontros permite leitura apenas a Suporte, Diretoria,
  Fichas e Comunicação e escrita também a Fichas. A política futura do
  Calendário já está documentada separadamente: todas as roles reconhecidas
  leem; apenas Suporte e Diretoria escrevem; superuser é bypass.
- O frontend possui lista paginada, criação e detalhe de Encontros. Ele usa
  somente os campos legados, oferece apenas dois statuses e ainda permite
  exclusão. Não há rota, componente, contrato ou navegação de Calendário.
- Dashboard, históricos e outros serializers ainda ordenam ou apresentam
  `data_referencia`. A D.6 não deve alterá-los incidentalmente.

### Testes, migration e arquivos

- `test_nucleo_encontros.py` cobre criação, dias não consecutivos,
  constraints, planejamento in-place, oficialização, reprogramação,
  adiamento, novo planejamento, lifecycle, cancelamento, atomicidade e
  compatibilidade de serializer.
- Não há testes de projeção por período, conflitos, autorização do
  Calendário, PDF ou publicação.
- A estrutura temporal nasceu em `0028_nucleo_encontros`; a migration mais
  recente do projeto é `0035_diaencontro_data_index`.
- Não há arquivo Excel/PDF de calendário no repositório nem biblioteca de
  geração de PDF instalada como dependência direta.

### Agenda exibida pela projeção

- A agenda canônica exibida é sempre a vigente. `oficializado_em is null`
  produz `PROVISORIA`; valor preenchido produz `OFICIAL`.
- `EM_AGENDAMENTO` projeta a agenda vigente provisória. `AGENDADO`,
  `EM_PREPARACAO`, `EM_ANDAMENTO` e `FINALIZADO` projetam a agenda oficial
  vigente.
- `CANCELADO` conserva e projeta sua agenda vigente com status cancelado; o
  frontend decidirá a apresentação acessível na D.6D.
- `ADIADO` sem novo planejamento não possui agenda vigente e, portanto, não
  gera ocorrência datada na consulta corrente. As datas oficiais anteriores
  permanecem históricas, não atuais. Ao iniciar planejamento ou reprogramar,
  a nova versão volta a alimentar a projeção.
- Registros legados sem agenda serão incluídos por fallback somente leitura em
  `data_referencia`, marcados como origem `LEGADO` e confirmação
  `INDETERMINADA`. Eles não serão apresentados falsamente como provisórios ou
  oficiais, nem receberão backfill automático.

## Compatibilidade com legado

- A projeção nova usa `status`; `status_encontro` continua isolado no contrato
  antigo e não participa das regras do Calendário.
- `data_referencia` permanece fallback explícito para Encontros sem agenda e
  continua atendendo os consumidores legados. `data_exato` não será
  interpretado para inventar dias estruturados.
- A D.6B é aditiva: novo endpoint e novo contrato, sem mudar lista/detalhe
  atuais. Não haverá tabela de item visual, dual-write ou backfill heurístico.
- Na D.6C, escritas originadas no Calendário passam apenas pelos services
  temporais. A criação legada atual continuará compatível; seu futuro cutover
  para dias estruturados exige aceitar o novo contrato sem tentar analisar
  `data_exato`.
- O model `Evento` e sua API legada existem, mas não serão conectados,
  remodelados ou simulados nesta fase.

## API e projeção

### Camadas propostas

- Criar um query service dedicado, por exemplo
  `core/services/calendario_institucional.py`, responsável por intervalo,
  seleção da agenda, fallback legado, ordenação e conflitos.
- O service retorna DTOs imutáveis internos; não retorna models diretamente e
  não conhece formato visual. Um provider de Encontros produz itens com
  `categoria='ENCONTRO'`. Providers futuros poderão ser compostos sem model
  genérico ou relação polimórfica antecipada.
- Um serializer DRF allowlist transforma os DTOs no contrato público. A view
  permanece fina e aplica autenticação, roles, validação de query params e
  capabilities.
- O endpoint de leitura recomendado é
  `GET /api/calendario-institucional/?inicio=YYYY-MM-DD&fim=YYYY-MM-DD`.
  Datas são inclusivas, `inicio <= fim` e o intervalo máximo é um ano civil
  completo. Mês e ano são apenas intervalos, não endpoints duplicados.
- Não há paginação: ela quebraria a completude mensal/anual. O limite de
  intervalo controla custo e respostas.

### Contrato mínimo de leitura

Cada item expõe:

- `categoria`, fixada em `ENCONTRO` nesta fase;
- `encontro_id`, `titulo`, `tipo` e `status` canônico;
- identificação/versão da agenda quando canônica;
- `origem_agenda`: `CANONICA` ou `LEGADO`;
- `confirmacao`: `PROVISORIA`, `OFICIAL` ou `INDETERMINADA` no fallback;
- ocorrências no intervalo, cada uma com ID quando canônica, data e ordem;
- indicador estruturado de conflito por data;
- ID suficiente para navegar ao Encontro;
- capability por item `pode_editar_calendario`.

A resposta também traz `periodo` e capabilities globais
`pode_criar_encontro` e `pode_publicar`. Ela não inclui participantes,
equipes, saúde, observações privadas ou contrato full de Encontro.

### Consulta eficiente e ordenação

- A consulta canônica parte de `DiaEncontro` no intervalo, filtra
  `calendario__vigente=True` e usa `select_related` para agenda e Encontro.
  Assim um Encontro entra se possuir ao menos um dia vigente dentro do
  intervalo e cada ocorrência é lida uma vez, sem N+1.
- O fallback consulta apenas Encontros sem qualquer agenda e com
  `data_referencia` dentro do intervalo.
- Um Encontro aparece uma vez no agrupamento, com todas as suas ocorrências
  pertencentes ao período solicitado. Dias fora do intervalo não contaminam
  a grade mensal/anual.
- A ordenação é determinística por data, ordem, título, `encontro_id` e ID do
  dia. Múltiplos Encontros no mesmo dia permanecem itens distintos.

### Conflitos consultivos

- O cálculo vive no mesmo query service, agrupando ocorrências por data e
  retornando conflito quando houver dois ou mais Encontros distintos.
- O resultado mínimo contém data, IDs envolvidos e quantidade. Não persiste
  entidade, severidade, aprovação ou resolução.
- A consulta de período calcula conflitos automaticamente. Antes de criar,
  editar dias ou reprogramar, D.6C reutilizará uma função de avaliação com
  dias propostos e exclusão do próprio Encontro.
- O comando nunca é bloqueado por sobreposição. A API devolve avisos
  estruturados para o frontend, sem recalcular regra em TypeScript.

## Criação, edição e autorização

### Comandos do contexto de Calendário

D.6C deve expor endpoints de comando próprios, sem update/delete genérico:

- criar Encontro com agenda inicial;
- editar nome e local, os metadados adequados à agenda institucional;
- editar dias do planejamento provisório;
- oficializar agenda;
- reprogramar agenda oficial;
- adiar;
- iniciar novo planejamento após adiamento;
- cancelar.

Mudar tipo depois da criação, iniciar preparação, iniciar o Encontro,
finalizar, excluir, gerir participantes/equipes ou outras operações detalhadas
continuam fora da interface de Calendário. Isso evita duplicar o módulo de
Encontros.

### Composição transacional

- A criação delega a `criar_encontro_com_agenda`; não cria um segundo fluxo
  de domínio. O command serializer recebe nome, tipo, local e dias.
- Para escritas novas, `data_referencia` será sincronizada com a menor data
  estruturada e `data_exato` será uma representação compatível derivada dos
  dias, sem se tornar fonte de verdade.
- Edição temporal delega a `editar_planejamento`, `oficializar_agenda`,
  `reprogramar_agenda`, `adiar_encontro`, `iniciar_novo_planejamento` e
  `cancelar_encontro`. Nome/local precisam de um service canônico pequeno que
  bloqueie o Encontro e não aceite status ou campos extras.
- O wrapper da API envolve service e `LogSistema` na mesma transação, audita
  IDs, operação e avisos de conflito, sem dados pessoais. Falha na auditoria
  reverte a escrita.
- Validação ou transição inválida retorna `400`; falta de sessão `401`;
  papel insuficiente `403`; recurso/nested mismatch `404`; método ausente
  `405`.

### Política de acesso

- Criar `INSTITUTIONAL_CALENDAR_READ_ROLES = RECOGNIZED_ROLES` e
  `INSTITUTIONAL_CALENDAR_MANAGEMENT_ROLES = FULL_ADMIN_ROLES` ou equivalentes
  explícitos.
- Consulta de projeção: todas as roles funcionais; geração/publicação e
  comandos: Suporte e Diretoria; superuser permanece bypass técnico.
- Usuário autenticado sem role e usuário anônimo continuam negados por
  default. A matriz implementada só deve ser atualizada com endpoints e testes
  da D.6B/D.6C.
- Capabilities no contrato orientam o frontend, mas não substituem
  `HasAnySiaRole` no backend nem ampliam acesso ao detalhe do Encontro.

## UX/UI aprovado

D.6D foi concluída por decisão humana. Não há visão Lista como modo principal.

### Visões e navegação

- A entrada padrão é o mês atual. O cabeçalho oferece mês anterior, próximo
  mês, `Hoje` e alternância `Mês | Ano`.
- A visão mensal usa grade tradicional de segunda a domingo, número no canto
  superior, itens centralizados e dias adjacentes esmaecidos. O dia atual
  destaca somente o número em pequeno círculo azul.
- A visão anual mostra 12 meses em grade 3 × 4. Alternar Mês → Ano comunica
  zoom out; clicar em um mês comunica expansão para a visão mensal.
- O mês atual recebe borda/sombra discreta. Dias ocupados têm indicador e o
  mês pode mostrar contagem discreta, sem listar todos os nomes completos.

### Identidade, ícones e cards

- A personalidade é jovem, moderna e institucional, sem aparência corporativa
  rígida ou categorias baseadas em cores aleatórias.
- Paleta de referência: `#001C38`, `#005EE9`, `#FD1E2E`, `#FFFFFF`,
  `#F6FAFD`, `#EAF1F7` e `#DCE4EC`. Encontro começa com identidade
  `#005EE9`, sempre acompanhada de texto/ícone/forma acessível; `#FD1E2E`
  fica reservado a comunicação semântica forte ou destrutiva.
- A identidade principal usa uma família pequena de SVGs locais próprios do
  SIA, com traço e proporção coerentes, e não ícones genéricos de bibliotecas
  como identidade de categoria. A D.6F cria inicialmente apenas o ícone de
  Encontro; Eventos/Outros recebem ícones quando seus módulos surgirem.
- Dentro da célula, o item é mini-card leve: cantos arredondados, fundo azul
  suave, detalhe `#005EE9`, texto centralizado e rótulo complementar discreto.
  Bloco totalmente azul não é o padrão. No desktop, hover eleva cerca de
  2–3 px e reforça suavemente a sombra.
- Data provisória acrescenta `*` ao nome e usa a legenda
  `* Data ainda sujeita a confirmação.`; data oficial não exibe texto extra.
- Quando faltar espaço, a célula limita itens e mostra `+N`, que abre os
  compromissos restantes sem aumentar indefinidamente sua altura.

### Drawer e navegação ao domínio

- Clicar no compromisso abre drawer lateral enxuto com nome, categoria/tipo,
  dias e respectivos rótulos.
- Status operacional como `EM_PREPARACAO` não vira bloco principal apenas por
  existir no domínio.
- Gestores veem a ação discreta `Editar calendário`. A ação principal para
  todos os autorizados é `Abrir Encontro completo`, apontando à página
  canônica para participantes, equipes, formação, MME e demais operações.
- O Calendário não replica o módulo completo de Encontros.

### Criação e edição

- Diretoria, Suporte e superuser veem `Novo compromisso` e um `+` contextual
  por dia; demais papéis não veem ações de criação.
- O `+` preenche a data selecionada, mas permite acrescentar outras datas. O
  comando cria um único Encontro com toda a agenda inicial.
- No mobile, o `+` aparece depois da seleção do dia, pois não há hover.

### Filtros, cabeçalho e mobile

- Filtros visíveis: `Todos`, `Encontros`, `Eventos`, `Outros`. Nesta fase,
  Todos e Encontros estão ativos; Eventos e Outros aparecem desabilitados.
- Não existem filtros de confirmado, a confirmar, adiado ou cancelado.
- O cabeçalho reúne título, período/navegação, Hoje, Mês/Ano, filtros,
  `Exportar` e `Novo compromisso`; as duas ações aparecem somente para
  gestores.
- Desktop/tablet preservam a grade completa. No mobile, o mês é adaptado e a
  seleção de um dia mostra abaixo uma lista legível dos seus compromissos.

## Agenda do Encontro aprovada

A Agenda exibida cronologicamente reúne sem duplicação:

- **Dias do Encontro:** `DiaEncontro` com rótulo público curto/editável, como
  `Pré-Escalada`, `Sexta-feira`, `Sábado` ou `Domingo`;
- **Preparação:** `ReuniaoPreparatoriaEncontro` real, preservando presença e
  regras da D.3;
- **Pós-Encontro:** item simples `Avaliação`, vinculado ao Encontro.

Sugestões de rótulo por tipo são editáveis, não obrigatórias e nunca inferidas
automaticamente pelo índice da data. Reuniões podem receber complemento de
agenda, como `Missa de Entrega`, sem criar novo tipo de compromisso. A criação
inicial pode incluir reuniões preparatórias junto com os dias.

A futura página canônica do Encontro terá uma seção `Agenda` com as mesmas
fontes. `Editar calendário` modifica os objetos reais, de modo que página e
Calendário refletem automaticamente a mesma informação.

## Deltas técnicos entregues na D.6E

A D.6E fechou no backend os pontos que bloqueavam o frontend:

- confirmar/adaptar o suporte de `DiaEncontro` ao rótulo público editável;
- projetar `ReuniaoPreparatoriaEncontro` no Calendário;
- criar/editar reuniões reais através da Agenda, inclusive na criação inicial;
- suportar complemento de agenda da reunião quando o model atual não bastar;
- modelar expansivamente o item simples `Avaliação` vinculado ao Encontro;
- criar query/DTO da Agenda agregada para Calendário e página do Encontro;
- representar itens heterogêneos sem duplicar os domínios de origem;
- distinguir, onde apropriado, conteúdo `PUBLICÁVEL` e `INTERNO`;
- ampliar comandos, autorização, auditoria, conflitos e testes apenas na
  medida necessária a essas fontes.

Não serão criados item visual genérico, sincronização entre cópias ou outros
tipos genéricos de compromisso nesta fase.

## Exportação PDF

### Modalidades e conteúdo

- **Público Mensal** e **Público Anual:** somente itens publicáveis
  externamente, inicialmente dias dos Encontros. Excluem reuniões
  preparatórias, avaliação interna, pessoas, equipes, presença e operação.
- **Interno Mensal** e **Interno Anual:** podem incluir dias, reuniões e
  avaliação. Recebem `USO INTERNO`, mas continuam sem dados pessoais ou
  sensíveis por padrão.
- Não existe Excel. PDF é saída de divulgação e nunca fonte de edição.
- A decisão publicável/interno pertence ao item/domínio apropriado; o renderer
  não será acoplado a uma lista fixa de classes.

### Composição mensal

- A4 paisagem, digital-first, grade de segunda a domingo e itens
  centralizados.
- Cabeçalho jovem/institucional e logo real do movimento/paróquia no canto
  superior direito.
- Provisório usa `*` e legenda. O interno também identifica `USO INTERNO`.

### Composição anual e checkpoint

- Digital-first, com A4 paisagem como ponto inicial e 12 meses em 3 × 4.
- **Modelo A:** mini-calendários com nomes curtos nas datas e
  legenda/overflow quando necessário.
- **Modelo B:** mini-calendários mais limpos, datas destacadas e lista curta
  abaixo de cada mês.
- A D.6G começa com os dois protótipos usando exatamente os mesmos dados. Um
  checkpoint humano escolhe o modelo antes do renderer anual oficial; nenhuma
  escolha automática foi feita na D.6D.

### Snapshot publicável

O renderer receberá um snapshot já allowlisted, nunca QuerySets ou models. O
snapshot possui versão de schema, período, instante de captura, legenda de
provisoriedade e somente ocorrências publicáveis com categoria, ID de origem,
nome, status, datas e indicador provisório. Participantes, equipes, dados
pessoais, saúde, observações internas e capabilities não entram.

### Renderer recomendado

- Gerar no backend a partir de template HTML/CSS de impressão e converter com
  WeasyPrint ou mecanismo equivalente aprovado em spike técnico na D.6G.
- Essa abordagem oferece melhor manutenção de grade, tipografia, quebra de
  página e composição anual que desenho manual de PDF.
- ReportLab exigiria layout de baixo nível; browser/Playwright adicionaria
  runtime Chromium e superfície operacional maior. Nenhuma das bibliotecas
  está instalada diretamente hoje.
- D.6G deverá fixar a dependência escolhida, validar bibliotecas de sistema no
  servidor e impedir busca de recursos remotos. Templates escapam títulos e
  usam apenas assets/fontes locais controlados.
- O renderer mensal segue a decisão aprovada; o anual aguarda a escolha entre
  os dois protótipos.

### Preview e publicação

- Recomenda-se preview transitório, sem registro oficial e com descarte
  imediato do arquivo temporário.
- Publicar é comando explícito: captura um snapshot novo, renderiza, calcula
  hash e persiste a versão imutável. Somente essa operação compõe o histórico.
- A UX exata de preview/publicar será definida no spike, preservando essa
  separação.
- A implementação precisa da logo real do movimento/paróquia, preferencialmente
  SVG ou PNG em boa resolução. Não haverá placeholder como artefato final.
- Toda versão publicada usa rodapé discreto
  `Gerado pelo SIA • Versão publicada em DD/MM/AAAA`; a modalidade interna
  também traz `USO INTERNO`.

## Histórico de divulgação

### Alternativas avaliadas

- Somente PDF preserva o artefato exato, mas dificulta consulta, auditoria do
  conteúdo e eventual geração em outro formato.
- Somente snapshot permite consulta e regeneração, mas não prova os mesmos
  bytes divulgados quando renderer, fontes ou template mudarem.
- **PDF + snapshot estruturado** preserva o material exato e a semântica que o
  originou. O custo de armazenamento é pequeno para calendários e justificado
  por fidelidade histórica, auditoria e backup. Esta é a arquitetura aprovada
  tecnicamente para D.6G.

### Model proposto

`PublicacaoCalendarioInstitucional`, sem FK para Encontro individual:

- `id`;
- `tipo`: `MENSAL` ou `ANUAL`;
- `ano` e `mes` opcional, obrigatório apenas para mensal;
- `publicado_em`;
- `publicado_por`, FK para `User` com `PROTECT` para preservar autoria;
- `snapshot_schema_version`;
- `snapshot`, `JSONField` allowlisted e sem dados pessoais;
- `arquivo_pdf`, `FileField` em storage privado;
- `sha256`, 64 caracteres hexadecimais.

Não há unicidade por período: republicações legítimas coexistem. A ordem
histórica usa `publicado_em` e PK, evitando numeração concorrente artificial.
Checks locais garantem mês 1–12 para mensal e mês nulo para anual. Índice por
`tipo`, `ano`, `mes` e `publicado_em` atende listagem histórica.

A publicação é imutável por service e contrato: API oferece criar, listar,
recuperar e baixar, sem PATCH, PUT ou DELETE. Não existe cleanup automático de
material publicado; eventual retenção exigirá política explícita.

### Consistência da captura

- O comando captura em transação os Encontros e agendas relevantes em ordem
  determinística, compatível com os locks dos services temporais, e produz um
  DTO imutável em memória.
- PDF e JSON são gerados do mesmo DTO. Mudanças canônicas posteriores não
  alteram a publicação.
- Persistência do arquivo e da linha usa compensação: falha de banco remove o
  novo arquivo; falha de storage não cria publicação parcial.
- O hash SHA-256 é calculado sobre os bytes armazenados e verificado no
  download/testes de integridade.

## Segurança e armazenamento

- O projeto usa `MEDIA_ROOT` local e `FileField`/`ImageField`, mas não publica
  `/media`. Downloads existentes passam por `FileResponse` autenticado e
  validam o objeto pai, padrão que deve ser reutilizado.
- PDFs ficam sob path lógico como
  `calendarios/divulgacoes/{ano}/{tipo}/{id}.pdf`; nomes não contêm dados
  pessoais nem texto fornecido pelo usuário.
- Download recebe ID da publicação, nunca path arbitrário, e devolve
  `application/pdf` como attachment. Não haverá URL pública permanente.
- Preview usa arquivo temporário fora do media persistente e o remove mesmo
  em erro. Publicação persistida é somente leitura.
- Backup precisa abranger banco e media privada; o snapshot permite auditar
  conteúdo, mas não substitui backup do PDF exato.
- O snapshot proposto não possui dados pessoais, reduzindo exposição LGPD.
  A inclusão futura de qualquer novo campo deverá passar por allowlist.

## Migrations previstas

- **D.6B:** concluída com a migration aditiva `0035`, que criou o índice
  B-tree em `DiaEncontro.data`.
- **D.6C:** concluída sem mudança de schema.
- **D.6E:** concluída com `0036_expand_agenda_encontro`, que adiciona rótulo de
  dia, complemento de reunião, avaliação 1:1 e seu índice de data, sem
  `RunPython` ou backfill.
- **D.6G:** migration expansiva para `PublicacaoCalendarioInstitucional`,
  checks de tipo/período, índice histórico, FK protegida, snapshot e arquivo.
- A migration atual mais recente é `0036_expand_agenda_encontro`. As
  próximas devem confirmar novamente a folha da cadeia antes de receber número.
- Não haverá `RunPython`, seed, backfill ou alteração destrutiva.

## Testes e validações

### D.6B — projeção e conflitos

- um dia, múltiplos dias e dias não consecutivos;
- intervalos mensal, arbitrário e anual, limites inclusivos e intervalo
  inválido/excessivo;
- Encontro incluído quando ao menos um dia está no período;
- agenda provisória, oficial, reprogramada, cancelada, finalizada e adiamento
  sem agenda vigente;
- fallback legado `INDETERMINADA`, sem interpretar `data_exato`;
- múltiplos Encontros no mesmo dia, conflito estruturado e aviso não
  bloqueante;
- ordenação determinística, ausência de N+1 e lista anual não paginada;
- leitura por todas as roles, superuser, `401`, default deny e allowlist.

### D.6C — comandos

- criação atômica do Encontro/agenda/dias e rollback de auditoria;
- edição de nome/local, planejamento, oficialização, reprogramação,
  adiamento, novo planejamento e cancelamento;
- conflitos retornados sem bloquear e sem duplicar regra no frontend;
- escrita por Diretoria/Suporte/superuser, negação para todas as demais
  roles, campos extras, nested mismatch e métodos não expostos;
- `data_referencia`/`data_exato` compatíveis sem se tornarem fonte canônica;
- nenhuma gestão de participantes, equipes, saúde ou Eventos.

### D.6E — suporte backend à Agenda

- rótulos públicos editáveis sem inferência obrigatória;
- projeção e comandos de reuniões reais, preservando presença e autorização;
- avaliação simples vinculada, sem confusão com outros domínios;
- agregação cronológica e itens heterogêneos sem N+1 ou cópia visual;
- visibilidade publicável/interna, allowlists, conflitos e auditoria;
- criação inicial atômica com dias e reuniões, rollback e compatibilidade.

### D.6F — frontend

- capabilities e navegação para todas as roles sem ampliar comandos;
- comportamento responsivo e acessível definido pela D.6D;
- visões mensal/anual, zoom conceitual, drawer, `+N`, criação multiday,
  filtros ativos/desabilitados e lista mobile;
- SVG próprio de Encontro, tokens da paleta e comunicação não dependente só
  de cor;
- Agenda na página canônica do Encontro lendo as mesmas fontes.

### D.6G — PDF e histórico

- snapshots mensal/anual, data provisória com marcador e ausência de campos
  privados;
- separação público/interno e marca `USO INTERNO`;
- protótipos anuais A/B com os mesmos dados e checkpoint humano;
- preview transitório, publicação imutável, duas publicações do mesmo período
  coexistindo e PDF antigo preservado após mudança canônica;
- hash, download autenticado, IDOR, content type, filename seguro, falhas de
  storage/banco e cleanup compensatório;
- renderer mensal/anual com fixtures determinísticos e testes de estrutura;
  validação visual segue o design aprovado, sem depender apenas de snapshot
  binário frágil.

### D.6H — PostgreSQL e regressão

- cinco cenários concorrentes de comandos preparados na D.6C e um cenário de
  criação concorrente da avaliação preparado na D.6E;
- publicações simultâneas não se sobrescrevem;
- alteração/reprogramação durante captura não produz snapshot misto;
- locks e constraints preservam versões temporais e publicações consistentes;
- migrations limpas, suítes backend/frontend, check, lint, TypeScript, build e
  `git diff --check`.

Os cenários concorrentes exigem PostgreSQL real. Testes funcionais, contratos,
frontend, renderer com storage temporário e autorização podem usar os
ambientes isolados normais.

## Pendências humanas

- Revisar visualmente a D.6F em navegadores e dispositivos reais antes de
  iniciar D.6G. A conclusão atual é técnica, não aprovação visual definitiva.
- Escolher na D.6G entre os modelos anuais A e B depois de comparar
  protótipos com os mesmos dados.
- Fornecer a logo real do movimento/paróquia quando a prototipagem de PDF
  começar; não usar placeholder final.
- Refinar no spike a UX de preview/publicar sem permitir que preview entre no
  histórico.
- A política de consulta/download histórico permanece conservadoramente
  restrita a Suporte/Diretoria/superuser até decisão explícita diferente.

Nenhuma dessas pendências bloqueia o frontend D.6F.

## Débitos

- O CRUD/frontend legado de Encontro não usa os services temporais e pode
  criar registros sem agenda. Seu cutover completo depende de contrato de dias
  estruturados e permanece separado da projeção D.6B.
- `data_referencia`, `data_exato` e `status_encontro` continuam necessários
  para consumidores existentes; não serão removidos nesta fase.
- Publicações exigem backup conjunto de banco e media; automação operacional
  de backup não pertence à D.6.
- A dependência de PDF e seus pacotes de sistema precisam de spike no ambiente
  real na D.6G, sem instalação antecipada.
- Eventos, compromissos genéricos, saúde, atividade canônica, frontends
  D.2–D.5, Excel e integrações externas permanecem fora do escopo, não débitos
  a resolver nesta fase.

## Arquivos relevantes

- `docs/decisions/ADR-001-calendario-institucional.md`
- `docs/domain/INSTITUTIONAL_CALENDAR.md`
- `docs/workplans/PHASE_1B_D6.md`
- `docs/00_HOME.md`
- `docs/PROJECT_STATE.md`
- `backend/core/models.py`
- `backend/core/services/encontros.py`
- `backend/core/services/avaliacoes_encontro.py`
- `backend/core/services/calendario_institucional.py`
- `backend/core/services/comandos_calendario.py`
- `backend/core/services/reunioes_preparatorias.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/urls.py`
- `backend/core/roles.py`
- `backend/core/permissions.py`
- `backend/core/migrations/0028_nucleo_encontros.py`
- `backend/core/migrations/0034_expand_propostas_violeiros.py`
- `backend/core/migrations/0035_diaencontro_data_index.py`
- `backend/core/migrations/0036_expand_agenda_encontro.py`
- `backend/core/tests/test_nucleo_encontros.py`
- `backend/core/tests/test_calendario_institucional.py`
- `backend/core/tests/test_calendario_institucional_agenda.py`
- `backend/core/tests/test_authorization.py`
- `backend/core/tests/test_authorization_paths.py`
- `backend/setup/settings.py`
- `backend/setup/urls.py`
- `backend/requirements.txt`
- `frontend/src/app/(painel)/encontros/page.tsx`
- `frontend/src/app/(painel)/encontros/[id]/page.tsx`
- `frontend/src/app/(painel)/calendario/page.tsx`
- `frontend/src/components/CalendarEncounterDrawer.tsx`
- `frontend/src/components/CalendarEncounterEditor.tsx`
- `frontend/src/components/CalendarEncounterForm.tsx`
- `frontend/src/components/EncounterAgendaSection.tsx`
- `frontend/src/components/InstitutionalCalendarHeader.tsx`
- `frontend/src/components/InstitutionalCalendarViews.tsx`
- `frontend/src/components/icons/EncounterCategoryIcon.tsx`
- `frontend/src/lib/dialog-focus.ts`
- `frontend/src/lib/institutional-calendar.ts`
- `frontend/src/lib/institutional-calendar.test.tsx`
- `frontend/src/lib/encontro-form-contract.ts`
- `frontend/src/lib/sia-profile-contracts.ts`
- `frontend/src/lib/sia-capabilities.ts`
- `frontend/src/lib/sia-navigation.ts`
- `frontend/src/components/Sidebar.tsx`
- `frontend/package.json`

## Próximo passo

Aguardando revisão visual humana antes da D.6G. Após esse checkpoint, o
próximo bloco permanece D.6G — PDF mensal/anual e histórico de divulgação.
Não iniciar renderer ou publicação antes da revisão.

## Histórico de execução

- 2026-10-06 — Vault da Fase 1B.3D.6 preparado. Regras estáveis separadas do
  relatório vivo; nenhum código, migration, teste, PDF ou banco foi alterado.
- 2026-10-06 — D.6A concluída por auditoria estática. Fechados query service,
  DTO/serializer, consulta por período, fallback legado, conflitos, comandos,
  roles, publicação com PDF + snapshot, private media, renderer recomendado,
  migrations e testes. Nenhum código, banco, migration ou PDF foi alterado.
- 2026-10-06 — D.6B concluída. Projeção, API de leitura, conflitos,
  autorização e índice implementados; 16 testes novos e suíte backend com 506
  testes aprovados, sem PostgreSQL, frontend ou comandos de escrita.
- 2026-10-06 — D.6C concluída. Comandos temporais, autorização de gestão,
  auditoria, avisos de conflito e sincronização compatível implementados; suíte
  backend com 525 testes aprovados e cinco cenários novos de concorrência
  reservados ao PostgreSQL na D.6H. Aguardando checkpoint humano de UX/UI.
- 2026-10-06 — D.6D concluída documentalmente por decisão humana. Aprovadas
  visões Mês/Ano, Agenda agregada, criação multiday, identidade visual, mobile,
  PDFs público/interno e dois protótipos anuais. D.6E foi inserida antes do
  frontend para implementar os deltas canônicos revelados pelo produto.
- 2026-10-06 — D.6E concluída. Schema expansivo, Agenda heterogênea, reuniões
  canônicas, avaliação 1:1, visibilidade, conflitos e criação completa foram
  implementados; suíte backend com 539 testes aprovados e seis cenários de
  concorrência reservados ao PostgreSQL na D.6H. Próximo bloco: D.6F.
- 2026-10-06 — D.6F tecnicamente concluída. Rota, visões mensal/anual,
  identidade própria, drawer, criação/edição canônicas, Agenda no Encontro,
  mobile e acessibilidade implementados; 124 testes frontend, lint,
  TypeScript e build Webpack aprovados. Aguardando revisão visual humana antes
  da D.6G.
