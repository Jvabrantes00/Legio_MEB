# SIA/MEB — Contexto do Projeto

Este arquivo é o ponto de entrada da documentação. Ele roteia o contexto; não
substitui os documentos de referência nem os `AGENTS.md` aplicáveis.

## Estado atual

- Fase 0 concluída.
- Fase 1 em andamento.
- 1B.3B — Pessoa e backfill inicial concluída.
- 1B.3C — Grupo e Frequência concluída; o profiling do grupo legado não
  sustenta backfill automático.
- Backfills de `PerfilAlpinista` e do histórico de Grupo continuam bloqueados
  até a reconciliação das fontes legadas.
- 1B.3D.0 concluiu a decisão do Calendário Institucional como HUB.
- 1B.3D.1 concluiu o núcleo de Encontros com lifecycle, calendários e dias,
  preservando o contrato legado da API.
- 1B.3D.2 concluiu Inscrição, Convite e Participação, com services
  transacionais, cutover lógico e validação real em PostgreSQL.
- 1B.3D.3 concluiu Equipes e Trabalho em Encontro, incluindo cutover lógico e
  validação de concorrência em PostgreSQL.
- 1B.3D.4 — Formação em Encontros concluída, com catálogo real, services, API,
  autorização e validação PostgreSQL.
- 1B.3D.5 — MME e Propostas de Violeiros concluída, com services, API,
  autorização, compatibilidade e validação de concorrência em PostgreSQL.
- 1B.3D.6 — Calendário Institucional concluída, incluindo frontend, Agenda,
  PDFs, publicação privada, regressão final e checkpoint de concorrência em
  PostgreSQL 16 com 6/6 cenários aprovados.
- Roadmap Re-baseline em andamento. R.1 foi concluída e validada humanamente.
- Checkpoint atual: R.2 — Planejado × implementado × faltante, documentada e
  aguardando aprovação humana.
- Após a aprovação da R.2: R.3 — Revisão de maturidade. O re-baseline não
  antecipa uma nova fase de implementação.

O estado vivo e o roadmap estão em [[PROJECT_STATE]].

## Como carregar contexto

### Regra geral

1. Leia e aplique primeiro os `AGENTS.md` que alcançam o arquivo ou diretório
   da tarefa.
2. Use este arquivo como roteador.
3. Não leia toda a pasta `docs/` por padrão.
4. Carregue somente os documentos relacionados à tarefa atual.
5. Não releia documentos quando a informação necessária já estiver
   suficientemente disponível no contexto da sessão.
6. Amplie a leitura apenas quando surgir evidência de dependência adicional.

### Documentos de domínio e workplans

- `docs/domain/*` registra regras estáveis de domínio.
- `docs/workplans/*` registra execução, progresso, decisões técnicas, testes,
  débitos e histórico de uma fase.
- Não carregue documentos desses dois grupos indiscriminadamente em tarefas de
  outros domínios.

### Roadmap Re-baseline

Se a tarefa envolver a auditoria do roadmap histórico, comparação entre
planejado e implementado, maturidade, checkpoint de produto/arquitetura ou
Roadmap v2, leia:

1. `docs/workplans/ROADMAP_REBASELINE.md`;
2. `docs/PROJECT_STATE.md` somente quando o estado atual for necessário;
3. fontes históricas citadas pelo workplan conforme a etapa em execução.

Não avance de uma etapa R para a seguinte sem o checkpoint previsto.

### Calendário Institucional — fatia de Encontros

Se a tarefa envolver Calendário Institucional, projeção ou agenda de
Encontros, `CalendarioEncontro`, `DiaEncontro`, criação/edição pelo
Calendário, frontend do Calendário, PDF mensal/anual, versões divulgadas ou
histórico de divulgação, leia nesta ordem:

1. `docs/decisions/ADR-001-calendario-institucional.md`;
2. `docs/domain/INSTITUTIONAL_CALENDAR.md`;
3. `docs/workplans/PHASE_1B_D6.md`.

Consulte a documentação e o código do núcleo de Encontros somente quando a
tarefa exigir. Não carregue D.2–D.5 sem dependência real.

### Inscrição, convite e participação em Encontros

Se a tarefa envolver inscrição em Escalada ou ESPPA, convite de Encontro,
confirmação, participação, `CONCLUIU`, `FALTOU`, `DESISTIU` ou criação de
`PerfilAlpinista` por conclusão, leia nesta ordem:

1. `docs/domain/ENCOUNTER_PARTICIPATION.md`;
2. `docs/workplans/PHASE_1B_D2.md`.

Consulte `docs/PROJECT_STATE.md` somente quando o estado global do projeto for
necessário. Carregue outros documentos apenas diante de dependência real da
tarefa.

### Equipes e Trabalho em Encontro

Se a tarefa envolver templates ou equipes de Encontro, roles/funções, convite
para trabalhar, alocação, `TrabalhoEncontro`, coordenação, reuniões ou presença
preparatória, autorização contextual da Coordenação Geral ou elegibilidade
para trabalhar, leia nesta ordem:

1. `docs/domain/ENCOUNTER_WORK.md`;
2. `docs/workplans/PHASE_1B_D3.md`.

Consulte `docs/PROJECT_STATE.md` somente quando o estado global for necessário.
Consulte `docs/domain/ENCOUNTER_PARTICIPATION.md` quando houver dependência
direta do `ConviteEncontro` criado na D.2. Não carregue outros domínios sem
evidência de necessidade.

### Formação em Encontros

Se a tarefa envolver palestras, bate-papos, sessões formativas, palestrantes,
palestrante externo, histórico formativo ou Formação em Encontros, leia nesta
ordem:

1. `docs/domain/ENCOUNTER_FORMATION.md`;
2. `docs/workplans/PHASE_1B_D4.md`.

Consulte `docs/domain/ENCOUNTER_WORK.md` somente quando houver dependência
direta de `TrabalhoEncontro`, especialmente para a regra de palestrante no
AVC. Consulte `docs/AUTHORIZATION_MATRIX.md` somente quando a tarefa envolver
permissões. Não carregue outros domínios indiscriminadamente.

### MME e Propostas de Violeiros

Se a tarefa envolver MME, propostas ou pré-equipes de Violeiros, candidatos,
cinco posições ativas, disponibilidade nas propostas, aproveitamento pela
escala oficial ou composição sugerida de um coordenador e quatro integrantes,
leia nesta ordem:

1. `docs/domain/ENCOUNTER_MME.md`;
2. `docs/workplans/PHASE_1B_D5.md`.

Consulte `docs/domain/ENCOUNTER_WORK.md` somente quando houver dependência
direta de `TrabalhoEncontro`, equipe oficial, alocação, elegibilidade ou
histórico de trabalho. Consulte `docs/AUTHORIZATION_MATRIX.md` somente quando a
tarefa envolver permissões. Não carregue outros domínios indiscriminadamente.

### Arquitetura

Para decisões ou mudanças arquiteturais, consulte:

- [[ARCHITECTURE]]
- [[PROJECT_STATE]]
- [[decisions/ADR-001-calendario-institucional]] para o Calendário
  Institucional e o lifecycle futuro de Encontros.

### Autorização, papéis e dados sensíveis

Para permissions, roles, escopo, privacidade ou dados sensíveis, consulte:

- [[AUTHORIZATION_MATRIX]]
- [[ARCHITECTURE]]

### Backend, domínio e migrations

Para models, migrations, services ou regras de domínio, consulte:

- [[PROJECT_STATE]]
- [[ARCHITECTURE]]
- a decisão ou documentação específica do domínio afetado, quando existir.

Leia também `/backend/AGENTS.md`. Os models, migrations e contratos atuais
continuam sendo a fonte técnica primária da implementação.

### Frontend, BFF e contratos

Leia `/frontend/AGENTS.md` e carregue somente a documentação do contrato,
feature ou fronteira arquitetural afetada. Para autenticação, BFF, mídia ou
summary/full, consulte também [[ARCHITECTURE]] e, quando houver autorização
envolvida, [[AUTHORIZATION_MATRIX]].

### Compatibilidade e regressão da Fase 0

Consulte [[PHASE_0_CLOSURE]] somente quando a tarefa envolver:

- compatibilidade com o baseline estabilizado;
- invariantes ou regressão da Fase 0;
- decisões históricas relevantes para a alteração.

## AGENTS

Os arquivos `AGENTS.md` permanecem em suas posições originais porque a
localização define seu escopo:

- `/AGENTS.md` — projeto inteiro;
- `/backend/AGENTS.md` — backend;
- `/frontend/AGENTS.md` — frontend.

Use [[AGENTS_INDEX]] como mapa de escopo. O índice não substitui a leitura dos
AGENTS aplicáveis.

## Navegação

- [[PROJECT_STATE]] — estado vivo, decisões e roadmap.
- [[ARCHITECTURE]] — fronteiras técnicas e arquitetura corrente.
- [[AUTHORIZATION_MATRIX]] — autorização implementada.
- [[decisions/ADR-001-calendario-institucional]] — decisão do Calendário
  Institucional.
- [[PHASE_0_CLOSURE]] — fechamento histórico da Fase 0.
- [[workplans/DEV_SEED]] — dataset controlado para testes manuais em
  desenvolvimento.
- [[AGENTS_INDEX]] — localização e alcance dos guias de agentes.
