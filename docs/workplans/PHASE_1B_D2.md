# Fase 1B.3D.2 — Inscrição, Convite e Participação

## Status geral

D.2A, D.2B, D.2C e D.2D concluídas. A fundação estrutural, os services
transacionais e o cutover lógico foram implementados sem backfill e sem
remoção física dos contratos legados. D.2E é o próximo bloco.

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

## Blocos

### D.2A — Análise, legado e desenho técnico

Status: concluída.

### D.2B — Models, migration e constraints

Status: concluída.

### D.2C — Services e regras transacionais

Status: concluída.

### D.2D — Compatibilidade e cutover legado

Status: concluída.

### D.2E — Regressão, documentação e fechamento

Status: pendente.

## Decisões da fase

As decisões de domínio já congeladas estão em
[[../domain/ENCOUNTER_PARTICIPATION]]. A fase deve implementá-las sem duplicar
essas regras neste relatório vivo.

### Fronteira com o model legado

- O `ParticipacaoEncontro` atual não representa o novo resultado de
  participação: ele mistura encontristas confirmados e integrantes de equipe,
  exige `Alpinista` e `FuncaoEncontro` e alimenta contratos ativos.
- Na expansão, o model atual será renomeado no estado Django para
  `VinculoEncontroLegado`, mantendo a tabela física
  `core_participacaoencontro`, seus dados, constraints e o endpoint
  `/api/participacoes-encontros/`.
- `Encontro.participantes` continuará temporariamente apontando para
  `VinculoEncontroLegado`. O nome, payload e comportamento da API antiga não
  mudam na D.2B.
- O novo model de domínio terá o nome `ParticipacaoEncontro` e tabela física
  própria, `core_participacaoencontro_resultado`. A separação evita misturar
  equipe, confirmação e resultado real na mesma linha.

### Inscricao

Campos implementados:

- `pessoa`: FK obrigatória para `Pessoa`, `on_delete=PROTECT`;
- `tipo`: choices limitadas a `Encontro.Tipo.ESCALADA` e
  `Encontro.Tipo.ESPPA`;
- `status`: `PENDENTE` ou `CUMPRIDA`, com default `PENDENTE`;
- `criada_em` e `atualizada_em`;
- `cumprida_em`, nulo enquanto pendente.

Invariantes de banco:

- unique constraint parcial em `(pessoa, tipo)` quando `status=PENDENTE`;
- check constraints para os valores aceitos de `tipo` e `status`;
- check que mantém `cumprida_em` nulo em `PENDENTE` e preenchido em
  `CUMPRIDA`.

Índices:

- `(tipo, status, criada_em)` para a fila humana;
- `(pessoa, tipo, status)` para histórico e elegibilidade.

### ConviteEncontro

Campos implementados:

- `pessoa`: FK obrigatória para `Pessoa`, `on_delete=PROTECT`;
- `encontro`: FK obrigatória para `Encontro`, `on_delete=PROTECT`;
- `finalidade`: `PARTICIPAR` ou `TRABALHAR`;
- `status`: `CONVIDADO`, `CONFIRMADO`, `RECUSADO` ou `SEM_RESPOSTA`, com
  default `CONVIDADO`;
- `inscricao`: FK opcional para `Inscricao`, `on_delete=PROTECT`;
- `criado_em` e `atualizado_em`.

Invariantes de banco:

- unique constraint em `(pessoa, encontro, finalidade)`;
- check constraints para os valores aceitos de `finalidade` e `status`;
- check que impede inscrição associada quando a finalidade é `TRABALHAR`.

Índices:

- `(encontro, finalidade, status)` para gestão por edição;
- `(pessoa, status)` para histórico e filas pessoais.

### ParticipacaoEncontro

Campos implementados:

- `pessoa`: FK obrigatória para `Pessoa`, `on_delete=PROTECT`;
- `encontro`: FK obrigatória para `Encontro`, `on_delete=PROTECT`;
- `convite`: one-to-one opcional para `ConviteEncontro`,
  `on_delete=PROTECT`;
- `resultado`: `CONCLUIU`, `FALTOU` ou `DESISTIU`;
- `tipo_encontro`: snapshot obrigatório e não editável de `Encontro.tipo`;
- `registrada_em` e `atualizada_em`.

O snapshot de tipo é necessário porque PostgreSQL não permite que uma unique
constraint use `Encontro.tipo` por join. Ele permite preservar no banco a
conclusão única mesmo se o Encontro for alterado indevidamente depois.

Invariantes de banco:

- unique constraint em `(pessoa, encontro)`;
- unique constraint parcial em `(pessoa, tipo_encontro)` quando
  `resultado=CONCLUIU`;
- check constraints para os valores aceitos de `resultado` e
  `tipo_encontro`.

Índices:

- `(encontro, resultado)` para fechamento da edição;
- `(pessoa, resultado)` para histórico e elegibilidade.

### Transições

- `Inscricao`: `PENDENTE → CUMPRIDA`, exclusivamente pelo service que registra
  uma conclusão válida de Escalada ou ESPPA. Não há transição reversa comum.
- `ConviteEncontro`: `CONVIDADO → CONFIRMADO | RECUSADO | SEM_RESPOSTA`.
  Correções posteriores exigem comando explícito, auditoria e bloqueio da
  linha; não são updates genéricos.
- `ParticipacaoEncontro` nasce com um resultado real. `FALTOU` ou `DESISTIU`
  pode ser corrigido para `CONCLUIU` pelo service auditado. `CONCLUIU` não pode
  ser rebaixado nem removido pelo fluxo comum porque seus efeitos de domínio
  são permanentes.

### Invariantes dos services

Pertencem aos services, pois dependem de outras linhas ou de regra contextual:

- a Pessoa, o tipo da inscrição e o tipo do Encontro devem ser compatíveis;
- convite ligado a inscrição deve usar a mesma Pessoa e o mesmo tipo;
- AVC e Acampamento não aceitam inscrição no convite;
- convite `TRABALHAR` não usa inscrição nem executa elegibilidade de
  participante;
- idade de Escalada e ESPPA gera aviso, nunca bloqueio estrutural;
- AVC exige conclusão de Escalada e ano elegível igual ou posterior ao ano da
  Escalada mais dois;
- Acampamento exige conclusão de Escalada;
- `tipo_encontro` é copiado de `Encontro.tipo` e não é aceito do payload;
- apenas `CONCLUIU` em Escalada ou ESPPA executa
  `PerfilAlpinista.objects.get_or_create(pessoa=...)`;
- a mesma operação marca a inscrição pendente correspondente como
  `CUMPRIDA`, quando ela existir;
- `FALTOU`, `DESISTIU`, convite e confirmação não criam perfil e não alteram
  `Frequencia`;
- o tipo do Encontro não pode ser alterado depois de existir convite ou novo
  resultado de participação;
- os novos models não terão escrita por `ModelViewSet` genérico; serializers
  de comando devem delegar aos services transacionais.

### Concorrência e atomicidade

- Criação de inscrição bloqueia `Pessoa` com `select_for_update`, verifica
  conclusão anterior e pendência e confia também na unique constraint parcial.
- Criação/transição de convite bloqueia `Pessoa`, `Encontro`, convite existente
  e inscrição associada, sempre nessa ordem.
- Registro ou correção de resultado usa `transaction.atomic`, bloqueia
  `Pessoa`, `Encontro`, convite e inscrição na mesma ordem e só então grava
  participação, perfil e cumprimento da inscrição.
- A unique constraint parcial de conclusão é a proteção final contra duas
  transações concorrentes. `IntegrityError` deve ser convertido em erro de
  validação estável, sem resultado parcial.
- Services devem buscar e bloquear as linhas novamente por PK; não devem
  confiar em instâncias previamente carregadas.

## Descobertas técnicas

### Fluxo atual

- `core.models.ParticipacaoEncontro` aponta para `Alpinista`, não para
  `Pessoa`, exige uma `FuncaoEncontro` e possui apenas `cor_grupo` e
  `coordenador`; não registra confirmação nem resultado real.
- A constraint `unico_alpinista_por_encontro` impede que a mesma pessoa seja
  encontrista e equipe no mesmo Encontro, reproduzindo a mistura conceitual do
  model.
- O signal `core.models.alpinista_ativo_automatico` altera qualquer novo
  vínculo para `Alpinista.status=ativo`, inclusive inclusão em equipe. Esta é
  a localização exata da ativação prematura conhecida.
- A action `efetivar-encontristas` cria o vínculo legado dentro de
  `transaction.atomic`; o signal ativa o Alpinista e a view pode sobrescrever
  o resultado para `confirmado` quando o status anterior era `pendente`.
- A action `remover-encontristas` apaga o vínculo e rebaixa `ativo` ou
  `confirmado` para `pendente` sem verificar outros Encontros ou evidências de
  conclusão.
- O CRUD direto de `/api/participacoes-encontros/` também dispara o signal. O
  serializer tenta impedir repetição do mesmo tipo para encontrista com uma
  consulta `exists()`, mas a regra não é protegida no banco nem contra
  concorrência.
- A API de criação de `Alpinista` ainda cria diretamente o model legado com
  status padrão `pendente`; não cria nem vincula `Pessoa`. O backfill 0026
  vinculou apenas registros existentes quando a migration foi executada.
- `PerfilAlpinista` existe, mas nenhum fluxo atual de Encontro o cria.

### Dependências do contrato legado

- O frontend usa `/participacoes-encontros/` para listar encontristas e
  equipes, criar/remover equipe e alternar coordenador.
- O frontend usa `efetivar-encontristas` e `remover-encontristas` para mover
  registros entre a lista de `Alpinista.status=pendente` e a lista tratada como
  confirmada.
- `AlpinistaCompletoSerializer` deriva `encontros_realizados` e
  `historico_equipes` do mesmo model legado; histórico de violeiro também
  depende dele.
- `Encontro.participantes`, serializers, viewsets, admin, auditoria, filtros e
  testes de autorização referenciam a relação antiga. Ela não pode ser
  removida ou redirecionada na migration expansiva.

### Legado externo

- `encontros_alpinista` produz apenas candidato `ENCONTRISTA`; sua presença não
  distingue `CONCLUIU`, `FALTOU`, `DESISTIU` ou mera confirmação.
- `encontro_equipe` representa trabalho e não pode virar resultado de
  participação ou convite confirmado automaticamente.
- O validador legado já detecta órfãos, duplicatas e conflito entre as duas
  classificações, mas não grava no ORM.
- `ele_recebe_inscricao` continua `DEFERRED`: nome não pode ser casado
  automaticamente, o vocabulário de validação é desconhecido e módulos ainda
  não possuem mapping seguro.
- `NO_ESCALADA`, `NO_ESPPA`, `NO_AVC` e `NO_ACAMPAMENTO` são evidências
  textuais diferidas, não prova inequívoca de conclusão.

## Compatibilidade com legado

### EXPAND — D.2B

- As três tabelas novas e suas constraints foram adicionadas vazias.
- O model antigo foi renomeado somente no estado Django para
  `VinculoEncontroLegado`, preservando sua tabela física e a API existente.
- Payloads, rotas, históricos e comportamento do frontend não foram alterados.
- O signal legado foi preservado como dívida isolada.

### Services — D.2C

- Foram implementados `criar_inscricao`, `criar_convite`,
  `responder_convite` e `registrar_resultado_participacao`, exclusivamente
  sobre os models novos.
- Os comandos reconsultam e bloqueiam as entidades persistidas, validam as
  transições de domínio e convertem conflitos de integridade esperados em
  `ValidationError` estável.
- Criação repetida do mesmo convite, repetição da mesma resposta e repetição
  do mesmo resultado são idempotentes. Uma resposta terminal divergente ou um
  resultado real divergente são rejeitados; `FALTOU` e `DESISTIU` ainda podem
  ser corrigidos para `CONCLUIU`.
- `CONFIRMADO`, `RECUSADO` e `SEM_RESPOSTA` não criam resultado. `FALTOU` e
  `DESISTIU` preservam a inscrição pendente e permitem tentativa em edição
  futura. Somente `CONCLUIU` em Escalada ou ESPPA cumpre a inscrição pendente
  correspondente e cria, por `get_or_create`, o `PerfilAlpinista` ausente.
- AVC e Acampamento continuam sem inscrição, exigem a conclusão prévia de
  Escalada e não criam perfil; o AVC aplica também a janela anual aprovada.
- Nenhum comando cria `Frequencia` ou escreve na relação legada.
- Não fazer dual write a partir das actions antigas: efetivação e remoção não
  possuem semântica suficiente para inferir convite ou resultado novo.
- Manter qualquer endpoint novo sob default deny e, enquanto não houver
  decisão específica de captação anônima, limitar gestão às roles já
  autorizadas para Encontros e participações.

### COMPAT e CUTOVER — D.2D

- O signal `alpinista_ativo_automatico` foi removido. Criar um
  `VinculoEncontroLegado`, seja de encontrista ou equipe, não altera mais
  `Alpinista.status` e não cria perfil, resultado ou frequência.
- `efetivar-encontristas` continua criando o vínculo legado e preserva rota,
  payload, resposta, atomicidade e auditoria, mas não promove mais o status
  legado para `confirmado` ou `ativo`.
- `remover-encontristas` continua removendo somente o vínculo legado e
  preserva rota, payload, resposta, atomicidade e auditoria, mas não rebaixa
  mais o status do Alpinista.
- O CRUD `/api/participacoes-encontros/` e seus contratos de leitura foram
  preservados. Sua validação deixou de interpretar outro vínculo de mesmo tipo
  como conclusão, pois o registro antigo não distingue confirmação, falta,
  desistência ou conclusão.
- Foram adicionados endpoints de comando, sem CRUD genérico de leitura, para
  inscrição, convite, resposta e resultado:
  - `POST /api/inscricoes-encontros/`;
  - `POST /api/convites-encontros/`;
  - `POST /api/convites-encontros/{id}/responder/`;
  - `POST /api/resultados-participacoes-encontros/`.
- Os serializers de comando limitam seus campos e delegam integralmente aos
  quatro services da D.2C. Erros de domínio são expostos como `400`, e as
  escritas mantêm auditoria transacional por identificador.
- Os comandos novos reutilizam os papéis administrativos já autorizados para
  Encontros e participações; nenhuma permissão foi ampliada.
- Não existe dual-write entre o vínculo antigo e os models novos. Os fluxos
  antigos não possuem evidência inequívoca para produzir inscrição, convite
  ou resultado, e os comandos novos não fabricam vínculo legado.
- O frontend e as leituras históricas continuam usando o contrato legado até
  migração posterior por fluxo.
- Não converter automaticamente status legado em frequência, perfil ou
  conclusão.

## Migrations

- Migration criada: `0029_expand_inscricao_convite_participacao`.
- A migration usa separação de estado/banco para representar
  `VinculoEncontroLegado` sem renomear a tabela física existente.
- Foram criadas somente as tabelas novas, FKs, índices, checks e unique
  constraints descritos neste workplan.
- Não há `RunPython`; a migration não altera linhas legadas, não cria
  `PerfilAlpinista`, não muda `Alpinista.status` e não remove o signal.
- A reversão remove apenas as tabelas novas e restaura o nome de estado do
  model legado; os dados anteriores permanecem intactos.
- Nenhum backfill automático nesta etapa.

## Testes e validações

Resultados da D.2B:

- 14 testes focados de models, constraints e migration: aprovados;
- suíte backend completa: 266 testes aprovados;
- `manage.py check --settings=setup.test_settings`: aprovado;
- `makemigrations --check --dry-run --settings=setup.test_settings`: nenhuma
  mudança detectada;
- `sqlmigrate core 0029 --settings=setup.test_settings`: somente criação de
  tabelas e índices novos; a separação do model legado é `no-op` no banco;
- PostgreSQL local não foi acessado e nenhum banco persistente foi alterado.

Cobertura adicionada:

- testes de model para choices, checks, `on_delete=PROTECT`, unicidade de
  pendência, convite, resultado por Encontro e conclusão por tipo;
- testes de migration forward/reverse garantindo tabela legada e linhas
  intactas, tabelas novas vazias e ausência de data migration;
- confirmação estrutural de que convite/participação não criam
  `PerfilAlpinista` nem `Frequencia` sem services;
- regressão integral das actions, endpoint, históricos e permissões legadas
  pela suíte backend completa.

Permanecem para o fechamento a concorrência real em PostgreSQL e a migração
futura dos consumidores frontend ainda apoiados no contrato legado.

Resultados da D.2C:

- 21 testes focados dos services: 19 aprovados no SQLite e 2 testes de corrida
  corretamente ignorados nesse backend por exigirem PostgreSQL;
- suíte backend completa: 287 testes aprovados, com os mesmos 2 skips
  PostgreSQL;
- `manage.py check --settings=setup.test_settings`: aprovado;
- `makemigrations --check --dry-run --settings=setup.test_settings`: nenhuma
  mudança detectada;
- a execução pontual dos 2 testes no PostgreSQL foi tentada fora da sandbox,
  após aprovação, mas o usuário `sia_dev` não possui permissão para criar o
  banco descartável `test_sia_dev`;
- a tentativa segura de provisionar somente `test_sia_dev` com o usuário
  administrativo não prosseguiu porque `sudo` exige senha. O banco persistente
  `sia_dev` não foi usado nem alterado.

Cobertura adicionada na D.2C:

- criação e duplicidade de inscrição de Escalada/ESPPA;
- convite associado, convite direto de AVC e respostas terminais;
- separação entre confirmação e resultado real;
- cumprimento ou preservação coerente da inscrição para cada resultado;
- conclusão única, correção para conclusão e tentativa futura após falta ou
  desistência;
- criação idempotente de perfil apenas nos tipos elegíveis e ausência de
  `Frequencia`;
- rollback integral diante de falha intermediária;
- dois testes `TransactionTestCase` com conexões independentes para inscrição
  e conclusão concorrentes, prontos para PostgreSQL.

Resultados da D.2D:

- 9 testes novos de API e compatibilidade aprovados;
- suíte backend completa: 296 testes aprovados, com os 2 skips PostgreSQL já
  registrados para D.2E;
- `manage.py check --settings=setup.test_settings`: aprovado;
- `makemigrations --check --dry-run --settings=setup.test_settings`: nenhuma
  mudança detectada;
- nenhum acesso ao PostgreSQL local foi necessário e nenhuma migration foi
  criada ou alterada.

Cobertura adicionada ou ajustada na D.2D:

- confirmação separada de resultado e sem criação de perfil ou frequência;
- `CONCLUIU`, `FALTOU`, `DESISTIU`, AVC e Acampamento através da API de
  comando;
- comprovação por mocks de que os writes novos delegam aos services;
- ausência da ativação prematura em criação direta, efetivação e remoção de
  vínculo legado;
- preservação dos payloads, rotas, respostas, atomicidade e autorização do
  contrato antigo;
- repetição de vínculo legado por tipo sem inferência de conclusão;
- endpoints de comando sem listagem ou update genéricos e sob default deny.

## Débitos

- Alpinistas criados depois da migration 0026 podem não possuir `pessoa_id`;
  nenhuma associação deve ser inventada. Esses casos precisam de profiling e
  reconciliação antes de usar os services novos.
- A tabela real `ele_recebe_inscricao` ainda precisa de profiling de módulos,
  validação, duplicidade, identidade e qualidade temporal.
- A abertura de captação anônima não está autorizada pela matriz atual e fica
  fora da expansão de schema. Até decisão e threat model próprios, prevalece
  default deny; isso não bloqueia D.2B.
- O domínio completo de equipes continua fora da D.2, por isso o vínculo
  legado não pode ser eliminado no fechamento deste núcleo.
- `Alpinista.status` permanece contrato legado e não deve ser usado como fonte
  de conclusão, perfil ou frequência.
- A data histórica de elegibilidade deve usar o calendário oficial vigente do
  Encontro; `data_referencia` permanece somente como fallback de
  compatibilidade enquanto o débito da D.1 existir.
- A semântica de concorrência de `select_for_update` será validada em
  PostgreSQL na D.2E. Os testes já existem, mas o ambiente precisa provisionar
  um banco de testes separado ou conceder `CREATEDB` ao usuário de teste; não
  se deve executar o runner sobre `sia_dev`.
- Avisos etários de Escalada e ESPPA permanecem responsabilidade da futura
  camada de comando/apresentação: são consultivos e não interferem nas
  transações implementadas.
- `Alpinista.status` e o vínculo legado continuam necessários para o frontend
  e históricos atuais, mas ficaram isolados de confirmação, resultado e
  criação de `PerfilAlpinista`. Sua depreciação física depende da migração dos
  consumidores na D.2E ou em plano posterior explícito.
- Alpinistas legados sem `pessoa_id` não podem usar os comandos novos até
  reconciliação segura; o cutover não cria associações heurísticas.

## Pendências humanas

Nenhuma decisão de produto pendente bloqueia D.2D. Profiling de dados reais,
eventual autorização para captação anônima e provisionamento do banco
descartável de testes são trabalhos futuros com evidência própria, não
pressupostos do cutover lógico.

## Arquivos relevantes

- `docs/domain/ENCOUNTER_PARTICIPATION.md`
- `docs/workplans/PHASE_1B_D2.md`
- `backend/core/models.py`
- `backend/core/services/encontros.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/urls.py`
- `backend/core/migrations/0006_funcaoencontro_encontro_participantes_and_more.py`
- `backend/core/migrations/0007_alter_participacaoencontro_unique_together_and_more.py`
- `backend/core/migrations/0025_expand_pessoa.py`
- `backend/core/migrations/0026_backfill_pessoa.py`
- `backend/core/legacy/contracts.py`
- `backend/core/legacy/transformers/participacoes.py`
- `backend/core/legacy/FIELD_MAPPING.md`
- `backend/core/tests/test_participacoes.py`
- `backend/core/tests/test_legacy_participations.py`
- `backend/core/migrations/0029_expand_inscricao_convite_participacao.py`
- `backend/core/tests/test_encontro_participacao_models.py`
- `backend/core/services/participacoes.py`
- `backend/core/tests/test_encontro_participacao_services.py`
- `frontend/src/app/(painel)/encontros/[id]/page.tsx`
- `frontend/src/lib/sia-profile-contracts.ts`

## Arquivos alterados na D.2B

- `backend/core/models.py`
- `backend/core/migrations/0029_expand_inscricao_convite_participacao.py`
- `backend/core/tests/test_encontro_participacao_models.py`
- `backend/core/admin.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/tests/test_alpinistas.py`
- `backend/core/tests/test_authorization.py`
- `backend/core/tests/test_participacoes.py`
- `backend/core/tests/test_serializer_contracts.py`
- `docs/workplans/PHASE_1B_D2.md`

## Arquivos alterados na D.2C

- `backend/core/services/participacoes.py`
- `backend/core/tests/test_encontro_participacao_services.py`
- `docs/workplans/PHASE_1B_D2.md`

## Arquivos alterados na D.2D

- `backend/core/models.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/urls.py`
- `backend/core/tests/test_encontro_participacao_api.py`
- `backend/core/tests/test_participacoes.py`
- `backend/core/tests/test_alpinistas.py`
- `backend/core/tests/test_authorization.py`
- `docs/workplans/PHASE_1B_D2.md`

## Próximo passo

Executar D.2E — regressão final, validação PostgreSQL e fechamento da D.2,
mantendo a estrutura legada até que todos os consumidores possam ser
depreciados com segurança.

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
  D.2A permanecia pendente.
- 2026-10-02 — D.2A concluída por inspeção estática. Localizados o signal de
  ativação prematura, a mistura entre encontrista/equipe no model atual e os
  consumidores do contrato legado. Fechado o desenho expansivo, sem acesso ao
  PostgreSQL e sem backfill automático.
- 2026-10-02 — D.2B concluída. Implementados `Inscricao`, `ConviteEncontro` e
  o novo `ParticipacaoEncontro`, com migration expansiva, constraints, índices
  e testes. A tabela, o signal e os contratos legados foram preservados; 266
  testes backend passaram sem acesso ao PostgreSQL.
- 2026-10-04 — D.2C concluída. Implementados os quatro services transacionais,
  transições, locks, idempotência, efeitos de conclusão e rollback. A suíte
  backend passou com 287 testes; os 2 testes de concorrência real permanecem
  para execução em PostgreSQL após provisionamento seguro de um banco de
  testes separado.
- 2026-10-04 — D.2D concluída. Removida a ativação implícita do vínculo
  legado, desacopladas as actions antigas de `Alpinista.status` e introduzidos
  comandos de API que delegam aos services novos. Contratos e estrutura
  legados foram preservados sem dual-write; 296 testes backend passaram.
