# Fase 1B.3D.5 — MME e Propostas de Violeiros

## Status geral

Fase preparada documentalmente. As regras estáveis foram registradas sem
análise técnica ou implementação. D.5A é o próximo bloco.

## Objetivo

Modelar o planejamento do MME por múltiplas propostas de possíveis equipes de
Violeiros, preservando candidatos históricos, derivando disponibilidade da
escala oficial e mantendo separação estrita entre sugestão e trabalho real,
conforme [[../domain/ENCOUNTER_MME|MME e Propostas de Violeiros]].

## Escopo

- Múltiplas propostas de Violeiros por Encontro.
- Cinco posições ativas por proposta: uma coordenação sugerida e quatro
  integrantes sugeridos.
- Preservação histórica de candidatos que deixam de ocupar posição ativa.
- Mesma Pessoa em várias propostas e unicidade apenas dentro de cada proposta.
- Disponibilidade derivada da escala oficial do mesmo Encontro.
- Indicação consultável de proposta incompleta.
- Edição durante planejamento aberto e encerramento operacional mínimo.
- Seleção oficial pelos fluxos canônicos da D.2/D.3.
- Autorização de MME, Diretoria, Suporte e leitura por Fichas.
- Compatibilidade incremental com estruturas eventualmente encontradas no
  legado.

## Fora de escopo

- Escala oficial paralela a `TrabalhoEncontro`.
- Convite, alocação ou histórico de trabalho criados pela proposta.
- Escolha obrigatória de uma proposta inteira.
- Reserva bloqueante de candidato ou unicidade global Pessoa/Encontro.
- Relação de substituição entre candidatos.
- Timeline completa de todas as edições.
- Subsistema de notificações, push ou e-mail.
- Catálogo de instrumentos.
- Frequência, saúde, Formação em Encontros ou permissões de coordenação.
- Backfill heurístico e remoção antecipada de estrutura legada.
- Implementação frontend nesta preparação documental.

## Blocos

### D.5A — Análise do legado e desenho técnico

Status: pendente.

### D.5B — Propostas, itens e fundação estrutural

Status: pendente.

### D.5C — Services, disponibilidade e encerramento operacional

Status: pendente.

### D.5D — API, autorização e compatibilidade

Status: pendente.

### D.5E — PostgreSQL, regressão e fechamento

Status: pendente.

## Decisões da fase

- As regras estáveis estão no documento de domínio e não devem ser duplicadas
  neste relatório vivo.
- Proposta é planejamento, nunca escala ou histórico permanente.
- Fichas/Diretoria podem compor a escala oficial livremente a partir de várias
  propostas ou de nomes externos a elas.
- A distinção técnica entre registro histórico e posição ativa será fechada na
  D.5A com base no código real.
- O indicador de proposta incompleta e o encerramento do planejamento devem
  usar a solução mínima coerente, sem workflow ou notificações excessivos.

## Descobertas técnicas

Pendentes da D.5A. Devem ser inspecionados models, campos de
`PerfilAlpinista`, estruturas de pré-equipe, serializers, views/actions,
frontend, histórico, permissões, testes, migrations e vínculos com a escala
oficial.

## Compatibilidade com legado

- O inventário do legado será realizado na D.5A antes de qualquer proposta de
  compatibilidade ou cutover.
- Não há evidência documental suficiente para backfill nesta preparação.
- **nenhum backfill automático nesta etapa**.

## Migrations

Nenhuma migration foi criada ou proposta nesta preparação. A D.5A deve
confirmar o estado real da cadeia antes de desenhar a fundação expansiva.

## Testes e validações

- Nenhum teste de código ou banco foi executado nesta preparação documental.
- A validação limita-se à integridade do diff e ao estado do repositório.
- Critérios técnicos e matriz de testes serão fechados na D.5A.

## Débitos

- Análise do legado e desenho técnico completo.
- Definição de models, constraints, índices, estados e migrations.
- Estratégia transacional de disponibilidade, encerramento e concorrência.
- API, autorização, compatibilidade e contratos frontend futuros.
- Validação PostgreSQL e regressão final.

## Arquivos relevantes

- `docs/domain/ENCOUNTER_MME.md`
- `docs/workplans/PHASE_1B_D5.md`
- `docs/domain/ENCOUNTER_WORK.md`, somente para dependências da escala oficial,
  `TrabalhoEncontro`, elegibilidade e histórico de trabalho.
- `docs/AUTHORIZATION_MATRIX.md`, somente para tarefas de autorização.
- Código e contratos reais a serem localizados pela D.5A sem leitura
  indiscriminada do repositório.

## Próximo passo

D.5A — analisar o código real e fechar o desenho técnico de propostas, itens,
posições ativas, disponibilidade, encerramento, compatibilidade e testes.

## Histórico de execução

- 2026-10-06 — Vault da Fase 1B.3D.5 preparado. Regras estáveis separadas do
  relatório vivo; nenhuma análise técnica, implementação, migration, teste ou
  acesso ao PostgreSQL foi realizado.
