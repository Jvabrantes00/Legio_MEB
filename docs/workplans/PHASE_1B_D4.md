# Fase 1B.3D.4 — Formação em Encontros

## Status geral

Fase preparada documentalmente. Nenhuma análise técnica ou implementação foi
iniciada. D.4A é o próximo bloco.

## Objetivo

Modelar palestras e bate-papos realizados em Encontros, seus temas fixos,
sessões, palestrantes internos ou externos e o histórico formativo do
Alpinista, preservando as regras estáveis de
[[../domain/ENCOUNTER_FORMATION|Formação em Encontros]] e a compatibilidade
incremental com o legado.

## Escopo

- Catálogo fixo de temas definido em código.
- Sessões formativas de Escalada, ESPPA e AVC.
- Múltiplos palestrantes internos ou externos por sessão, conforme o tipo de
  Encontro.
- Histórico de atuação efetiva do Alpinista como palestrante.
- Regra bloqueante que vincula o palestrante de AVC ao trabalho naquele mesmo
  Encontro.
- Autorização de Formação, Diretoria e Suporte.
- Evolução incremental `EXPAND` → `POPULATE` seguro → `COMPAT` → `CUTOVER` →
  `DEPRECATE`.

## Fora de escopo

- Conteúdo formativo de Acampamento.
- CRUD livre ou administrativo de temas.
- Nomes reais ou fictícios de palestras e bate-papos nesta preparação.
- Dia e horário obrigatórios para a sessão.
- Criação de `Pessoa` para palestrante externo.
- Criação de `PerfilAlpinista` ou `Frequencia`.
- Alteração de equipes, `TrabalhoEncontro` ou histórico de equipe.
- Backfill heurístico ou remoção antecipada de estrutura legada.

## Blocos

### D.4A — Análise do legado e desenho técnico

Status: pendente.

### D.4B — Catálogo estrutural, sessões e palestrantes

Status: pendente.

### D.4C — Services, regras por tipo e histórico

Status: pendente.

### D.4D — API, autorização e compatibilidade

Status: pendente.

### D.4E — PostgreSQL, regressão e fechamento

Status: pendente.

## Decisões da fase

- As regras de produto já fechadas estão consolidadas no documento de domínio
  e não devem ser duplicadas aqui a cada bloco.
- A representação técnica do catálogo fixo, das sessões, dos palestrantes e do
  histórico será decidida na D.4A a partir do código real.
- Preencher futuramente os nomes do catálogo em código não deve exigir uma
  migration apenas por causa dos nomes.

## Descobertas técnicas

Nenhuma descoberta técnica registrada. A inspeção de models, services,
serializers, views, rotas, frontend, testes, migrations e legado pertence à
D.4A.

## Compatibilidade com legado

- A D.4A deve inventariar palestras, funções, históricos e quadrantes atuais,
  incluindo seus consumidores.
- Estruturas e contratos existentes só poderão sofrer cutover após estratégia
  incremental explícita.
- Não há evidência avaliada para população automática nesta preparação;
  nenhum backfill foi proposto.

## Migrations

Nenhuma migration criada ou numerada. A D.4A deverá confirmar o schema atual e
a migration mais recente antes de propor qualquer etapa expansiva.

## Testes e validações

- Nenhum teste de código foi necessário nesta preparação documental.
- A validação desta etapa limita-se à consistência dos documentos, ao
  `git diff --check` e ao estado do repositório.

## Débitos

- Representação técnica do catálogo fixo.
- Models, FKs, `on_delete`, constraints, índices e invariantes de service.
- Critério persistido que comprova atuação efetiva do palestrante.
- Integração exata com `Pessoa`, `PerfilAlpinista` e `TrabalhoEncontro` no AVC.
- Estratégia de concorrência, API, auditoria, autorização e cutover legado.
- Possibilidade ou ausência de backfill inequivocamente seguro.

## Arquivos relevantes

- `docs/domain/ENCOUNTER_FORMATION.md`
- `docs/workplans/PHASE_1B_D4.md`
- `docs/domain/ENCOUNTER_WORK.md`, somente para dependências diretas de
  `TrabalhoEncontro`, especialmente no AVC.
- `docs/AUTHORIZATION_MATRIX.md`, somente quando a tarefa envolver permissões.
- Código e testes relacionados, a identificar na D.4A.

## Próximo passo

D.4A — analisar o código real e fechar o desenho técnico da Formação em
Encontros, sem implementar models ou migrations.

## Histórico de execução

- 2026-10-05 — Vault da Fase 1B.3D.4 preparado. Regras estáveis separadas do
  relatório vivo; nenhuma análise técnica, implementação, migration ou acesso
  ao PostgreSQL foi realizado.
