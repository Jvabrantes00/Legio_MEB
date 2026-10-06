# Fase 1B.3D.6 — Calendário Institucional: Encontros

## Status geral

Fase preparada documentalmente em 2026-10-06. Todos os blocos permanecem
pendentes. D.6A — auditoria e desenho técnico da projeção — é o próximo
bloco.

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

Status: pendente.

Auditará models, services, serializers, views, rotas, autorização, frontend,
testes e migrations relacionados ao núcleo temporal. Fechará o desenho da
projeção, comandos expostos, detecção mínima de conflitos e arquitetura de
exportação e histórico de divulgação, sem implementar.

### D.6B — Projeção, consultas e API

Status: pendente.

### D.6C — Comandos, criação/edição e autorização

Status: pendente.

### D.6D — Definição de UX/UI

Status: pendente.

Checkpoint humano obrigatório. O trabalho deve parar para apresentar o estado
técnico e obter decisões do usuário. Nenhum frontend, design final de PDF ou
aplicação de paleta pode ser implementado antes da aprovação e do registro da
especificação visual.

### D.6E — Implementação do frontend personalizado

Status: pendente.

### D.6F — PDF mensal/anual e histórico de divulgação

Status: pendente.

Implementará a exportação e a preservação das publicações somente depois do
design aprovado na D.6D.

### D.6G — Integração, PostgreSQL, regressão e fechamento

Status: pendente.

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

Ainda não realizadas. A preparação documental parte da estrutura temporal já
registrada (`Encontro`, `CalendarioEncontro` e `DiaEncontro`). A D.6A deve
confirmar o código real e não assumir que os contratos existentes expõem toda
a capacidade necessária.

## Compatibilidade com legado

- `status_encontro` continua sendo projeção temporal legada e não será usado
  como lifecycle pela nova interface.
- A D.6 não cria entidade visual duplicada nem altera contratos antigos como
  efeito colateral.
- Estratégia incremental, contratos preservados e eventual débito de cutover
  serão detalhados pela auditoria D.6A.

## API e projeção

Pendente de desenho técnico na D.6A. A API deve projetar objetos canônicos,
reutilizar services de Encontro e manter categoria e status como dimensões
distintas. O Calendário não concederá permissões do módulo de origem.

## UX/UI aprovado

Pendente do checkpoint humano D.6D. Devem ser decididos visual mensal,
semanal/lista, navegação, desktop/mobile, cards, densidade, criação/edição,
múltiplos dias, provisoriedade, status, filtros, acessibilidade, hierarquia e
eventual uso da paleta candidata `#001C38`, `#005EE9`, `#FD1E2E`, `#FFFFFF`,
`#F6FAFD`, `#EAF1F7` e `#DCE4EC`. Essas cores são apenas material para a
discussão e não uma especificação aprovada.

## Exportação PDF

Estão aprovadas as modalidades mensal e anual e a linguagem de calendário em
grade. Papel, orientação, fontes, dimensões, cabeçalho, densidade, cores,
nomes longos e múltiplas atividades no mesmo dia aguardam D.6D. A implementação
pertence à D.6F.

## Histórico de divulgação

Cada material efetivamente publicado deve permanecer recuperável com seu
conteúdo exato, ainda que o calendário canônico mude depois. A D.6A comparará
PDF imutável, snapshot estruturado, combinação de ambos, metadados e hash;
nenhuma opção foi escolhida nesta preparação.

## Testes e validações

Ainda não executados. Cada bloco registrará cobertura estrutural, services,
API, autorização, contratos, frontend, exportação, histórico, integração,
migrations e regressão proporcionais ao seu escopo.

## Débitos

Nenhum débito novo foi identificado nesta preparação documental. Eventos,
compromissos genéricos, saúde, atividade canônica, frontends D.2–D.5, Excel e
integrações externas permanecem fora do escopo, não débitos da D.6.

## Arquivos relevantes

- `docs/decisions/ADR-001-calendario-institucional.md`
- `docs/domain/INSTITUTIONAL_CALENDAR.md`
- `docs/workplans/PHASE_1B_D6.md`
- `docs/00_HOME.md`
- `docs/PROJECT_STATE.md`
- models, services, serializers, views, rotas, testes e migrations do núcleo
  de Encontros, a identificar precisamente na D.6A.
- contratos e componentes frontend atuais de Encontros, somente quando a
  auditoria comprovar dependência.

## Próximo passo

D.6A — auditar o código atual e fechar o desenho técnico da projeção de
Encontros no Calendário Institucional e da futura arquitetura de publicação
PDF, sem implementar.

## Histórico de execução

- 2026-10-06 — Vault da Fase 1B.3D.6 preparado. Regras estáveis separadas do
  relatório vivo; nenhum código, migration, teste, PDF ou banco foi alterado.
