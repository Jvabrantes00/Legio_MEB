# Fase 1B.3D.5 — MME e Propostas de Violeiros

## Status geral

D.5A concluída em 2026-10-06. O legado foi inventariado e o desenho técnico
foi fechado sem decisão de produto bloqueante. D.5B — propostas, itens e
fundação estrutural — é o próximo bloco.

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

Status: pendente.

Implementará os dois models aprovados, choices, constraints, índices, migration
expansiva e testes estruturais. Não implementará services, API ou backfill.

### D.5C — Services, disponibilidade e encerramento operacional

Status: pendente.

Implementará comandos transacionais, projeção de disponibilidade, composição
`n/5`, preenchimento de slots e encerramento, sem escrever na escala oficial.

### D.5D — API, autorização e compatibilidade

Status: pendente.

Implementará contratos explícitos de leitura e comando, autorização por papel,
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
- `nome` obrigatório, com tamanho limitado, para distinguir as múltiplas
  combinações do mesmo Encontro.
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

A mesma Pessoa não pode reaparecer em outro item da mesma proposta, inclusive
depois de retirada; a unicidade total por proposta e perfil preserva essa
regra sem ambiguidades. O mesmo perfil pode integrar propostas diferentes do
mesmo Encontro porque não existe unicidade perfil/Encontro.

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
3. rejeita perfil não violeiro, não disponível para MME, bloqueado ou já usado
   na mesma proposta;
4. consulta a escala oficial sob lock;
5. se o slot estiver ocupado por candidato ainda disponível, rejeita;
6. se o ocupante estiver indisponível, torna a linha anterior histórica e cria
   a nova linha no mesmo comando atômico;
7. traduz corrida de constraint para erro de domínio previsível.

Também haverá comando explícito para retirar um item vigente sem preencher o
slot. Não haverá remoção física em fluxo normal. Reativar uma Pessoa já
histórica na mesma proposta fica proibido; ela pode ser escolhida oficialmente
sem voltar à proposta ou integrar outra proposta.

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
- unicidade exata de `encontro/nome` para identificar propostas;
- unicidade total de proposta/perfil;
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

## Migration prevista

A D.5B deve criar `0034_expand_propostas_violeiros`, dependente de
`0033_expand_sessoes_formativas`, contendo apenas:

- `PropostaVioleiros`;
- `ItemPropostaVioleiros`;
- FKs, choices, índices e constraints aprovados.

A migration será expansiva, sem `RunPython`, seed, alteração de models
legados ou dados. Os campos de `PerfilAlpinista` já existem e não exigem
mudança de schema.

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

Nenhuma dessas pendências exige nova decisão de produto para iniciar a D.5B.

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

D.5B — implementar `PropostaVioleiros`, `ItemPropostaVioleiros`, a migration
expansiva `0034` e os testes estruturais, sem services, API ou backfill.

## Histórico de execução

- 2026-10-06 — Vault da Fase 1B.3D.5 preparado; nenhuma análise técnica ou
  implementação realizada.
- 2026-10-06 — D.5A concluída por inspeção do código. Fechados models, cinco
  slots, disponibilidade derivada, encerramento, autorização, concorrência,
  migration, compatibilidade e testes. Nenhum código, banco ou migration foi
  alterado.
