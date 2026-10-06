# Fase 1B.3D.6 — Calendário Institucional: Encontros

## Status geral

D.6A concluída em 2026-10-06 por auditoria estática do código. O desenho de
projeção, conflitos, comandos, autorização, publicação imutável e geração de
PDF foi fechado sem implementar. D.6B — projeção, consultas e API — é o
próximo bloco.

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

Status: pendente.

Implementará o query service, DTOs, serializer allowlist, consulta inclusiva
por período, conflito consultivo, capabilities de leitura e índice de data,
sem comandos de escrita nem tabela duplicada de calendário.

### D.6C — Comandos, criação/edição e autorização

Status: pendente.

Exporá comandos explícitos de criação, dados básicos, planejamento,
oficialização, reprogramação, adiamento e cancelamento, delegando aos services
canônicos e atualizando auditoria e matriz implementada.

### D.6D — Definição de UX/UI

Status: pendente.

Checkpoint humano obrigatório. O trabalho deve parar para apresentar o estado
técnico e obter decisões do usuário. Nenhum frontend, design final de PDF ou
aplicação de paleta pode ser implementado antes da aprovação e do registro da
especificação visual.

### D.6E — Implementação do frontend personalizado

Status: pendente.

Implementará somente a especificação visual aprovada na D.6D, usando o BFF,
as capabilities e os contratos entregues em D.6B/D.6C.

### D.6F — PDF mensal/anual e histórico de divulgação

Status: pendente.

Implementará a exportação e a preservação das publicações somente depois do
design aprovado na D.6D.

### D.6G — Integração, PostgreSQL, regressão e fechamento

Status: pendente.

Validará integração, migrations limpas, concorrência de publicação e
alteração temporal em PostgreSQL, regressão backend/frontend, storage
temporário e remoção de recursos efêmeros.

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
- Publicações efetivas são históricas e não podem ser sobrescritas.
- D.6D é gate humano antes do frontend e da apresentação final dos PDFs.

## Descobertas técnicas

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
- Não existe índice iniciado por `DiaEncontro.data`; o índice único atual
  começa por `calendario_id` e não atende idealmente buscas globais por
  intervalo.
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
  recente do projeto é `0034_expand_propostas_violeiros`.
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

Pendente do checkpoint humano D.6D. O contrato técnico acima é suficiente
para D.6B/D.6C e não congela aparência.

Perguntas reservadas ao checkpoint:

- visual principal mensal, semanal ou lista e combinação entre eles;
- navegação, desktop/mobile, densidade, filtros e interação com dias;
- cards, páginas, modais ou drawers para criação e edição;
- apresentação de múltiplos dias, status, conflito e datas provisórias;
- se Encontros `ADIADO` sem agenda vigente precisam de uma lista auxiliar
  sem data, pois eles corretamente não entram na projeção por intervalo;
- acessibilidade, hierarquia e eventual uso da paleta candidata `#001C38`,
  `#005EE9`, `#FD1E2E`, `#FFFFFF`, `#F6FAFD`, `#EAF1F7` e `#DCE4EC`;
- papel, orientação, cabeçalho, fontes, densidade, nomes longos e múltiplos
  compromissos nos PDFs;
- se consulta/download das publicações históricas deve continuar restrita a
  Suporte/Diretoria ou ser aberta a todas as roles leitoras;
- como o usuário alterna entre preview e publicação. A distinção técnica é
  recomendada, mas o fluxo visual não será presumido.

Nenhuma dessas perguntas bloqueia a D.6B. A política conservadora até D.6D é
default deny para download histórico fora de Suporte/Diretoria.

## Exportação PDF

### Snapshot publicável

O renderer receberá um snapshot já allowlisted, nunca QuerySets ou models. O
snapshot possui versão de schema, período, instante de captura, legenda de
provisoriedade e somente ocorrências publicáveis com categoria, ID de origem,
nome, status, datas e indicador provisório. Participantes, equipes, dados
pessoais, saúde, observações internas e capabilities não entram.

### Renderer recomendado

- Gerar no backend a partir de template HTML/CSS de impressão e converter com
  WeasyPrint ou mecanismo equivalente aprovado em spike técnico na D.6F.
- Essa abordagem oferece melhor manutenção de grade, tipografia, quebra de
  página e composição anual que desenho manual de PDF.
- ReportLab exigiria layout de baixo nível; browser/Playwright adicionaria
  runtime Chromium e superfície operacional maior. Nenhuma das bibliotecas
  está instalada diretamente hoje.
- D.6F deverá fixar a dependência escolhida, validar bibliotecas de sistema no
  servidor e impedir busca de recursos remotos. Templates escapam títulos e
  usam apenas assets/fontes locais controlados.
- Aparência e dimensões permanecem bloqueadas até D.6D. O mesmo renderer
  receberá snapshots mensal e anual.

### Preview e publicação

- Recomenda-se preview transitório, sem registro oficial e com descarte
  imediato do arquivo temporário.
- Publicar é comando explícito: captura um snapshot novo, renderiza, calcula
  hash e persiste a versão imutável. Somente essa operação compõe o histórico.
- A D.6D decidirá a experiência dessa distinção, não sua garantia técnica.

## Histórico de divulgação

### Alternativas avaliadas

- Somente PDF preserva o artefato exato, mas dificulta consulta, auditoria do
  conteúdo e eventual geração em outro formato.
- Somente snapshot permite consulta e regeneração, mas não prova os mesmos
  bytes divulgados quando renderer, fontes ou template mudarem.
- **PDF + snapshot estruturado** preserva o material exato e a semântica que o
  originou. O custo de armazenamento é pequeno para calendários e justificado
  por fidelidade histórica, auditoria e backup. Esta é a arquitetura aprovada
  tecnicamente para D.6F.

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

- **D.6B:** provável migration exclusivamente aditiva para índice B-tree em
  `DiaEncontro.data`. A projeção em si não cria tabela.
- **D.6C:** nenhuma mudança de schema é esperada; comandos reutilizam a
  estrutura existente. Qualquer necessidade real deverá ser demonstrada por
  implementação/teste, não antecipada.
- **D.6F:** migration expansiva para `PublicacaoCalendarioInstitucional`,
  checks de tipo/período, índice histórico, FK protegida, snapshot e arquivo.
- A migration atual mais recente é `0034_expand_propostas_violeiros`. As
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

### D.6E/D.6F — frontend, PDF e histórico

- capabilities e navegação para todas as roles sem ampliar comandos;
- comportamento responsivo e acessível definido pela D.6D;
- snapshots mensal/anual, data provisória com marcador e ausência de campos
  privados;
- preview transitório, publicação imutável, duas publicações do mesmo período
  coexistindo e PDF antigo preservado após mudança canônica;
- hash, download autenticado, IDOR, content type, filename seguro, falhas de
  storage/banco e cleanup compensatório;
- renderer mensal/anual com fixtures determinísticos e testes de estrutura;
  validação visual segue o design aprovado, sem depender apenas de snapshot
  binário frágil.

### D.6G — PostgreSQL e regressão

- publicações simultâneas não se sobrescrevem;
- alteração/reprogramação durante captura não produz snapshot misto;
- locks e constraints preservam versões temporais e publicações consistentes;
- migrations limpas, suítes backend/frontend, check, lint, TypeScript, build e
  `git diff --check`.

Os três cenários concorrentes acima exigem PostgreSQL real. Testes funcionais,
contratos, renderer com storage temporário e autorização podem usar os
ambientes isolados normais.

## Pendências humanas

As perguntas visuais e a política de download histórico estão reservadas à
D.6D. Elas não bloqueiam a D.6B, cuja leitura usará o contrato neutro e a
política conservadora documentada. Não há decisão humana ou bloqueio técnico
pendente antes da projeção.

## Débitos

- O CRUD/frontend legado de Encontro não usa os services temporais e pode
  criar registros sem agenda. Seu cutover completo depende de contrato de dias
  estruturados e permanece separado da projeção D.6B.
- `data_referencia`, `data_exato` e `status_encontro` continuam necessários
  para consumidores existentes; não serão removidos nesta fase.
- Publicações exigem backup conjunto de banco e media; automação operacional
  de backup não pertence à D.6.
- A dependência de PDF e seus pacotes de sistema precisam de spike no ambiente
  real antes da D.6F, sem instalação antecipada na D.6A.
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
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/urls.py`
- `backend/core/roles.py`
- `backend/core/permissions.py`
- `backend/core/migrations/0028_nucleo_encontros.py`
- `backend/core/migrations/0034_expand_propostas_violeiros.py`
- `backend/core/tests/test_nucleo_encontros.py`
- `backend/core/tests/test_authorization.py`
- `backend/core/tests/test_authorization_paths.py`
- `backend/setup/settings.py`
- `backend/setup/urls.py`
- `backend/requirements.txt`
- `frontend/src/app/(painel)/encontros/page.tsx`
- `frontend/src/app/(painel)/encontros/[id]/page.tsx`
- `frontend/src/lib/encontro-form-contract.ts`
- `frontend/src/lib/sia-profile-contracts.ts`
- `frontend/src/lib/sia-capabilities.ts`
- `frontend/src/lib/sia-navigation.ts`
- `frontend/src/components/Sidebar.tsx`
- `frontend/package.json`

## Próximo passo

D.6B — implementar projeção, consulta inclusiva por período, fallback legado,
conflitos consultivos, serializer/API allowlist, autorização de leitura e o
índice necessário, sem comandos de escrita ou frontend.

## Histórico de execução

- 2026-10-06 — Vault da Fase 1B.3D.6 preparado. Regras estáveis separadas do
  relatório vivo; nenhum código, migration, teste, PDF ou banco foi alterado.
- 2026-10-06 — D.6A concluída por auditoria estática. Fechados query service,
  DTO/serializer, consulta por período, fallback legado, conflitos, comandos,
  roles, publicação com PDF + snapshot, private media, renderer recomendado,
  migrations e testes. Nenhum código, banco, migration ou PDF foi alterado.
