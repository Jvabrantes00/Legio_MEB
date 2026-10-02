# Fase 1B.3D.2 — Inscrição, Convite e Participação

## Status geral

D.2A e D.2B concluídas. A fundação estrutural foi implementada na migration
`0029_expand_inscricao_convite_participacao`, sem acesso ou escrita no
PostgreSQL local, sem backfill e sem cutover dos contratos legados. D.2C é o
próximo bloco.

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

Status: pendente.

### D.2D — Compatibilidade e cutover legado

Status: pendente.

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

- Implementar comandos transacionais exclusivamente sobre os models novos.
- Não fazer dual write a partir das actions antigas: efetivação e remoção não
  possuem semântica suficiente para inferir convite ou resultado novo.
- Manter qualquer endpoint novo sob default deny e, enquanto não houver
  decisão específica de captação anônima, limitar gestão às roles já
  autorizadas para Encontros e participações.

### COMPAT e CUTOVER — D.2D

- Introduzir leitura e comandos novos sem retirar o recurso legado.
- Migrar o frontend por fluxo: inscrição, convite/confirmação e só depois
  resultado real.
- Trocar `encontros_realizados` para resultados `CONCLUIU` apenas quando o novo
  histórico estiver disponível; `historico_equipes` continua no vínculo antigo
  até o domínio de equipes ser remodelado.
- Remover o signal de ativação prematura no cutover dos fluxos que hoje criam
  vínculo legado. `PerfilAlpinista`, e não `Alpinista.status`, passa a ser a
  evidência de que a Pessoa é oficialmente Alpinista.
- Manter `VinculoEncontroLegado` e sua tabela enquanto equipes, frontend ou
  contratos da Fase 0 ainda dependerem deles.

### DEPRECATE

- Só remover rota, relação M2M e tabela antigas após busca global sem
  consumidores, regressão dos contratos e plano separado para equipes.
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

Permanecem para os próximos blocos os testes de services, concorrência real em
PostgreSQL, APIs novas e frontend no COMPAT/CUTOVER.

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
  PostgreSQL na D.2C/D.2E, quando os services transacionais existirem.

## Pendências humanas

Nenhuma decisão de produto pendente bloqueia D.2B. Profiling de dados reais e
eventual autorização para captação anônima são trabalhos futuros com evidência
própria, não pressupostos da migration expansiva.

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

## Próximo passo

Executar D.2C — services e regras transacionais sobre os models novos, sem
cutover dos contratos legados.

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
