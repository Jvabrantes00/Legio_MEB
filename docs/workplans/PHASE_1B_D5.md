# Fase 1B.3D.5 — MME e Propostas de Violeiros

## Status geral

D.5A a D.5D concluídas em 2026-10-06. Fundação, services, API, autorização e
compatibilidade de propostas foram implementados e validados pela suíte
backend. D.5E — PostgreSQL, regressão e fechamento — é o próximo bloco.

## Objetivo

Modelar o planejamento do MME por múltiplas propostas de possíveis equipes de
Violeiros, preservando candidatos históricos, derivando disponibilidade da
escala oficial e mantendo separação estrita entre sugestão e trabalho real,
conforme [[../domain/ENCOUNTER_MME|MME e Propostas de Violeiros]].

## Escopo

- Propostas e posições sugeridas de Violeiros por Encontro.
- Situação consultável dos candidatos diante do perfil e da escala oficial.
- Preenchimento de posições livres e encerramento simples do planejamento.
- Integração somente consultiva com o domínio canônico de Trabalho.
- Autorização própria, compatibilidade incremental e regressão.

As regras estáveis de composição, autorização, histórico e separação de
domínios permanecem no documento de domínio e não são repetidas aqui.

## Fora de escopo

- Escala oficial paralela, reserva de candidato ou criação automática de
  convite, trabalho ou alocação.
- Relação de substituição, timeline completa ou workflow de aprovação.
- Notificações, catálogo de instrumentos e histórico permanente de sugestões.
- Criação automática de `Pessoa`, `PerfilAlpinista` ou `Frequencia`.
- Saúde, Formação em Encontros e autorização contextual por proposta.
- Backfill heurístico e remoção da estrutura legada.

## Blocos

### D.5A — Análise do legado e desenho técnico

Status: concluída em 2026-10-06.

### D.5B — Propostas, itens e fundação estrutural

Status: concluída em 2026-10-06.

Implementou os dois models aprovados, choices, constraints, índices, migration
expansiva e testes estruturais, sem services, API ou backfill.

### D.5C — Services, disponibilidade e encerramento operacional

Status: concluída em 2026-10-06.

Implementou comandos transacionais, projeção de disponibilidade, composição
`n/5`, preenchimento/substituição de slots e encerramento, sem escrever na
escala oficial.

### D.5D — API, autorização e compatibilidade

Status: concluída em 2026-10-06.

Implementou contratos explícitos de leitura e comando, autorização por papel,
auditoria e convivência com os endpoints legados, sem cutover destrutivo.

### D.5E — PostgreSQL, regressão e fechamento

Status: pendente.

Executará os testes concorrentes em PostgreSQL, regressão backend, conferência
de migrations, fechamento documental e atualização do estado global.

## D.5A — relatório de análise e desenho técnico

### Método e limites

- Análise somente de arquivos na branch `sia/fase-1-modelagem-dominio`, a
  partir do commit `6e7908a docs: add phase 1b d5 domain context`.
- Foram inspecionados models, migrations, camada de legado, services de
  trabalho e elegibilidade, serializers, views, rotas, roles, permissions,
  admin, testes e os poucos contratos frontend diretamente relacionados.
- `ENCOUNTER_WORK.md` foi consultado somente para escala oficial,
  `TrabalhoEncontro`, elegibilidade e histórico. A matriz de autorização foi
  consultada apenas para delimitar os novos acessos.
- Nenhum código, migration ou teste foi alterado e não houve acesso ao
  PostgreSQL.

### Inventário do estado real

- Não existe model, tabela, serializer, rota, service, signal, tela ou teste de
  proposta MME ou pré-equipe de Violeiros. O admin também não possui estrutura
  semelhante.
- `PerfilAlpinista` já contém `violeiro`, `canta` e `disponivel_mme`, todos
  booleanos com default `False`, desde a migration `0025_expand_pessoa`.
- A migration `0026_backfill_pessoa` criou `Pessoa` a partir de `Alpinista`,
  mas deliberadamente não criou `PerfilAlpinista` nem transferiu as
  características musicais. O débito global de perfis permanece aberto.
- A superfície pública atual ainda usa `Alpinista.eh_violeiro` e
  `Alpinista.canta`: summary/full, filtros, action `musica` e frontend leem ou
  escrevem esses campos legados. `disponivel_mme` não é exposto nem alterado
  por API. Não existe sincronização entre os dois modelos.
- A role MME hoje pode consultar summary de Alpinista, filtrar por
  `eh_violeiro`/`canta`, alterar a action musical e consultar o histórico
  legado de violeiro. Ela não possui acesso a Encontros, equipes ou trabalho.
- O histórico `historico-violeiro` atual lê `VinculoEncontroLegado` cuja
  `FuncaoEncontro.eh_violeiro=True`; esse vínculo não prova realização. O
  histórico canônico aprovado pela D.3 é `TrabalhoEncontro` com status
  `TRABALHOU` e role pertencente à equipe snapshot de Violeiros.
- `TrabalhoEncontro` já garante uma Pessoa por Encontro, diferencia aguardando,
  alocado, trabalhou, faltou e retirado e aponta para
  `RoleEquipeEncontro`/`EquipeEncontro`. Desalocação remove a role; retirada
  pode preservá-la, portanto a projeção não pode tratar toda role não nula como
  alocação atual.
- A D.3 não materializa catálogo fixo de equipes. `EquipeEncontro.codigo` é o
  identificador estável do snapshot, mas os dados são provisionados
  explicitamente. A D.5 adotará o código canônico `violeiros` e nunca
  comparação textual com `nome`.
- O evaluator de elegibilidade da D.3 é puro, usa `Pessoa`,
  `PerfilAlpinista` e participações canônicas e devolve elegível, aviso ou
  bloqueio. Ele pode ser reutilizado sem duplicar regras de caminho formativo.
- A camada legada conhece apenas `IN_VIOLEIRO` e linhas de
  `encontro_equipe` com Pessoa, Encontro, função textual e ordem. O mapping de
  funções continua vazio e não há proposta, agrupamento de cinco pessoas,
  coordenador sugerido, disponibilidade ou encerramento.
- O frontend possui somente os campos musicais legados no perfil e nenhuma
  tela ou contrato de proposta MME.
- A migration mais recente é `0033_expand_sessoes_formativas`.

### Conflitos que o desenho precisa isolar

1. Os campos musicais canônicos existem, mas os consumidores atuais continuam
   no model legado e não há equivalência segura para `disponivel_mme`.
2. Um vínculo legado de equipe representa escala ou participação, não uma
   sugestão interna do MME.
3. Disponibilidade diante da escala muda fora do domínio MME; persistir uma
   cópia exigiria dual-write e poderia divergir.
4. A proposta precisa guardar mais de cinco linhas históricas sem permitir
   mais de cinco posições vigentes.
5. O histórico legado de Violeiro superestima realização e não pode ser fonte
   para propostas nem para o histórico canônico futuro.
6. MME precisa gerir o novo recurso sem receber por consequência CRUD geral de
   Encontro, equipes ou trabalho.

## Desenho técnico aprovado

### `PropostaVioleiros`

- FK `encontro` com `PROTECT` e `related_name='propostas_violeiros'`.
- `nome` opcional e com tamanho limitado; é apresentação, não identidade.
- `status` com apenas `ABERTA` e `ENCERRADA`.
- `encerrada_em` nulo enquanto aberta e obrigatório quando encerrada.
- Timestamps de criação e atualização.
- Ordenação estável por Encontro, criação e PK; nomes são apresentação, não
  códigos de domínio.

Não haverá aprovação, seleção oficial, autor ou dono contextual persistido. A
autoria e as alterações relevantes ficam na auditoria geral da API.

### `ItemPropostaVioleiros`

- FK protegida para `PropostaVioleiros`.
- FK protegida para `PerfilAlpinista`; a `Pessoa` usada pela escala é obtida
  por `perfil_alpinista.pessoa`, sem duplicar as duas FKs.
- `papel_sugerido` com `COORDENADOR` e `INTEGRANTE`.
- `posicao` numérica: coordenador usa posição `1`; integrantes usam posições
  `1` a `4`.
- `vigente` indica que a linha ainda ocupa o slot de planejamento. Não é cópia
  de disponibilidade nem de status de trabalho.
- `retirado_em` registra quando a linha deixou de ocupar o slot; timestamps
  comuns preservam a sugestão original com granularidade suficiente.

Não serão criados `substituido_por`, status persistido de disponibilidade,
snapshot da escala, instrumento, convite ou trabalho no item.

### Cinco slots e preservação histórica

Os cinco slots são representados por:

- `(COORDENADOR, 1)`;
- `(INTEGRANTE, 1)` a `(INTEGRANTE, 4)`.

Uma unicidade parcial por proposta, papel e posição quando `vigente=True`
impede dois ocupantes vigentes no mesmo slot. O check de papel/posição torna
impossível criar um sexto slot. Quando um candidato indisponível for
substituído, o service marca a linha anterior como não vigente e preenche o
mesmo slot com nova linha, sem relação entre elas. Linhas antigas permanecem
consultáveis e a proposta pode acumular mais de cinco itens ao longo do tempo.

A mesma Pessoa não pode ocupar simultaneamente dois itens vigentes da mesma
proposta. Uma unicidade parcial por proposta e perfil aplica essa regra sem
impedir a preservação ou o reaproveitamento de linhas históricas. O mesmo
perfil pode integrar propostas diferentes do mesmo Encontro porque não existe
unicidade perfil/Encontro.

### Disponibilidade derivada

A projeção de cada item será calculada por query/service, nunca copiada de
`TrabalhoEncontro`. A precedência será:

1. `HISTORICO`, quando `vigente=False`;
2. `APROVEITADO_VIOLEIROS`, quando existe trabalho do mesmo Encontro com role
   na equipe de código `violeiros` e status diferente de `RETIRADO` e
   `AGUARDANDO_ALOCACAO`;
3. `INDISPONIVEL_OUTRA_EQUIPE`, para o mesmo caso em outra equipe;
4. `INDISPONIVEL_MME`, quando o perfil não está marcado simultaneamente como
   `violeiro` e `disponivel_mme`, ou a elegibilidade canônica possui bloqueio;
5. `DISPONIVEL`, nos demais casos; avisos da elegibilidade permanecem
   consultáveis e não viram impedimento inventado.

`canta` é informação consultiva e não bloqueia nem ocupa slot distinto. Um
trabalho apenas `AGUARDANDO_ALOCACAO` ainda não é escala oficial; trabalho
`RETIRADO` não indisponibiliza a Pessoa, mesmo que preserve uma role antiga.
Estados `ALOCADO`, `TRABALHOU` e `FALTOU`, todos coerentemente ligados a role,
identificam que houve alocação oficial. Essa classificação não altera o
critério do histórico permanente, que continua exigindo `TRABALHOU`.

O resumo da proposta deriva `disponiveis` pela contagem de itens vigentes cuja
situação é `DISPONIVEL`, fixa `total_posicoes=5` e expõe `completa` quando a
contagem for cinco. Assim `4/5`, `3/5` etc. são consulta, não estado gravado ou
notificação.

### Preenchimento de posição livre

O comando recebe proposta, perfil, papel e posição. Ele:

1. valida proposta aberta, slot permitido, perfil canônico e Encontro;
2. reaproveita o evaluator de elegibilidade da D.3;
3. rejeita perfil não violeiro, não disponível para MME, bloqueado ou já
   vigente na mesma proposta;
4. consulta a escala oficial sob lock;
5. exige slot vazio no comando de preenchimento;
6. usa comando explícito de substituição, referenciando a ocupação esperada,
   para tornar a linha anterior histórica e preencher o mesmo slot;
7. traduz corrida de constraint ou ocupação obsoleta para erro de domínio
   previsível.

Também haverá comando explícito para retirar um item vigente sem preencher o
slot. Não haverá remoção física em fluxo normal. Uma Pessoa histórica poderá
voltar em nova linha somente quando não possuir outro item vigente na proposta.

### Encerramento

`encerrar_proposta_violeiros(proposta, momento=None)` é idempotente e realiza
somente a transição `ABERTA → ENCERRADA`, preenchendo `encerrada_em`. Uma
proposta pode ser encerrada incompleta; o indicador final continua
consultável.

Depois disso, nome, itens, slots e vigência ficam read-only pelos services e
pela API. Não haverá reabertura nesta fase. A relação consultiva com a escala
oficial pode continuar mostrando se uma Pessoa foi posteriormente aproveitada,
mas não altera as linhas, o status nem o encerramento da proposta.

### Integração com a escala e histórico

- A proposta entrega apenas `pessoa_id` e sugestão de papel aos consumidores.
- Fichas/Diretoria continuam usando os comandos existentes de
  `ConviteEncontro(TRABALHAR)` e `TrabalhoEncontro`; não haverá action
  “aprovar proposta” nem dual-write.
- A role sugerida de coordenador não é convertida automaticamente em
  `RoleEquipeEncontro`, pois proposta e snapshot oficial são independentes.
- A identificação de Violeiros usa `EquipeEncontro.codigo='violeiros'`.
- Nenhum item entra nos históricos do perfil. O cutover do endpoint legado de
  histórico de Violeiro para `TrabalhoEncontro(status=TRABALHOU)` é débito de
  compatibilidade da D.5D e deve preservar o contrato público antes de mudar a
  fonte.

### Autorização e API prevista

- Será criado um conjunto explícito de gestão para Suporte, Diretoria e MME;
  superuser permanece bypass técnico.
- Leitura inclui também Fichas. Fichas não recebe create, update, retirada ou
  encerramento de proposta.
- A role sugerida não participa de permission classes e não cria autorização
  contextual.
- O endpoint será próprio e exigirá escopo de Encontro na listagem. O contrato
  de leitura usará allowlist, dados summary do candidato, situação derivada,
  avisos de elegibilidade e resumo `n/5`.
- Escritas serão comandos explícitos para criar/editar metadados enquanto
  aberta, preencher/retirar slot e encerrar. Não haverá `DELETE`, update
  genérico de item ou action que escreva em Trabalho.
- MME não receberá CRUD amplo de Encontro por efeito colateral. A consulta de
  proposta fornecerá apenas o contexto mínimo necessário do Encontro.
- Cada mutação ficará na mesma transação de seu `LogSistema`, sem registrar
  dados pessoais sensíveis.

### Banco: constraints e índices

Pertencem ao banco:

- choices válidos de status da proposta e papel sugerido;
- coerência `ABERTA/encerrada_em nulo` e `ENCERRADA/encerrada_em preenchido`;
- nome opcional, sem unicidade ou papel de identidade;
- unicidade parcial de proposta/perfil quando o item está vigente;
- check local entre papel e faixa da posição;
- unicidade parcial de slot vigente por proposta/papel/posição;
- coerência entre `vigente` e `retirado_em`;
- índices por `encontro/status`, por `proposta/vigente/papel/posicao` e por
  `perfil_alpinista/vigente`.

Pertencem aos services ou à projeção:

- proposta aberta para mutação;
- perfil e flags canônicas de MME;
- elegibilidade e avisos da D.3;
- disponibilidade diante de Trabalho;
- preenchimento e troca de slot;
- classificação de aproveitamento em Violeiros ou outra equipe;
- contagem `n/5`, completude, encerramento e autorização.

Regras que atravessam `Encontro`, perfil, equipe ou trabalho não serão
convertidas em constraints SQL frágeis.

### Transações e concorrência

Os services previstos são:

- `criar_proposta_violeiros(...)`;
- `editar_proposta_violeiros(...)`;
- `preencher_posicao_proposta(...)`;
- `substituir_ocupacao_proposta(...)`;
- `retirar_item_proposta(...)`;
- `encerrar_proposta_violeiros(...)`;
- `obter_situacao_item_proposta(...)` e
  `resumir_proposta_violeiros(...)`, consultas sem efeitos colaterais.

Mutações compostas usam `transaction.atomic`. Para operações que confrontam a
escala, a ordem de locks será compatível com a D.3: Pessoas envolvidas por PK,
Encontro, proposta, itens/slots e trabalhos relevantes. `select_for_update`
protege a proposta aberta, o slot e a leitura da alocação; constraints são a
defesa final.

Essa ordem serializa preenchimento contra alocação oficial concorrente sem
acoplar os domínios. Se a alocação vencer, o candidato é rejeitado como
indisponível; se a proposta vencer, uma alocação imediatamente posterior o
torna indisponível na projeção e o resumo passa a indicar a vaga livre. Não há
signal nem atualização em massa das propostas.

## Migration

A D.5B criou `0034_expand_propostas_violeiros`, dependente de
`0033_expand_sessoes_formativas`, contendo apenas:

- `PropostaVioleiros`;
- `ItemPropostaVioleiros`;
- FKs, choices, índices e constraints aprovados.

A migration é expansiva, sem `RunPython`, seed, alteração de models legados ou
dados. Os campos de `PerfilAlpinista` já existiam e não exigiram mudança de
schema. **nenhum backfill automático nesta etapa**.

## Resultado da D.5B

### Models e cinco slots

- `PropostaVioleiros` foi implementada com Encontro protegido, nome opcional,
  estados `ABERTA`/`ENCERRADA`, timestamp coerente de encerramento e índice de
  consulta por Encontro/status.
- `ItemPropostaVioleiros` reutiliza `PerfilAlpinista`, registra papel, posição,
  vigência, retirada e timestamps, com FKs protegidas.
- Os slots vigentes são limitados estruturalmente a coordenador `1` e
  integrantes `1–4`. Unicidades parciais impedem colisão de slot e duplicação
  simultânea do perfil na mesma proposta.
- Itens não vigentes permanecem armazenados e podem elevar o total histórico
  acima de cinco sem ampliar os cinco slots vigentes.
- Nenhum campo de trabalho, equipe, disponibilidade, substituição ou histórico
  permanente foi duplicado.

### Constraints e índices

- Checks de status, papel, formato do slot, encerramento e coerência entre
  vigência/retirada.
- Unicidades condicionais de slot vigente e perfil vigente por proposta.
- Índices para proposta por Encontro/status, slots vigentes e consulta de
  itens por perfil.
- Disponibilidade, elegibilidade, proposta encerrada e relação com a escala
  continuam fora do banco e pertencem à D.5C.

### Testes e validações

- Adicionados 16 testes estruturais cobrindo múltiplas propostas, nome
  opcional, estados, cinco slots, colisões, histórico acima de cinco linhas,
  perfil vigente único, uso em propostas diferentes, FKs protegidas, ausência
  de campos redundantes, ausência de efeitos externos e preservação do legado.
- Testes novos: 16/16 aprovados.
- Suíte backend: 445/445 aprovados, com 9 skips condicionais já previstos.
- `python manage.py check --settings=setup.test_settings`: aprovado.
- `python manage.py makemigrations --check --dry-run
  --settings=setup.test_settings`: nenhuma mudança detectada.
- PostgreSQL não foi necessário nesta etapa. As corridas reservadas permanecem
  para D.5E.

### Arquivos alterados na D.5B

- `backend/core/models.py`
- `backend/core/migrations/0034_expand_propostas_violeiros.py`
- `backend/core/tests/test_encontro_mme_models.py`
- `docs/workplans/PHASE_1B_D5.md`

## Resultado da D.5C

### Services implementados

- `criar_proposta_violeiros` e `editar_proposta_violeiros` criam e alteram
  somente proposta aberta.
- `preencher_posicao_proposta` inclui candidato disponível em slot vazio e
  rejeita perfil ou slot já vigente.
- `substituir_ocupacao_proposta` recebe a ocupação esperada, arquiva a linha e
  cria a nova no mesmo slot atomicamente. Uma segunda substituição concorrente
  da linha obsoleta é rejeitada, evitando lost update.
- `retirar_item_proposta` preserva a linha e é idempotente enquanto a proposta
  permanece aberta.
- `encerrar_proposta_violeiros` executa `ABERTA → ENCERRADA`, inclusive em
  proposta incompleta, sem implementar reabertura.
- `obter_situacao_item_proposta` e `resumir_proposta_violeiros` são consultas
  sem efeitos colaterais e retornam estruturas próprias para a futura API.

### Disponibilidade e composição

- A situação é derivada de `PerfilAlpinista`, do evaluator da D.3 e de
  `TrabalhoEncontro`; nenhum estado da escala foi copiado para a proposta.
- Trabalho `ALOCADO`, `TRABALHOU` ou `FALTOU` em equipe de código `violeiros`
  produz `APROVEITADO_VIOLEIROS`; em outra equipe produz
  `INDISPONIVEL_OUTRA_EQUIPE`.
- Trabalho aguardando alocação ou retirado não bloqueia a proposta.
- Perfil sem `violeiro` ou `disponivel_mme`, ou com bloqueio estrutural da D.3,
  produz `INDISPONIVEL_MME`; `canta` permanece apenas consultivo e avisos de
  elegibilidade não são convertidos em bloqueio.
- Item não vigente produz `HISTORICO`. Apenas itens vigentes em situação
  `DISPONIVEL` contam no resumo.
- O resumo expõe `total_posicoes=5`, `total_disponivel`, `vagas_disponiveis`,
  `completa` e `precisa_completar`. Uma alocação oficial altera esse resultado
  em todas as propostas relacionadas sem dual-write.

### Transações e concorrência

- Todas as mutações compostas usam `transaction.atomic`.
- Locks seguem Pessoas, Encontro, proposta, itens/slots e trabalhos relevantes,
  em ordem compatível com o domínio de Trabalho.
- `select_for_update` serializa preenchimentos, substituições, retirada e
  encerramento; constraints da D.5B permanecem a defesa final.
- Foram preparados cinco testes condicionados a PostgreSQL para mesmo slot,
  mesmo candidato, substituições da mesma ocupação, encerramento concorrente
  com edição e alocação oficial concorrente. A execução real permanece
  reservada à D.5E.

### Testes e validações

- Adicionados 24 testes de services: 19 executados e aprovados no SQLite e 5
  concorrentes ignorados por exigirem PostgreSQL real.
- Cobertura inclui criação, edição, cinco posições, `5/5`, `4/5`, duplicidade,
  múltiplas propostas, substituição, retirada, todas as situações derivadas,
  encerramento, bloqueio pós-encerramento, ausência de reabertura, ausência de
  efeitos em outros domínios e rollback integral.
- Suíte backend: 469/469 aprovada, com 14 skips condicionais no total.
- `python manage.py check --settings=setup.test_settings`: aprovado.
- `python manage.py makemigrations --check --dry-run
  --settings=setup.test_settings`: nenhuma mudança detectada.
- Nenhuma migration foi criada ou alterada na D.5C e não houve acesso ao
  PostgreSQL.

### Arquivos alterados na D.5C

- `backend/core/services/propostas_violeiros.py`
- `backend/core/tests/test_encontro_mme_services.py`
- `docs/workplans/PHASE_1B_D5.md`

## Resultado da D.5D

### API e contratos

- Registrado `/api/propostas-violeiros/` com listagem escopada obrigatoriamente
  por `encontro`, criação e detalhe.
- Actions explícitas: `editar-nome`, `preencher-posicao`,
  `substituir-posicao`, `retirar-item`, `encerrar`, `resumo` e
  `aproveitar-candidato`.
- O contrato de leitura usa allowlist e expõe estado, composição `n/5`, vagas,
  completude, itens vigentes e históricos, papel/posição, situação derivada,
  flags musicais canônicas e avaliação de elegibilidade quando aplicável.
- Serializers de comando são estritos e rejeitam campos extras. Não foram
  expostos `PUT`, `DELETE` ou update genérico dos models.
- Nested mismatch de item/proposta retorna `404`; erros de entrada e transição
  dos services permanecem `400`, autorização `401/403` e métodos ausentes
  `405`.

### Autorização

- Suporte, Diretoria e MME possuem gestão de proposta; Fichas possui somente
  leitura e a action separada de aproveitamento oficial.
- A action de aproveitamento usa as roles administrativas canônicas da D.3:
  Suporte, Diretoria e Fichas. MME não recebe escrita em convite, trabalho ou
  escala.
- Demais papéis permanecem negados por default. Superuser continua bypass
  técnico separado.
- A role `COORDENADOR` sugerida não participa das permissions e não concede
  capability contextual.
- `AUTHORIZATION_MATRIX.md` foi atualizada com a fronteira implementada.

### Aproveitamento oficial

- A action valida que o item pertence à proposta e continua disponível, então
  delega a `criar_convite_trabalho` da D.3.
- A operação cria somente `ConviteEncontro(TRABALHAR)` em estado `CONVIDADO`.
  Não confirma, não cria `TrabalhoEncontro`, não aloca e nunca marca
  `TRABALHOU`.
- `role_equipe_id` é opcional e representa a role oficial proposta no convite;
  ela pode divergir do papel sugerido pelo MME.
- Candidatos podem ser aproveitados individualmente de propostas diferentes;
  não existe proposta vencedora ou seleção integral.

### Propostas incompletas

- Leitura e action `resumo` reutilizam integralmente a projeção da D.5C.
- A listagem aceita `precisa_completar=true` para retornar somente propostas
  abertas cuja disponibilidade derivada está abaixo de cinco.
- O aviso permanece consultável; nenhuma notificação, push ou e-mail foi
  criado.

### Compatibilidade e auditoria

- Os endpoints e writes legados de música, função, participação e histórico
  de Violeiro permanecem intactos. Não há dual-write, backfill ou reconstrução
  de propostas.
- Novos writes usam exclusivamente os services canônicos da D.5C. A escala
  continua sob os services da D.3.
- Criação, alteração de nome, preenchimento, substituição, retirada e
  encerramento geram `LogSistema` apenas com identificadores. O aproveitamento
  registra a solicitação junto ao convite, sem dados pessoais sensíveis.
- Situação da mesma Pessoa muda em todas as propostas por leitura de
  `TrabalhoEncontro`, sem atualização em cascata.

### Testes e validações

- Adicionados 21 testes de API e contratos cobrindo papéis, autenticação,
  comandos, resumo, filtro de incompletas, todas as situações derivadas,
  histórico, multi-proposta, aproveitamento oficial, role divergente,
  auditoria, ausência de efeitos colaterais, nested mismatch, `405` e
  allowlists.
- Testes novos: 21/21 aprovados.
- Suíte backend: 490/490 aprovada, com 14 skips condicionais.
- `python manage.py check --settings=setup.test_settings`: aprovado.
- `python manage.py makemigrations --check --dry-run
  --settings=setup.test_settings`: nenhuma mudança detectada.
- Nenhuma migration foi criada ou alterada e não houve acesso ao PostgreSQL.

### Arquivos alterados na D.5D

- `backend/core/roles.py`
- `backend/core/services/propostas_violeiros.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/urls.py`
- `backend/core/tests/test_encontro_mme_api.py`
- `docs/AUTHORIZATION_MATRIX.md`
- `docs/workplans/PHASE_1B_D5.md`

## Estratégia incremental e compatibilidade

### EXPAND — D.5B e D.5C

- Criar tabelas isoladas e services canônicos.
- Manter `Alpinista`, `FuncaoEncontro`, `VinculoEncontroLegado`, seus
  endpoints e o frontend sem alteração.
- Não sincronizar proposta com vínculo legado ou Trabalho por signal.

### COMPAT — D.5D

- Adicionar API própria sem ampliar silenciosamente os contratos de perfil.
- Ler flags canônicas de `PerfilAlpinista`; a action musical legada continua
  intacta até uma reconciliação explícita de perfil.
- Manter o histórico legado disponível enquanto o consumidor não puder usar a
  fonte canônica com contrato compatível.

### CUTOVER e DEPRECATE

- Somente após dados de perfil reconciliados, contratos validados e decisão
  explícita sobre o histórico legado.
- A estrutura antiga não será removida na D.5.

## Backfill

O legado não contém identidade de proposta, agrupamento confiável de cinco
pessoas, slot, coordenação sugerida, disponibilidade ou encerramento. Linhas de
`encontro_equipe` representam outra semântica, e `IN_VIOLEIRO` isolado não
reconstrói planejamento.

**nenhum backfill automático nesta etapa**.

Também não haverá cópia automática de `Alpinista.eh_violeiro/canta` para
`PerfilAlpinista`: perfis podem não existir e `disponivel_mme` não possui fonte
legada equivalente. Essa reconciliação permanece débito humano separado.

## Matriz de testes prevista

### D.5B — estrutura

- criação de múltiplas propostas no mesmo Encontro;
- status, encerramento e constraints locais;
- cinco slots válidos e rejeição de slot/papel impossível;
- unicidade de slot vigente e de perfil por proposta;
- mesma Pessoa em propostas diferentes;
- linhas históricas acima de cinco sem mais de cinco slots vigentes;
- `PROTECT` e ausência de efeitos em Trabalho, Convite e Frequência;
- migration expansiva preservando estruturas anteriores.

### D.5C — services

- criação, edição, preenchimento, retirada e encerramento idempotente;
- rejeição de mutação encerrada;
- perfil sem flags necessárias, bloqueios e avisos de elegibilidade;
- classificação disponível, aproveitado em Violeiros, indisponível em outra
  equipe e histórico;
- trabalho aguardando ou retirado não bloqueando; alocado bloqueando;
- queda automática de `5/5` para `4/5` sem dual-write;
- substituição no mesmo slot com preservação da linha anterior;
- mesma Pessoa em várias propostas e não repetida na mesma;
- rollback em falha intermediária e nenhuma criação de objetos externos;
- corridas de mesmo slot, mesmo candidato e alocação oficial concorrente.

### D.5D — API e autorização

- contratos allowlist, escopo obrigatório e nested mismatch `404`;
- Suporte, Diretoria e MME com gestão; Fichas somente leitura;
- demais roles negadas por default e superuser como bypass;
- role sugerida sem capability contextual;
- métodos não expostos retornando `405` e erros preservando a semântica HTTP;
- auditoria e regressão dos contratos legados.

### D.5E — PostgreSQL e regressão

- executar as corridas reais reservadas em PostgreSQL isolado;
- suíte backend completa, `check`, `makemigrations --check --dry-run`, estado
  das migrations e `git diff --check`;
- confirmar ausência de dual-write, perfil/frequência implícitos e histórico
  duplicado.

## Débitos e pendências

- Reconciliar a existência e os valores de `PerfilAlpinista`, inclusive
  `violeiro`, `canta` e `disponivel_mme`, com fonte humana confiável.
- Definir e provisionar operacionalmente o catálogo/snapshot de equipes com o
  código estável `violeiros`; a D.5 não cria catálogo paralelo.
- Migrar consumidores do histórico legado de violeiro para a fonte canônica
  sem quebra de contrato.
- Implementação frontend das propostas fica fora dos blocos backend definidos
  neste workplan, salvo decisão posterior explícita.

Nenhuma dessas pendências impede a validação e o fechamento da D.5E.

## Arquivos relevantes

- `docs/domain/ENCOUNTER_MME.md`
- `docs/workplans/PHASE_1B_D5.md`
- `docs/domain/ENCOUNTER_WORK.md`, apenas para integração com a escala.
- `docs/AUTHORIZATION_MATRIX.md`, para a autorização da D.5D.
- `backend/core/models.py`
- `backend/core/services/trabalhos.py`
- `backend/core/services/elegibilidade_trabalho.py`
- `backend/core/roles.py`, `permissions.py`, `serializers.py`, `views.py` e
  `urls.py`
- migrations `0025`, `0026`, `0030` e `0033`.

## Próximo passo

D.5E — executar as cinco corridas em PostgreSQL real, regressão final e
fechamento documental da Fase 1B.3D.5.

## Histórico de execução

- 2026-10-06 — Vault da Fase 1B.3D.5 preparado; nenhuma análise técnica ou
  implementação realizada.
- 2026-10-06 — D.5A concluída por inspeção do código. Fechados models, cinco
  slots, disponibilidade derivada, encerramento, autorização, concorrência,
  migration, compatibilidade e testes. Nenhum código, banco ou migration foi
  alterado.
- 2026-10-06 — D.5B concluída. Models, migration expansiva e 16 testes
  estruturais implementados; suíte backend com 445 testes aprovada. Nenhum
  backfill, service, API ou acesso ao PostgreSQL foi realizado.
- 2026-10-06 — D.5C concluída. Services transacionais, situações derivadas,
  resumo `n/5`, substituição segura e encerramento implementados; suíte backend
  com 469 testes aprovada. Cinco corridas aguardam validação PostgreSQL na
  D.5E.
- 2026-10-06 — D.5D concluída. API canônica, autorização, aproveitamento via
  convite oficial, filtro de propostas incompletas, auditoria e compatibilidade
  implementados; suíte backend com 490 testes aprovada. Nenhuma migration ou
  alteração de legado foi necessária.
