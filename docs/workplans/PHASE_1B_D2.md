# Fase 1B.3D.2 — Inscrição, Convite e Participação

## Status geral

Preparação documental concluída. A análise técnica ainda não foi iniciada e
todos os blocos de implementação permanecem pendentes.

## Objetivo

Modelar inscrição, convite, confirmação, participação e conclusão de Encontros,
preservando compatibilidade incremental com o legado e as regras estáveis de
[[../domain/ENCOUNTER_PARTICIPATION|participação em Encontros]].

## Escopo

- Inscrição permanente para Escalada e ESPPA.
- Convites de participação ou trabalho vinculados a Encontros.
- Resultado real de participação e conclusão única por tipo elegível.
- Criação de `PerfilAlpinista` por conclusão válida de Escalada ou ESPPA.
- Compatibilidade e transição incremental do legado.

## Fora de escopo

- Domínio completo de trabalho e equipes.
- Participação diária genérica.
- Criação automática de `Frequencia` a partir de inscrição, convite,
  confirmação, participação ou conclusão.
- Resultados técnicos ainda não apurados pela D.2A.

## Blocos

### D.2A — Análise, legado e desenho técnico

Status: pendente.

### D.2B — Models, migration e constraints

Status: pendente.

### D.2C — Services e regras transacionais

Status: pendente.

### D.2D — Compatibilidade e cutover legado

Status: pendente.

### D.2E — Regressão, documentação e fechamento

Status: pendente.

## Decisões da fase

As decisões de domínio já congeladas estão em
[[../domain/ENCOUNTER_PARTICIPATION]]. A fase deve implementá-las sem duplicar
essas regras neste relatório vivo.

## Descobertas técnicas

Pendente da D.2A.

## Compatibilidade com legado

- Estratégia: `EXPAND` → `POPULATE`, quando seguro → `COMPAT` → `CUTOVER` →
  `DEPRECATE`.
- Identificar na D.2A o comportamento legado que pode criar ou ativar Alpinista
  cedo demais.
- Mapeamentos, riscos e condições de cutover permanecem pendentes.

## Migrations

Nenhuma migration criada. Desenho pendente da D.2A.

## Testes e validações

Nenhum teste executado ou criado. Estratégia pendente da D.2A.

## Débitos

- Definir a constraint concreta para inscrição pendente ativa por Pessoa e
  tipo.
- Definir a proteção técnica para conclusão única por Pessoa e tipo elegível.
- Localizar e caracterizar o comportamento legado de criação ou ativação
  antecipada de Alpinista.

## Arquivos relevantes

- `docs/domain/ENCOUNTER_PARTICIPATION.md`
- `docs/workplans/PHASE_1B_D2.md`
- `docs/PROJECT_STATE.md`, somente para estado global do projeto.

## Próximo passo

Executar D.2A — análise do código real, legado e desenho técnico.

## Padrão de relatórios durante a D.2

Ao finalizar cada bloco:

1. atualizar este workplan com os detalhes completos;
2. atualizar `docs/PROJECT_STATE.md` e `docs/00_HOME.md` somente quando houver
   mudança de estado global ou de roteamento;
3. entregar no chat apenas um resumo executivo curto com o bloco concluído,
   principais implementações, testes e validações, débitos ou decisões
   pendentes, documentação atualizada, status do Git e commit sugerido quando
   aplicável.

O chat não deve repetir o conteúdo completo já registrado neste workplan.

## Histórico de execução

- 2026-10-02 — Vault preparado; regras estáveis separadas do relatório vivo.
  D.2A permanece pendente.

