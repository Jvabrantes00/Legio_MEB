# Fase 1B.3D.3 — Equipes e Trabalho em Encontro

## Status geral

Fase preparada no Vault. Implementação ainda não iniciada; D.3A é o próximo
bloco.

## Objetivo

Modelar templates, equipes, roles, convites de trabalho, alocação,
`TrabalhoEncontro`, reuniões preparatórias, presença, autorização contextual e
elegibilidade para trabalhar, preservando compatibilidade incremental com o
legado e as regras estáveis de
[[../domain/ENCOUNTER_WORK|Equipes e Trabalho em Encontro]].

## Escopo

- Templates e snapshots de equipes e roles por tipo de Encontro.
- Convite com finalidade `TRABALHAR` e alocação operacional.
- Resultado real de trabalho e histórico permanente.
- Reuniões preparatórias e presença dos trabalhadores.
- Autorização contextual da Coordenação Geral.
- Elegibilidade e avisos para trabalhar.
- Compatibilidade incremental com os contratos legados.

## Fora de escopo

- Saúde contextual e acesso a dados de saúde.
- Criação ou destruição automática de contas.
- Criação automática de `Frequencia`.
- Timeline completa de realocações ou entidade explícita de substituição.
- Frontend novo antes do bloco de compatibilidade aplicável.
- Backfill heurístico de equipes, funções ou históricos.
- Remoção física antecipada da estrutura legada.

## Blocos

### D.3A — Análise do legado e desenho técnico

Status: pendente.

### D.3B — Templates, equipes, roles e TrabalhoEncontro

Status: pendente.

### D.3C — Services de convite, alocação e trabalho

Status: pendente.

### D.3D — Reuniões preparatórias e presença

Status: pendente.

### D.3E — Autorização contextual da Coordenação Geral

Status: pendente.

### D.3F — Elegibilidade e avisos para trabalhar

Status: pendente.

### D.3G — Compatibilidade, PostgreSQL, regressão e fechamento

Status: pendente.

## Decisões da fase

As regras de domínio já fechadas estão em
[[../domain/ENCOUNTER_WORK]]. Este workplan registrará somente decisões
técnicas, conflitos encontrados, progresso e validações, sem duplicar o
documento estável.

O desenho técnico de models, FKs, constraints, transições, concorrência,
compatibilidade e migrations permanece pendente da D.3A.

## Descobertas técnicas

Ainda não iniciadas. A D.3A deve inspecionar o código real antes de registrar
qualquer correspondência entre os conceitos novos e a estrutura legada.

## Compatibilidade com legado

- Estratégia prevista: `EXPAND` → `POPULATE`, quando seguro → `COMPAT` →
  `CUTOVER` → `DEPRECATE`.
- O legado mistura equipe e função; nenhuma equivalência ou origem de backfill
  será presumida antes da análise.
- Contratos ainda consumidos devem ser preservados durante a transição, sem
  big-bang ou remoção física antecipada.

## Migrations

Nenhuma migration criada. A necessidade e a forma da próxima migration
expansiva serão definidas somente após a D.3A.

## Testes e validações

Nenhum teste executado nesta preparação documental. Cada bloco deve registrar
sua cobertura e seus resultados reais quando for concluído.

## Débitos

- Mapping entre equipes, funções e vínculos legados ainda não analisado.
- Segurança de eventual backfill ainda não demonstrada.
- A forma técnica de avaliar elegibilidade e avisos para AVC e Acampamento
  ainda precisa ser fechada na D.3A.
- Consumidores backend e frontend da estrutura antiga ainda precisam ser
  inventariados.

## Arquivos relevantes

- `docs/domain/ENCOUNTER_WORK.md`
- `docs/workplans/PHASE_1B_D3.md`
- `docs/domain/ENCOUNTER_PARTICIPATION.md`, quando houver dependência direta de
  `ConviteEncontro`.
- `docs/workplans/PHASE_1B_D2.md`, como histórico da fundação de convite e
  compatibilidade.

Arquivos de código serão acrescentados somente depois da inspeção da D.3A.

## Próximo passo

D.3A — analisar o código real e fechar o desenho técnico.

## Padrão de relatórios durante a D.3

Ao finalizar cada bloco:

1. registrar detalhes completos neste workplan;
2. não repetir regras estáveis do documento de domínio;
3. atualizar `docs/PROJECT_STATE.md` somente diante de mudança global;
4. atualizar `docs/00_HOME.md` somente quando o roteamento mudar;
5. entregar no chat apenas um resumo executivo curto.

## Histórico de execução

- 2026-10-04 — Vault preparado. Regras estáveis separadas do relatório vivo;
  D.3A permanece pendente e nenhuma implementação foi iniciada.
