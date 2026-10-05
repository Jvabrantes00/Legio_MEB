# Fase 1B.3D.4 — Formação em Encontros

## Status geral

Fase em andamento. D.4A, D.4B, D.4C, D.4C.1 e D.4D estão concluídos. O
domínio possui fundação, catálogo real, services, API canônica, autorização e
compatibilidade de leitura sem backfill. D.4E é o próximo bloco.

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
- Inclusão de temas além do catálogo real aprovado na D.4C.1.
- Dia e horário obrigatórios para a sessão.
- Criação de `Pessoa` para palestrante externo.
- Criação de `PerfilAlpinista` ou `Frequencia`.
- Alteração de equipes, `TrabalhoEncontro` ou histórico de equipe.
- Backfill heurístico ou remoção antecipada de estrutura legada.

## Blocos

### D.4A — Análise do legado e desenho técnico

Status: concluída em 2026-10-05.

### D.4B — Catálogo estrutural, sessões e palestrantes

Status: concluída em 2026-10-05.

### D.4C — Services, regras por tipo e histórico

Status: concluída em 2026-10-05.

### D.4C.1 — Catálogo real fixo

Status: concluída em 2026-10-05.

### D.4D — API, autorização e compatibilidade

Status: concluída em 2026-10-05.

### D.4E — PostgreSQL, regressão e fechamento

Status: pendente.

## D.4A — relatório de análise e desenho técnico

### Método e limites

- Análise somente de arquivos na branch `sia/fase-1-modelagem-dominio`, a
  partir do commit `b6a9c78 docs: add phase 1b d4 domain context`.
- Foram inspecionados models, migrations, serializers, views, rotas,
  permissions, roles, admin, services, transformadores legados, testes e os
  consumidores frontend diretamente relacionados.
- `ENCOUNTER_WORK.md` foi consultado somente para a invariante de trabalho no
  AVC e a ordem de locks já estabelecida. `AUTHORIZATION_MATRIX.md` foi
  consultado somente para separar leitura e gestão de Formação.
- Nenhum teste, migration, query ou acesso ao PostgreSQL foi executado.

### Inventário do legado real

- O model `Palestra`, criado em `core.0022_palestra`, contém somente FKs com
  `CASCADE` para `Alpinista` e `Encontro`, `titulo` livre e unicidade por
  `alpinista/encontro/titulo`. Ele não representa sessão, tipo de conteúdo,
  catálogo, múltiplos palestrantes, externo, planejamento ou comprovação
  individual de realização.
- `HistoricoPalestraSerializer` expõe a allowlist `encontro_id`, nome, tipo e
  data do Encontro e `titulo`. A action read-only
  `/api/alpinistas/{id}/historico-palestras/` consulta diretamente `Palestra`.
- O filtro `palestrou` também deriva apenas da existência de `Palestra`. Não há
  flag persistido de palestrante, e os testes congelam essa derivação, a
  separação de histórico de equipe e a ausência de dados sensíveis.
- Suporte, Diretoria, Fichas e Formação podem ler o histórico atual. Formação
  pode usar o filtro `palestrou`, mas não recebe escrita de Alpinista. Não
  existe API de criação/edição de `Palestra` e o model não está registrado no
  admin técnico.
- O frontend fonte não consulta palestras, histórico formativo ou quadrante.
  Portanto, o consumidor implementado hoje é a API de perfil e seus testes;
  não há contrato visual da D.4 a migrar nesta etapa.
- A migration inicial tinha o valor textual `PALESTRANTE` no antigo campo de
  participação. A `0006` substituiu esse campo pela FK `FuncaoEncontro`, cujos
  tipos atuais são somente `encontrista` e `equipe`. Esse artefato histórico
  não identifica sessão, tema nem atuação efetiva e não é fonte segura.
- `FuncaoEncontro.nome` ainda menciona “Palestrante” apenas como exemplo de
  texto livre. `VinculoEncontroLegado` mistura participação/função e tampouco
  comprova conteúdo ministrado.
- A camada `core/legacy` não possui contrato, transformador, tabela ou mapping
  para palestra, bate-papo, tema, palestrante ou quadrante. O transformador de
  equipes conhece somente `encontros_alpinista` e `encontro_equipe`, e o
  mapping de funções permanece vazio.
- A migration mais recente é `core.0032_vinculousuariopessoa`. Não existe
  service atual para palestra; `TrabalhoEncontro` já oferece os estados e
  locks necessários para validar a regra do AVC sem fundir os domínios.

### Catálogo fixo em código

- Criar um módulo puro de domínio com `TemaFormativo` imutável e um registry
  somente leitura indexado por `codigo` estável. Cada entrada possuirá código,
  `tipo_conteudo`, título de apresentação e tipos de Encontro permitidos.
- `tipo_conteudo` terá os valores estruturais `PALESTRA` e `BATE_PAPO`. Os
  tipos permitidos serão validados sem comparação por títulos ou nomes de
  Encontro.
- O registry nascerá estruturalmente pronto e sem entradas enquanto os nomes
  reais não forem fornecidos. Não haverá seed, tabela de tema ou dado fictício.
- `SessaoFormativa.tema_codigo` será `CharField` sem `choices` derivadas do
  registry. Isso impede o autodetector de criar migrations sempre que o
  catálogo em código receber um tema novo. O service será a fronteira que
  rejeita código ausente ou incompatível.
- `tipo_conteudo` e `titulo_snapshot` serão copiados do registry na criação da
  sessão. O primeiro preserva classificação estrutural; o segundo preserva a
  leitura histórica mesmo após mudança de título no código.
- Código desconhecido nunca será aceito como string livre. Alterar o catálogo
  exige revisão de código e testes, mas não migration nem CRUD administrativo.

### Models propostos

#### `SessaoFormativa`

- FK `PROTECT` para `Encontro`, com `related_name='sessoes_formativas'`.
- Campos `tema_codigo`, `tipo_conteudo`, `titulo_snapshot`, `status`,
  `realizada_em`, `criado_em` e `atualizado_em`.
- Status técnicos: `PLANEJADA`, `REALIZADA` e `CANCELADA`. Somente
  `REALIZADA` pode alimentar histórico; cancelar preserva o registro sem
  convertê-lo em realização.
- Não terá dia ou horário obrigatório. Não haverá FK para tabela de temas.
- Não impor unicidade de Encontro/tema: o produto não proibiu duas realizações
  do mesmo conteúdo no mesmo Encontro.

#### `PalestranteSessao`

- FK `PROTECT` para `SessaoFormativa` e FK `PROTECT`, opcional, para
  `PerfilAlpinista`. O perfil canônico expressa que o interno é Alpinista, e
  sua `Pessoa` continua sendo a identidade usada na regra do AVC.
- Campo `nome_externo` vazio por padrão e sem criação de entidade permanente.
- Campos `status`, `ministrou_em`, `criado_em` e `atualizado_em`.
- Status técnicos: `PREVISTO`, `MINISTROU` e `NAO_MINISTROU`. A distinção é
  necessária para que uma indicação ou substituição não vire histórico.
- Uma sessão suporta múltiplas entradas. A mesma sessão não repete o mesmo
  `PerfilAlpinista`; nomes externos iguais não recebem unicidade automática,
  pois homônimos podem representar pessoas diferentes.
- O histórico canônico consulta somente palestrantes `MINISTROU` em sessões
  `REALIZADA` e projeta perfil/Pessoa, snapshot do título e Encontro. Não será
  criada uma terceira tabela ou cópia no Alpinista.

### Constraints e índices de banco

- Checks locais para choices válidos de tipo e status.
- Coerência de `SessaoFormativa`: `REALIZADA` exige `realizada_em`; estados
  não realizados mantêm esse timestamp nulo.
- XOR em `PalestranteSessao`: exatamente um entre `perfil_alpinista` não nulo
  e `nome_externo` não vazio.
- Coerência do palestrante: `MINISTROU` exige `ministrou_em`; os demais estados
  mantêm esse timestamp nulo.
- `UniqueConstraint` condicional para
  `sessao_formativa/perfil_alpinista` quando o perfil estiver preenchido.
- Índices para `SessaoFormativa(encontro, status)`,
  `SessaoFormativa(tema_codigo, status)`,
  `PalestranteSessao(sessao_formativa, status)` e
  `PalestranteSessao(perfil_alpinista, status)`.
- Banco não tentará validar registry em código, tipo do Encontro, pertencimento
  ao AVC ou texto composto por espaços; essas regras exigem objetos
  relacionados e pertencem aos services.

### Invariantes e services

- `criar_sessao_formativa(encontro, tema_codigo)` resolve o registry, valida
  tipo/conteúdo, bloqueia Acampamento e grava os snapshots.
- `alterar_tema_sessao(...)` será permitido apenas enquanto `PLANEJADA` e
  renovará os snapshots pelo registry; sessões realizadas não mudam de tema.
- `adicionar_palestrante_alpinista(sessao, perfil_alpinista)` cria apenas o
  vínculo previsto. Não cria Pessoa, Perfil, Trabalho ou Frequência.
- `adicionar_palestrante_externo(sessao, nome_externo)` normaliza nome não
  vazio e aceita somente sessões de Escalada/ESPPA; AVC permanece bloqueado.
- `remover_palestrante` será permitido apenas antes de atuação confirmada.
- `registrar_realizacao_sessao(sessao, resultados)` finaliza sessão e
  resultados individuais na mesma transação, exige ao menos um `MINISTROU` e
  é idempotente somente para repetição semanticamente idêntica.
- `cancelar_sessao_formativa` preserva sessão e palestrantes sem gerar
  histórico.
- Acampamento é rejeitado no service antes de qualquer escrita. O banco não
  imitará uma constraint atravessando a FK de Encontro.

### Regra bloqueante do AVC

- AVC aceita somente `PerfilAlpinista`; externo é rejeitado antes da escrita.
- Ao incluir o palestrante e ao confirmar `MINISTROU`, o service exige
  `TrabalhoEncontro` da mesma `Pessoa` e do mesmo Encontro, em estado
  `ALOCADO` ou `TRABALHOU`.
- Enquanto houver palestrante previsto em bate-papo de AVC, transições que
  removeriam seu trabalho operacional devem exigir antes a retirada/correção
  da indicação. Depois de `MINISTROU`, resultado `FALTOU` ou retirada fica
  bloqueado; `TRABALHOU` é o resultado coerente.
- A integração será feita por uma guarda explícita reutilizada pelos services
  de Formação e pelas transições relevantes de trabalho. Não haverá signal,
  alteração automática de `TrabalhoEncontro` nem dual-write.

### Transações e concorrência

- Todos os comandos compostos usam `transaction.atomic`.
- A ordem de locks preserva o padrão da D.3: `Pessoa`/`PerfilAlpinista`,
  `Encontro`, `TrabalhoEncontro` quando AVC, `SessaoFormativa` e, por último,
  `PalestranteSessao`, sempre por PK estável.
- `select_for_update` protege alteração/finalização da sessão, inclusão ou
  remoção concorrente do mesmo Alpinista, resultados individuais e a
  revalidação do trabalho no AVC.
- A unique constraint condicional é a defesa final contra inclusão concorrente
  do mesmo Alpinista, com `IntegrityError` traduzido para erro de domínio.
- Como múltiplas sessões do mesmo tema são permitidas, a criação concorrente
  de sessões não precisa de uma unicidade inventada.

### API e autorização previstas

- Criar `FORMATION_MANAGEMENT_ROLES` com Suporte, Diretoria e Formação. Essa
  lista não reutiliza `FICHAS_MANAGEMENT_ROLES` e mantém Fichas fora dos
  writes de palestrantes.
- A leitura formativa preservará `FORMATION_HISTORY_ROLES`: Suporte,
  Diretoria, Fichas e Formação. Fichas mantém consulta, mas não gestão.
- Superuser continua bypass técnico; usuário sem regra explícita permanece
  negado. Nenhuma capability de Formação concede escrita de Alpinista,
  equipes, Trabalho, Frequência ou saúde.
- D.4D exporá leitura com allowlist e escopo obrigatório por Encontro, além de
  serializers de comando que deleguem integralmente aos services. Não haverá
  CRUD de tema nem update/delete genérico de resultado formativo.
- O histórico do perfil preservará inicialmente o path e formato público de
  `historico-palestras`, fazendo o cutover para a projeção canônica somente
  depois da nova API validada. O filtro `palestrou` seguirá o mesmo corte.

### Compatibilidade incremental

- **EXPAND (D.4B–D.4C):** adicionar registry vazio, tabelas novas e services
  sem alterar `Palestra`, seu endpoint, filtro ou testes legados.
- **COMPAT/CUTOVER (D.4D):** expor comandos e consultas canônicas; depois de
  validá-los, trocar histórico e filtro para sessão `REALIZADA` + palestrante
  `MINISTROU`, preservando o payload público quando aplicável.
- `Palestra`, migration `0022` e contratos atuais permanecem fisicamente
  disponíveis. Novos writes não farão dual-write no model antigo.
- **DEPRECATE** ocorrerá apenas após inventário de consumidores e
  reconciliação explícita; remoção física não pertence à D.4.

### Backfill

**nenhum backfill automático nesta etapa**.

O legado tem título livre e vínculo único com Alpinista, mas não possui código
de catálogo, tipo de conteúdo confiável, sessão, múltiplos palestrantes,
externo ou evidência separada entre planejamento e atuação efetiva. A camada
de importação também não conhece palestra/quadrante. Uma futura população
exige catálogo real, mapping explícito de título para código, `Pessoa` e
`PerfilAlpinista` resolvidos, tipo de Encontro compatível e confirmação humana
de realização. Registros não reconciliados permanecem apenas no legado.

### Plano de implementação e testes

- **D.4B:** módulo de catálogo vazio, models, migration expansiva `0033`,
  constraints, índices e testes estruturais/registry; sem seed ou `RunPython`.
- **D.4C:** services transacionais, estados de realização, histórico derivado,
  guarda de AVC e testes de rollback, idempotência, concorrência, múltiplos
  palestrantes e ausência de efeitos colaterais.
- **D.4D:** API allowlisted, autorização positiva/negativa por papel, escopo de
  Encontro, auditoria por IDs, compatibilidade do path/payload histórico e
  cutover do filtro `palestrou`.
- **D.4E:** suíte completa SQLite/PostgreSQL, testes concorrentes reais,
  aplicação limpa das migrations, regressão de D.2/D.3 e fechamento.
- Todos os blocos devem provar que não criam `Frequencia`, Pessoa externa,
  Perfil, Trabalho ou vínculo de equipe e não expõem saúde.

### Pendências humanas

- Os nomes e códigos reais do catálogo continuam deliberadamente ausentes.
  Isso impede população operacional, mas não bloqueia o desenho nem a fundação
  estrutural da D.4B.
- Não existe outra decisão humana bloqueante para iniciar D.4B.

## D.4B — resultado da implementação

### Registry e models

- `core/formacao_catalogo.py` introduz `TemaFormativo` imutável, os tipos
  estruturais `PALESTRA`/`BATE_PAPO` e `TEMAS_FORMATIVOS` como mapping somente
  leitura, inicialmente vazio. Nenhum nome real, seed, tabela ou CRUD de tema
  foi criado.
- `SessaoFormativa` armazena Encontro protegido, código sem `choices`
  derivadas do registry, tipo estrutural, snapshot do título, estado,
  timestamp de realização e timestamps de auditoria.
- `PalestranteSessao` suporta múltiplas atuações por sessão e representa
  exatamente uma origem: `PerfilAlpinista` protegido ou nome externo local.
  O histórico continuará derivável da sessão realizada e da atuação
  `MINISTROU`, sem tabela duplicada.

### Migration, constraints e índices

- A migration expansiva `0033_expand_sessoes_formativas` parte da `0032` e
  cria somente as duas novas tabelas, quatro índices, checks locais e a
  unicidade condicional do palestrante interno por sessão.
- Os checks cobrem tipo e estados válidos, coerência dos timestamps de
  realização/atuação e XOR interno/externo. As FKs históricas usam `PROTECT`.
- As regras que atravessam `Encontro.tipo`, `TrabalhoEncontro`, registry ou
  autorização não foram convertidas em SQL frágil e permanecem para D.4C/D.4D.
- `Palestra` e todos os contratos legados permanecem inalterados. A migration
  não contém `RunPython`, seed, alteração destrutiva ou dual-write.
- **nenhum backfill automático nesta etapa**.

### Testes e validações

- Foram adicionados 11 testes estruturais e de migration para registry vazio
  e imutável, independência de `tema_codigo`, snapshots, estados e timestamps,
  múltiplos palestrantes, XOR, unicidade, `PROTECT`, preservação de `Palestra`
  e ausência de efeitos em `TrabalhoEncontro` e `Frequencia`.
- A migration foi testada no avanço `0032` → `0033`: o registro legado foi
  preservado e as estruturas canônicas nasceram vazias.
- Testes focados: 11 aprovados.
- Suíte backend: 392 testes executados, resultado OK, com 7 ignorados.
- `manage.py check`: sem problemas.
- `makemigrations --check --dry-run`: nenhuma mudança detectada.
- A validação usou SQLite de testes; D.4B não exigiu acesso ao PostgreSQL.

### Arquivos alterados

- `backend/core/formacao_catalogo.py`
- `backend/core/models.py`
- `backend/core/migrations/0033_expand_sessoes_formativas.py`
- `backend/core/tests/test_encontro_formacao_models.py`
- `docs/workplans/PHASE_1B_D4.md`

## D.4C.1 — catálogo real fixo

### Estrutura e conteúdo

- O registry imutável foi preenchido com 20 temas reais: nove palestras
  compartilhadas por Escalada/ESPPA e onze bate-papos exclusivos de AVC.
- `TemaFormativo` agora inclui `ordem` e `bloco`, além de código, título, tipo
  de conteúdo e tipos de Encontro. Bloco é metadado de apresentação e não foi
  ligado ao calendário institucional nem a data/horário da sessão.
- Os títulos fornecidos foram preservados literalmente. Acampamento continua
  sem tema e não há seed, tabela ou CRUD de catálogo.

### Códigos, ordens e blocos

| Catálogo | Ordem | Código | Bloco |
|---|---:|---|---|
| Palestra | 1 | `PALESTRA_SER_PESSOA` | `PRE_ESCALADA` |
| Palestra | 2 | `PALESTRA_VALORES_CONTRAVALORES` | `PRE_ESCALADA` |
| Palestra | 3 | `PALESTRA_AMOR_DE_DEUS` | `PRE_ESCALADA` |
| Palestra | 4 | `PALESTRA_JESUS_CRISTO` | `SABADO` |
| Palestra | 5 | `PALESTRA_AMOR_DE_MARIA` | `SABADO` |
| Palestra | 6 | `PALESTRA_PERDAO` | `SABADO` |
| Palestra | 7 | `PALESTRA_AMOR_SEXUALIDADE` | `DOMINGO` |
| Palestra | 8 | `PALESTRA_FAMILIA` | `DOMINGO` |
| Palestra | 9 | `PALESTRA_ESTRUTURA_MOVIMENTO` | `DOMINGO` |
| Bate-papo | 1 | `BATE_PAPO_JESUS_DEUS_HOMEM` | `PRE_AVC` |
| Bate-papo | 2 | `BATE_PAPO_DEPOIMENTO_SANTO_1` | `PRE_AVC` |
| Bate-papo | 3 | `BATE_PAPO_DEPOIMENTO_SANTO_2` | `PRE_AVC` |
| Bate-papo | 4 | `BATE_PAPO_DEPOIMENTO_SANTO_3` | `PRE_AVC` |
| Bate-papo | 5 | `BATE_PAPO_ALIANCAS_DEUS_HOMEM` | `SEXTA` |
| Bate-papo | 6 | `BATE_PAPO_SER_PROFETA` | `SEXTA` |
| Bate-papo | 7 | `BATE_PAPO_NECESSIDADES_SER_HUMANO` | `SABADO` |
| Bate-papo | 8 | `BATE_PAPO_IMPORTANCIA_SACRAMENTOS_PROFETA` | `SABADO` |
| Bate-papo | 9 | `BATE_PAPO_CAMPANHA_FRATERNIDADE` | `DOMINGO` |
| Bate-papo | 10 | `BATE_PAPO_BIOGRAFIA_SANTO` | `DOMINGO` |
| Bate-papo | 11 | `BATE_PAPO_PROFETA_IGREJA` | `DOMINGO` |

### Testes e schema

- Cinco testes dedicados validam quantidades, códigos, títulos exatos,
  unicidade de ordem, blocos, compartilhamento Escalada/ESPPA, separação do
  AVC, ausência de Acampamento, lookup e imutabilidade.
- Os testes de service deixaram de substituir o registry por catálogo
  fictício e agora exercitam os códigos reais. O único override restante
  simula uma futura mudança de título para provar a preservação do snapshot.
- Testes focados de catálogo, models e services: 36 testes, resultado OK, com
  2 testes de concorrência PostgreSQL ignorados conforme condição.
- Suíte backend: 417 testes executados, resultado OK, com 9 ignorados.
- `manage.py check` e `git diff --check`: sem problemas.
- Nenhuma alteração de model ou migration foi necessária; o autodetector não
  apontou mudança de schema.

### Arquivos alterados

- `backend/core/formacao_catalogo.py`
- `backend/core/tests/test_formacao_catalogo.py`
- `backend/core/tests/test_encontro_formacao_models.py`
- `backend/core/tests/test_encontro_formacao_services.py`
- `docs/domain/ENCOUNTER_FORMATION.md`
- `docs/workplans/PHASE_1B_D4.md`

## D.4C — resultado da implementação

### Services e transições

- `core/services/formacoes.py` centraliza criação e alteração de tema de
  sessão planejada, inclusão e remoção de palestrantes, cancelamento,
  realização com resultados individuais e consulta do histórico derivado.
- A criação resolve exclusivamente o registry e copia código, tipo e título
  para o snapshot. Código ausente ou incompatível não vira texto livre.
- Sessões passam de `PLANEJADA` para `REALIZADA` ou `CANCELADA`. A realização
  exige resultado para toda a composição e ao menos um `MINISTROU`; repetição
  semanticamente idêntica é idempotente e resultado divergente é rejeitado.
- Palestrantes permanecem `PREVISTO`, `MINISTROU` ou `NAO_MINISTROU` conforme
  o resultado. Remoção só ocorre antes da atuação e em sessão planejada.

### Regras por tipo e histórico

- Escalada e ESPPA aceitam somente temas `PALESTRA` aplicáveis e podem ter
  Alpinista ou externo. Externo é apenas nome normalizado na sessão e não cria
  Pessoa, Perfil, User, Trabalho ou Frequência.
- AVC aceita somente `BATE_PAPO`, bloqueia externo e exige
  `TrabalhoEncontro` da mesma Pessoa e do mesmo Encontro em `ALOCADO` ou
  `TRABALHOU`, tanto na indicação quanto na realização.
- As transições de trabalho agora usam uma guarda explícita: palestrante
  previsto ou efetivo do AVC não pode ser desalocado, retirado, substituído ou
  receber `FALTOU`. A guarda não altera o trabalho e não usa signal.
- Acampamento é bloqueado antes da criação da sessão.
- O histórico canônico é uma consulta sobre palestrante interno `MINISTROU`
  em sessão `REALIZADA`, carregando snapshot e Encontro. Sessão planejada,
  `NAO_MINISTROU`, externo, `Palestra` legado e `TrabalhoEncontro` não entram.

### Transações e concorrência

- Comandos de escrita usam `transaction.atomic` e locks pessimistas sobre o
  contexto necessário, seguindo Pessoa/Perfil, Encontro, Trabalho no AVC,
  Sessão e Palestrante.
- A composição é revalidada sob lock na realização; alteração concorrente
  detectada exige nova tentativa. A unicidade do palestrante interno continua
  como defesa final no banco e `IntegrityError` é traduzido.
- Dois testes de corrida real foram adicionados e condicionados a PostgreSQL:
  inclusão simultânea do mesmo Alpinista e realizações simultâneas com
  resultados divergentes. A execução real permanece para D.4E.

### Testes e validações

- Foram adicionados 20 testes de service: 18 executados com sucesso em SQLite
  e 2 ignorados por exigirem PostgreSQL real.
- Eles cobrem registry e snapshots, múltiplos palestrantes, regras por tipo,
  vínculo correto do AVC, realização, idempotência, cancelamento, histórico,
  isolamento do legado, ausência de efeitos colaterais e rollback após falha
  intermediária.
- Regressão focada com Formação e Trabalho: 42 testes, resultado OK, com 7
  ignorados conforme suas condições.
- Suíte backend: 412 testes executados, resultado OK, com 9 ignorados.
- `manage.py check`: sem problemas.
- `makemigrations --check --dry-run`: nenhuma mudança detectada; D.4C não
  criou migration.

### Arquivos alterados

- `backend/core/services/formacoes.py`
- `backend/core/services/trabalhos.py`
- `backend/core/tests/test_encontro_formacao_services.py`
- `docs/workplans/PHASE_1B_D4.md`

## D.4D — resultado da implementação

### Endpoints e contratos

- `GET /api/catalogo-formacao/?encontro={id}` lista somente o catálogo
  aplicável, com código, título, tipo, ordem e bloco. Não existe write ou CRUD
  de tema.
- `GET|POST /api/sessoes-formativas/` exige escopo de Encontro na listagem e
  cria sessões exclusivamente pelo service. `GET
  /api/sessoes-formativas/{id}/` expõe contrato allowlisted com palestrantes.
- Actions explícitas oferecem `alterar-tema`, `cancelar`, `palestrantes`,
  `adicionar-palestrante`, `remover-palestrante` e `realizar`. Não existem
  update ou delete genéricos.
- `realizar` recebe o resultado de toda a composição e delega ao comando
  transacional da D.4C, que registra `MINISTROU`/`NAO_MINISTROU` e finaliza a
  sessão atomicamente.
- `GET /api/alpinistas/{id}/historico-formativo/` expõe somente histórico
  canônico derivado com Alpinista, tema e Encontro, sem dados sensíveis.
- Erros de domínio são traduzidos para `400`; nested mismatch de palestrante
  retorna `404`; métodos genéricos não suportados retornam `405`.

### Autorização

- `FORMATION_MANAGEMENT_ROLES` contém Suporte, Diretoria e Formação.
  Superuser continua bypass técnico e não foi convertido em papel de negócio.
- `FORMATION_HISTORY_ROLES` preserva leitura para Suporte, Diretoria, Fichas e
  Formação. Fichas não recebe nenhum comando de gestão.
- Os demais papéis permanecem negados por default. Formação não recebeu
  gestão de Alpinista, Trabalho, equipe, Frequência ou saúde.
- A matriz de autorização foi atualizada para separar formalmente leitura e
  gestão de Formação em Encontros.

### Compatibilidade e cutover lógico

- Novos writes existem somente na API canônica e não criam `Palestra`,
  `TrabalhoEncontro`, `Frequencia`, Pessoa externa ou User.
- `Palestra` e `GET /api/alpinistas/{id}/historico-palestras/` foram
  preservados como leitura legada. O filtro legado `palestrou` também não foi
  removido nesta etapa.
- O histórico novo usa path próprio e somente a projeção canônica. Não há
  união silenciosa entre fontes, dual-write, conversão, backfill ou migration
  destrutiva.
- A retirada do endpoint/model legado e o cutover de consumidores antigos
  dependem de inventário/reconciliação futuros.

### Testes e validações

- Foram adicionados 12 testes de API cobrindo catálogo dos quatro tipos,
  escopo, allowlists, criação/listagem, papéis positivos e negativos,
  edição/cancelamento, múltiplos palestrantes, nested mismatch, externo,
  bloqueio/aceite do AVC, realização, histórico e compatibilidade legada.
- A regressão focada de API, serializers e autorização executou 105 testes com
  resultado OK.
- A suíte backend executou 429 testes com resultado OK e 9 ignorados.
- `manage.py check` e `git diff --check`: sem problemas.
- `makemigrations --check --dry-run`: nenhuma mudança detectada; D.4D não
  criou migration.

### Arquivos alterados

- `backend/core/roles.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/urls.py`
- `backend/core/tests/test_encontro_formacao_api.py`
- `backend/core/tests/test_serializer_contracts.py`
- `docs/AUTHORIZATION_MATRIX.md`
- `docs/workplans/PHASE_1B_D4.md`

## Decisões da fase

- As regras de produto fechadas permanecem no documento de domínio; o desenho
  técnico aprovado e suas evidências estão no relatório da D.4A acima.
- Catálogo é código imutável, não tabela nem `choices` de model. Sessão e
  atuação individual preservam snapshots e estados necessários ao histórico.
- `PerfilAlpinista` identifica o palestrante interno; externo permanece apenas
  nome local da sessão e é proibido no AVC.

## Descobertas técnicas

O inventário completo está no relatório da D.4A. O legado implementado se
resume ao model `Palestra`, action de histórico e filtro `palestrou`; não há
write API, service, admin, transformador legado ou consumidor frontend fonte.

## Compatibilidade com legado

- `Palestra`, seu path histórico e o filtro legado permanecem disponíveis
  somente para leitura compatível.
- Novos writes são exclusivamente canônicos e sem dual-write.
- O histórico canônico possui path separado; remoção física, reconciliação e
  cutover dos consumidores antigos ficam para etapa futura explícita.
- **nenhum backfill automático nesta etapa**.

## Migrations

- A migration anterior foi confirmada por código como
  `0032_vinculousuariopessoa`.
- `0033_expand_sessoes_formativas` foi criada de forma exclusivamente
  expansiva com `SessaoFormativa` e `PalestranteSessao`.
- Não há tabela/seed de catálogo, `RunPython`, alteração ou remoção do model
  `Palestra`.

## Testes e validações

- A D.4A foi exclusivamente documental. Na D.4B, os 11 testes focados
  passaram; a suíte backend executou 392 testes com resultado OK e 7 ignorados
  conforme suas condições próprias.
- `check` e `makemigrations --check --dry-run` passaram sem apontamentos.
- Na D.4C, 20 testes de service foram adicionados; a suíte backend passou com
  412 testes e 9 skips. Os dois testes novos de concorrência real estão
  condicionados a PostgreSQL e permanecem reservados ao fechamento D.4E.
- Na D.4D, 12 testes de API foram adicionados e a suíte backend passou com 429
  testes e 9 skips. A regressão focada de API/contratos/autorização passou com
  105 testes.

## Débitos

- Execução PostgreSQL dos testes de inclusão e realização concorrentes,
  regressão final e fechamento da D.4E.
- Reconciliação humana do legado e futura depreciação do model `Palestra`.
- Inventário de consumidores externos ao repositório antes da remoção física.
- Migração de qualquer consumidor frontend legado para a API canônica.

## Arquivos relevantes

- `docs/domain/ENCOUNTER_FORMATION.md`
- `docs/workplans/PHASE_1B_D4.md`
- `docs/domain/ENCOUNTER_WORK.md`, somente para dependências diretas de
  `TrabalhoEncontro`, especialmente no AVC.
- `docs/AUTHORIZATION_MATRIX.md`, somente quando a tarefa envolver permissões.
- `backend/core/models.py`
- `backend/core/formacao_catalogo.py`
- `backend/core/tests/test_formacao_catalogo.py`
- `backend/core/migrations/0033_expand_sessoes_formativas.py`
- `backend/core/tests/test_encontro_formacao_models.py`
- `backend/core/services/formacoes.py`
- `backend/core/tests/test_encontro_formacao_services.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/permissions.py`
- `backend/core/roles.py`
- `backend/core/services/trabalhos.py`
- `backend/core/migrations/0001_initial.py`
- `backend/core/migrations/0006_funcaoencontro_encontro_participantes_and_more.py`
- `backend/core/migrations/0022_palestra.py`
- `backend/core/migrations/0032_vinculousuariopessoa.py`
- `backend/core/tests/test_authorization.py`
- `backend/core/tests/test_authorization_paths.py`
- `backend/core/tests/test_encontro_formacao_api.py`
- `backend/core/tests/test_serializer_contracts.py`
- `backend/core/legacy/`

## Próximo passo

D.4E — executar os testes de concorrência em PostgreSQL real, regressão final,
conferência das migrations e fechamento da Fase 1B.3D.4.

## Histórico de execução

- 2026-10-05 — Vault da Fase 1B.3D.4 preparado. Regras estáveis separadas do
  relatório vivo; nenhuma análise técnica, implementação, migration ou acesso
  ao PostgreSQL foi realizado.
- 2026-10-05 — D.4A concluída por inspeção estática. O legado e seus contratos
  foram inventariados, o desenho do catálogo/models/services/compatibilidade
  foi fechado, nenhum backfill seguro foi identificado e D.4B foi definido
  como próximo bloco.
- 2026-10-05 — D.4B concluída com registry estrutural vazio, models,
  migration expansiva `0033`, constraints, índices e 11 testes novos. A suíte
  backend de 392 testes, os checks do Django e o autodetector de migrations
  passaram; D.4C foi definida como próximo bloco.
- 2026-10-05 — D.4C concluída com services transacionais, regras por tipo,
  guarda do trabalho no AVC e histórico derivado. A suíte backend executou
  412 testes com resultado OK e 9 skips; dois testes de concorrência real
  ficaram condicionados ao PostgreSQL da D.4E, e D.4D foi definido como
  próximo bloco.
- 2026-10-05 — D.4C.1 preencheu o registry com nove palestras de
  Escalada/ESPPA e onze bate-papos de AVC, incluindo ordem e bloco. Os
  services passaram a ser testados contra o catálogo real, sem model,
  migration, seed ou banco, e D.4D permaneceu como próximo bloco.
- 2026-10-05 — D.4D concluiu a API canônica, autorização por papel, histórico
  derivado e compatibilidade de leitura do legado. A suíte backend executou
  429 testes com resultado OK e 9 skips, nenhuma migration foi gerada e D.4E
  foi definido como próximo bloco.
