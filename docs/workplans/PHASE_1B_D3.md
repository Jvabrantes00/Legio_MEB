# Fase 1B.3D.3 — Equipes e Trabalho em Encontro

## Status geral

Fase em andamento. D.3A e D.3B estão concluídas. A fundação estrutural de
templates, snapshots, roles e `TrabalhoEncontro` foi implementada e validada;
D.3C é o próximo bloco.

## Objetivo

Modelar templates, snapshots de equipes e roles, convite para trabalhar,
alocação, resultado de trabalho, reuniões preparatórias, presença,
autorização contextual e elegibilidade, preservando as regras estáveis de
[[../domain/ENCOUNTER_WORK|Equipes e Trabalho em Encontro]] e os contratos
legados durante a transição.

## Escopo

- Templates e snapshots de equipes e roles por tipo de Encontro.
- Integração com `ConviteEncontro(finalidade=TRABALHAR)` sem confundir convite,
  confirmação, alocação e trabalho realizado.
- `TrabalhoEncontro`, reuniões preparatórias e presença.
- Autorização contextual da Coordenação Geral.
- Avaliação estruturada de elegibilidade e avisos.
- Compatibilidade incremental com API, frontend e históricos legados.

## Fora de escopo

- Saúde contextual e acesso a dados de saúde.
- Criação ou destruição automática de contas.
- Criação automática de `Frequencia`.
- Timeline completa de realocações ou entidade explícita de substituição.
- Backfill heurístico de equipes, roles ou históricos.
- Remoção física antecipada de `FuncaoEncontro`,
  `VinculoEncontroLegado` ou seus contratos.

## Blocos

### D.3A — Análise do legado e desenho técnico

Status: concluída em 2026-10-04.

### D.3B — Templates, equipes, roles e TrabalhoEncontro

Status: concluída em 2026-10-04.

### D.3C — Services de convite, alocação e trabalho

Status: próximo bloco.

### D.3D — Reuniões preparatórias e presença

Status: pendente.

### D.3E — Autorização contextual da Coordenação Geral

Status: pendente.

### D.3F — Elegibilidade e avisos para trabalhar

Status: pendente.

### D.3G — Compatibilidade, PostgreSQL, regressão e fechamento

Status: pendente.

## D.3A — relatório de análise e desenho técnico

### Método e limites

- Análise somente de arquivos, na branch `sia/fase-1-modelagem-dominio`, a
  partir do commit `b779933 docs: add phase 1b d3 domain context`.
- Foram inspecionados models, migrations, services, serializers, views,
  rotas, permissões, admin, transformadores legados, testes e os consumidores
  frontend diretamente relacionados.
- `ENCOUNTER_PARTICIPATION.md` foi consultado somente para confirmar o contrato
  já implementado de `ConviteEncontro` com finalidade `TRABALHAR`.
- Nenhuma query, migration, teste com banco ou acesso ao PostgreSQL foi
  executado nesta etapa.

### Inventário do legado real

- `FuncaoEncontro` oferece apenas `nome`, `tipo`, `descricao_faq`, `ordem` e
  `eh_violeiro`. O choice `tipo` diferencia somente `encontrista` de `equipe`;
  não existem entidades próprias para template, equipe de uma edição ou role.
  O campo `nome` é texto livre e hoje mistura nomes de equipes e posições.
- `VinculoEncontroLegado`, na tabela física
  `core_participacaoencontro`, liga `Alpinista`, `Encontro` e
  `FuncaoEncontro`, com `cor_grupo` e o booleano livre `coordenador`. Sua
  unicidade por `Alpinista/Encontro` mistura encontristas e trabalhadores e
  impede que o mesmo registro represente os conceitos novos separadamente.
- O model novo `ParticipacaoEncontro` é resultado de participação, usa
  `Pessoa` e vive em tabela própria. O service rejeita corretamente um convite
  `TRABALHAR` como origem de participação.
- `ConviteEncontro` já suporta `TRABALHAR`, impede inscrição nessa finalidade
  e possui unicidade por Pessoa, Encontro e finalidade. `criar_convite`
  aceita o convite de trabalho sem executar a elegibilidade de participante;
  confirmar o convite não cria outro objeto.
- Não há model, service, serializer, rota, signal ou teste específico de
  `TrabalhoEncontro`, equipe snapshot, reunião preparatória ou presença. Não há
  signals ativos para recuperar ou adaptar esses fluxos.
- O CRUD legado de `/api/funcoes/` e `/api/participacoes-encontros/` grava
  models diretamente por `ModelViewSet`, sob as roles atuais de gestão de
  Fichas. O admin técnico registra apenas as estruturas legadas relacionadas.
- O detalhe frontend de Encontro carrega todas as funções cujo tipo não é
  `encontrista`, usa cada função como card de equipe e cria, altera ou remove
  diretamente `VinculoEncontroLegado`. O toggle `coordenador` não identifica
  uma role estrutural.
- `historico_equipes` considera histórico todo vínculo cuja função não seja
  `encontrista`; `historico-violeiro` usa somente `eh_violeiro`. Nenhum dos
  dois comprova que a Pessoa efetivamente trabalhou.
- A camada de transformação conhece a tabela `encontro_equipe` e os campos
  `CD_REGISTRO`, `CD_ENCONTRO`, `NM_FUNCAO` e `NR_ORDEM`, mas o mapping
  `LEGACY_FUNCTION_TO_CANONICAL` está intencionalmente vazio. O transformador
  também classifica como erro vínculos duplicados ou incompatíveis para a
  mesma pessoa e encontro.
- As migrations `0006`, `0007`, `0015`, `0021` e `0029` explicam a evolução
  da estrutura atual. A migration mais recente é
  `0029_expand_inscricao_convite_participacao`.
- Os testes existentes congelam o payload legado, o CRUD auditado, a
  autorização por roles, a unicidade antiga, a ausência de efeitos implícitos
  e os históricos atuais. Eles são baseline de compatibilidade, não evidência
  para inferir trabalho concluído.

### Conflitos que o desenho precisa isolar

1. Equipe, role, coordenação e função textual são um único conceito no legado.
2. O mesmo vínculo físico representa participação e escala de trabalho.
3. `coordenador=True` não informa qual role de coordenação foi ocupada.
4. A existência do vínculo não distingue escala provisória, falta, retirada
   ou trabalho efetivamente realizado.
5. O histórico atual superestima trabalho ao tratar escala como realização.
6. A unicidade antiga não pode ser reutilizada como invariante do domínio
   novo, e o domínio novo não pode fazer dual-write nela sem perder semântica.
7. `User` e `Pessoa` não possuem vínculo explícito; grupos Django, isolados,
   não demonstram participação contextual em uma Coordenação Geral.
8. `PerfilAlpinista` não possui um estado canônico de atividade. O status
   `ativo/inativo` ainda existe no `Alpinista` legado, ligado opcionalmente e
   de forma one-to-one a `Pessoa`.

## Desenho técnico aprovado

### Templates e snapshots

#### `TemplateEquipeEncontro`

- Campos: `tipo_encontro`, `codigo`, `nome`, `ordem`,
  `capacidade_minima_recomendada`, `capacidade_maxima_recomendada`, `ativo`,
  timestamps.
- Unicidade de `tipo_encontro/codigo`; códigos estáveis não são nomes de
  apresentação.
- Capacidades nulas significam ausência de limite consultivo. Os valores
  presentes são copiados para o snapshot e produzem avisos, não bloqueios.
- Templates usados deixam de ser apagados e passam a ser desativados.

#### `TemplateRoleEquipe`

- FK protegida para `TemplateEquipeEncontro` e campos `codigo`, `nome`,
  `ordem`, `quantidade_estrutural` opcional,
  `concede_registro_presenca` e `ativo`.
- Unicidade de `template_equipe/codigo`.
- `quantidade_estrutural` representa somente posições cuja composição foi
  definida como estrutural. `null` representa role sem máximo rígido inicial.
- Nomes e quantidades do catálogo estável são materializados por seed
  versionado, não por comparação com texto legado.

#### `EquipeEncontro`

- FKs protegidas para `Encontro` e para o template de origem.
- Copia `codigo`, `nome`, `ordem` e capacidades consultivas.
- Unicidade de `encontro/codigo` e índice de apresentação por
  `encontro/ordem`.
- Alterar o template não altera snapshots existentes.

#### `RoleEquipeEncontro`

- FKs protegidas para `EquipeEncontro` e para a role de template de origem.
- Copia `codigo`, `nome`, `ordem`, `quantidade_estrutural` e a capacidade
  contextual de registrar presença.
- Unicidade de `equipe_encontro/codigo` e índice por
  `equipe_encontro/ordem`.
- O vínculo de um `TrabalhoEncontro` com esta role representa a ocupação da
  posição. Quantidades estruturais maiores que um permitem essa quantidade de
  ocupantes sob lock da role; não será criada uma entidade de slot sem
  necessidade demonstrada.

### Convite de trabalho e proposta conhecida

- `ConviteEncontro` continua sendo a autoridade de convite e confirmação.
- Será adicionado `role_trabalho_proposta`, FK opcional e protegida para
  `RoleEquipeEncontro`. O campo comunica equipe/role quando já conhecidas no
  convite, mas não constitui alocação nem histórico.
- Constraint local: `role_trabalho_proposta` deve ser nula quando a finalidade
  não for `TRABALHAR`.
- A coerência entre o Encontro do convite e o Encontro do snapshot é
  invariante de service, pois uma check constraint não pode atravessar FKs.
- Ao confirmar, o service pode copiar a proposta válida para o trabalho
  criado por comando explícito posterior. `responder_convite` continua
  alterando somente o convite: a confirmação isolada não cria trabalho nem
  `ParticipacaoEncontro` e não será transformada em signal implícito.

### `TrabalhoEncontro`

- FKs protegidas para `Pessoa` e `Encontro`.
- One-to-one protegida e obrigatória para `ConviteEncontro`.
- FK protegida e opcional `role_equipe`; a equipe é derivada da role, evitando
  combinações inconsistentes entre equipe e role.
- Status: `AGUARDANDO_ALOCACAO`, `ALOCADO`, `TRABALHOU`, `FALTOU` e
  `RETIRADO`.
- Campos temporais: `criado_em`, `atualizado_em` e `resultado_registrado_em`
  opcional.
- Unicidade forte de `pessoa/encontro`; o one-to-one também impede reutilizar
  o mesmo convite.
- Índices: `encontro/status`, `pessoa/status` e `role_equipe/status`.
- Checks locais:
  - status pertence ao conjunto aprovado;
  - `AGUARDANDO_ALOCACAO` exige role nula;
  - `ALOCADO`, `TRABALHOU` e `FALTOU` exigem role;
  - `TRABALHOU` e `FALTOU` exigem `resultado_registrado_em`;
  - estados não finais não aceitam `resultado_registrado_em`;
  - `RETIRADO` pode preservar a última role ou permanecer sem role e não
    possui resultado de comparecimento.
- A finalidade, a confirmação, a mesma Pessoa e o mesmo Encontro do convite
  são validados sob transação no service; SQL não deve imitar joins frágeis.
- Apenas `TRABALHOU` alimenta o histórico e os contadores canônicos.

### Transições operacionais

- Convite de trabalho já `CONFIRMADO` → comando explícito e idempotente cria o
  trabalho em `AGUARDANDO_ALOCACAO`, ou `ALOCADO` quando houver proposta
  válida.
- `AGUARDANDO_ALOCACAO` → `ALOCADO` ou `RETIRADO`.
- `ALOCADO` → outra role `ALOCADO`, `AGUARDANDO_ALOCACAO`, `TRABALHOU`,
  `FALTOU` ou `RETIRADO`.
- Estados `TRABALHOU`, `FALTOU` e `RETIRADO` são terminais no fluxo comum.
  Correções administrativas futuras devem usar comando explícito, auditoria
  e a mesma proteção transacional; CRUD genérico não altera resultados.
- Substituição é uma operação atômica: retirar o trabalho anterior e alocar o
  novo trabalho confirmado. Não haverá FK `substituido_por`.

### Composição estrutural e capacidades

- O seed de templates representa as composições estáveis por roles e
  `quantidade_estrutural`; roles de integrante permanecem sem limite rígido.
- O service bloqueia exceder uma quantidade estrutural com
  `select_for_update` na role snapshot e conta somente trabalhos operacionais
  que ainda ocupam a posição.
- Quantidades abaixo da composição esperada são pendências estruturais
  explícitas na consulta de composição; as capacidades gerais de equipe
  continuam avisos.
- A leitura da equipe retorna ocupação atual, pendências estruturais e avisos
  de capacidade sem transformar recomendações em constraints SQL.

### Reuniões preparatórias e presença

#### `ReuniaoPreparatoriaEncontro`

- FK protegida para `Encontro`; campos `ordem`, `data`, `horario`, `local`,
  `observacoes`, timestamps.
- Ordem positiva e única por Encontro; índices por `encontro/ordem` e
  `encontro/data`.

#### `PresencaPreparatoria`

- FKs protegidas para reunião e `TrabalhoEncontro`.
- Campos `status`, `justificativa`, `registrada_por`, timestamps.
- `registrada_por` aponta para o `User` técnico com `PROTECT` para auditoria.
- Unicidade de `reuniao/trabalho`; índice por `reuniao/status`.
- Choices válidos são protegidos por check. A justificativa permanece
  opcional e não ganha uma regra SQL inventada.
- Reunião e trabalho pertencerem ao mesmo Encontro é invariante de service.
- O flag de revisão será derivado por `Exists` de presença com ausência sem
  justificativa. Não será persistido um booleano sujeito a ficar obsoleto; a
  consulta expõe `requer_revisao=True` e nenhuma remoção é automática.

### Autorização contextual

- Será criado `VinculoUsuarioPessoa`, com relações one-to-one protegidas para
  `AUTH_USER_MODEL` e `Pessoa`. O vínculo é explícito e administrado; não
  funde identidade técnica com pessoa do domínio e não cria contas.
- A capability contextual exige simultaneamente: usuário autenticado ligado à
  mesma Pessoa, `TrabalhoEncontro` daquele Encontro ainda operacional, role
  snapshot com `concede_registro_presenca=True` e Encontro fora de
  `FINALIZADO`/`CANCELADO`.
- A role com a capability é somente a posição apropriada da Coordenação Geral
  definida no template. Coordenar outra equipe não satisfaz a consulta.
- Permission DRF específica fará verificação de objeto/Encontro e manterá
  default deny. Superuser segue como bypass técnico; as roles administrativas
  atuais continuam separadas da capability contextual.
- O catálogo de templates terá escrita de negócio somente por Suporte; a
  composição dos snapshots permanece operável por Suporte, Diretoria e
  Fichas. O admin Django continua sendo fronteira do superuser técnico, não a
  interface normal de gestão do catálogo.
- Revogar o contexto decorre da alteração do trabalho, role ou lifecycle; não
  remove o `User`, seus grupos ou logs.
- A matriz implementada só será atualizada na D.3E, junto de endpoints e
  testes positivos, negativos, cross-Encontro e pós-finalização.

### Elegibilidade e avisos — arquitetura da D.3F

- Um evaluator puro `avaliar_elegibilidade_trabalho(pessoa, encontro)` retorna
  resultado `ELEGIVEL`, `AVISO` ou `BLOQUEIO` e uma lista estável de códigos;
  não grava banco e não se confunde com permission DRF.
- O evaluator usa `PerfilAlpinista` e conclusões canônicas de
  `ParticipacaoEncontro`. A situação ativa atual fica atrás de uma policy:
  enquanto não houver estado canônico novo, o adaptador pode ler o status do
  `Alpinista` somente pela relação one-to-one exata com `Pessoa`; ausência de
  evidência produz aviso `ATIVIDADE_NAO_DETERMINADA`, nunca inferência.
- Inatividade produz aviso anulável por decisão humana registrada no comando;
  não é bloqueio SQL.
- As regras de caminho já estáveis produzem códigos próprios, sem consultas
  por nomes livres. Para AVC e Acampamento não há evidência aprovada de um
  bloqueio adicional de trabalho: até regra de produto explícita, o evaluator
  retorna aviso de revisão manual, e não inventa impedimento.
- O wrapper de criação de convite de trabalho executa o evaluator, bloqueia
  apenas regras estruturais documentadas e exige confirmação explícita para
  prosseguir diante de avisos. A decisão e os códigos devem entrar na
  auditoria sem dados pessoais sensíveis.

## Banco: constraints e invariantes de service

### Pertencem ao banco

- Choices locais por `CheckConstraint`.
- Códigos únicos nos respectivos escopos de template e snapshot.
- Faixas não negativas e `minimo <= maximo` para capacidades informadas.
- Quantidade estrutural positiva quando informada.
- Um `TrabalhoEncontro` por Pessoa/Encontro e um trabalho por convite.
- Coerência local entre status, role e timestamp de resultado.
- Role proposta somente em convite `TRABALHAR`.
- Ordem positiva e única de reunião por Encontro.
- Uma presença por reunião/trabalho.
- Um vínculo técnico por User e por Pessoa.

### Pertencem aos services

- Tipos de Encontro compatíveis com templates e snapshots.
- Convite de trabalho confirmado, com mesma Pessoa e mesmo Encontro.
- Role proposta e role alocada pertencentes ao snapshot do Encontro.
- Snapshot idempotente e imutável depois de usado operacionalmente.
- Limites estruturais e composição; capacidades consultivas só geram avisos.
- Transições de `TrabalhoEncontro`, retirada e substituição.
- Reunião e trabalho pertencentes ao mesmo Encontro.
- Permissão contextual ligada ao Encontro e ao lifecycle.
- Elegibilidade, override humano de aviso e ausência de efeitos sobre
  `Frequencia`.

## Services e estratégia de concorrência

Os nomes previstos, seguindo o padrão atual em `core/services`, são:

- `preparar_equipes_encontro(encontro)`;
- `criar_convite_trabalho(...)`, reutilizando `criar_convite` da D.2;
- `iniciar_trabalho_confirmado(convite)`;
- `alocar_trabalho(trabalho, role_equipe)`;
- `desalocar_trabalho(trabalho)`;
- `registrar_resultado_trabalho(trabalho, status)`;
- `retirar_trabalho(trabalho)`;
- `substituir_trabalho(trabalho_anterior, trabalho_novo, role_equipe)`;
- services de criação/edição de reunião e `registrar_presenca_preparatoria`.

Todas as mutações compostas usam `transaction.atomic`. A ordem de locks será
estável: `Pessoa`, `Encontro`, `ConviteEncontro`, `TrabalhoEncontro`,
`EquipeEncontro`/`RoleEquipeEncontro` e, por último, reunião/presença quando
aplicável. `select_for_update` protege preparação idempotente, criação do
trabalho, alocação/realocação, quantidade estrutural, resultado, substituição
e upsert de presença. `UniqueConstraint` permanece a defesa final contra
corridas, com tradução de `IntegrityError` para erro de domínio coerente.

Nenhuma lógica nova será introduzida por signal. Fluxos explícitos permitem
transação, autorização, auditoria e erros previsíveis.

## API e compatibilidade incremental

### EXPAND — D.3B a D.3F

- Criar tabelas novas, campos opcionais e endpoints de comando/consulta sem
  remover a estrutura antiga.
- Não expor CRUD genérico para resultado de trabalho, presença ou templates.
- Escritas novas passam por serializers de comando e services; leituras usam
  allowlists e escopo por Encontro.
- O frontend e a API legados continuam usando `/funcoes/` e
  `/participacoes-encontros/` durante essa expansão, sem dual-write.

### COMPAT e CUTOVER — D.3G

- Migrar a aba de equipes para snapshots, roles e comandos novos.
- Mudar `historico_equipes` e contadores para considerar somente
  `TrabalhoEncontro(status=TRABALHOU)`, preservando o formato público enquanto
  houver consumidor legado.
- Manter rotas antigas enquanto o frontend novo for validado. Writes legados
  não criam automaticamente trabalho canônico.
- Depreciação e remoção física ficam para etapa posterior, após inventário de
  consumidores, reconciliação dos dados e janela explícita de compatibilidade.

## Resultado da D.3B

### Models implementados

- `TemplateEquipeEncontro`, com tipo, código estável, apresentação, ordem,
  capacidades consultivas, ativação e timestamps.
- `TemplateRoleEquipe`, ligado por `PROTECT` ao template de equipe, com código,
  apresentação, ordem, quantidade estrutural, capability futura de presença,
  ativação e timestamps.
- `EquipeEncontro`, snapshot ligado por `PROTECT` ao Encontro e ao template de
  origem, com cópia dos dados operacionais da equipe.
- `RoleEquipeEncontro`, snapshot ligado por `PROTECT` à equipe da edição e à
  role de origem, com cópia da posição estrutural.
- `TrabalhoEncontro`, separado de participação, com FKs protegidas para
  Pessoa, Encontro e convite, role snapshot opcional, estados estruturais e
  timestamps.
- `ConviteEncontro.role_trabalho_proposta`, opcional e protegido, registra
  somente a proposta conhecida de role para convite de trabalho; não cria
  trabalho nem alocação.

O trabalho exige convite estruturalmente, conforme o desenho da D.3A, mas pode
nascer em `AGUARDANDO_ALOCACAO` sem role. A equipe é derivada da role snapshot,
evitando armazenar uma combinação equipe/role divergente. Não foi criado campo
de substituição, signal, service de fluxo ou efeito sobre `Frequencia`.

### Constraints e indexes

- Códigos únicos por tipo/template/Encontro nos escopos aprovados.
- Coerência interna de capacidades mínima e máxima, sem limitar ocupação.
- Quantidade estrutural positiva quando informada, sem implementar contagem de
  composição no banco.
- Role proposta aceita somente em convite `TRABALHAR`.
- Um trabalho por convite e unicidade forte por Pessoa/Encontro.
- Checks locais de status, role e timestamp de resultado.
- Índices de templates ativos, ordenação dos snapshots e consultas de trabalho
  por Encontro, Pessoa, role e status.

Tipo do Encontro, correspondência convite/Pessoa/Encontro, role pertencente ao
snapshot correto, composição, capacidade de ocupação, transições e
elegibilidade permanecem invariantes de services para a D.3C/D.3F.

### Migration

- Criada `0030_expand_equipes_trabalho_encontro`, dependente de
  `0029_expand_inscricao_convite_participacao`.
- A migration apenas cria models, FKs, índice, constraints e o campo opcional
  no convite. Não remove, renomeia ou transforma estrutura anterior.
- Não há `RunPython`, seed, dual-write ou alteração de dados existentes.
- O teste de migration confirmou o vínculo legado e o convite anteriores
  preservados, `role_trabalho_proposta` nula e todas as tabelas novas vazias.

Embora a D.3A previsse um seed versionado posterior, a instrução explícita da
D.3B proibiu `RunPython`. O catálogo não foi populado automaticamente; sua
provisão deverá ocorrer por caminho explícito e autorizado de sistema/Suporte,
sem inferência a partir do legado.

### Testes e validações

- Adicionados 12 testes estruturais para templates, roles, independência dos
  snapshots, convite com e sem proposta, trabalho sem alocação, FK de role,
  choices, unicidade, checks, `PROTECT`, ausência de `Frequencia`, estrutura
  legada e avanço da migration.
- Testes novos: 12/12 aprovados.
- Suíte backend: 308/308 aprovados; 2 skips condicionais já existentes.
- `python manage.py check --settings=setup.test_settings`: aprovado.
- `python manage.py makemigrations --check --dry-run
  --settings=setup.test_settings`: nenhuma mudança detectada.
- PostgreSQL não foi necessário para esta fundação estrutural; concorrência e
  validação real permanecem no fechamento D.3G.

### Débitos da D.3B

- O catálogo de templates continua vazio por decisão explícita de não executar
  carga automática nesta etapa.
- Criação de snapshots, validação cross-FK, transições e locks pertencem à
  D.3C.
- Reuniões, presença, autorização contextual, elegibilidade, novos contratos e
  cutover permanecem nos blocos D.3D–D.3G.
- Nenhum dado legado foi classificado como trabalho realizado.

### Arquivos alterados na D.3B

- `backend/core/models.py`
- `backend/core/migrations/0030_expand_equipes_trabalho_encontro.py`
- `backend/core/tests/test_encontro_trabalho_models.py`
- `docs/workplans/PHASE_1B_D3.md`

## Migrations previstas

1. `0030_expand_equipes_trabalho_encontro`: implementada na D.3B.
2. Próxima numeração disponível: `0031`; nenhuma migration é antecipada antes
   da mudança real de schema do bloco correspondente.
3. Reuniões/presenças e vínculo User/Pessoa continuam previstos para D.3D e
   D.3E, respectivamente.

A numeração deve ser reconfirmada no início de cada implementação. Nenhuma
migration transforma, renomeia ou remove tabelas/campos legados. Snapshots de
Encontros existentes serão criados somente por comando administrativo
explícito após revisão, não por `RunPython` automático.

## Backfill

**nenhum backfill automático nesta etapa**.

Não há evidência inequívoca para converter os vínculos atuais: nome livre,
booleano de coordenação e ordem não identificam role canônica nem comprovam
`TRABALHOU`. O mapping legado de funções está vazio, e parte dos Alpinistas
ainda pode não possuir `pessoa_id`. O seed de templates não muda dados de
operação e não é backfill.

Um futuro `POPULATE` exige catálogo real reconciliado, crosswalk explícito,
Pessoa resolvida e evidência externa do resultado. Casos não comprovados
devem permanecer apenas no contrato legado e em relatório de reconciliação.

## Plano de testes por bloco

### D.3B

- Concluída: models, choices, FKs `PROTECT`, snapshots independentes,
  constraints, índices e migration do estado `0029` para o novo schema.
- Nenhum seed foi executado, conforme a proibição de `RunPython` da etapa.

### D.3C

- Convite sem role e com role proposta; confirmação; criação idempotente do
  trabalho; uma Pessoa/Encontro; alocação, realocação, retirada, substituição e
  resultados.
- Rejeição de convite não confirmado, finalidade incorreta, Pessoa/Encontro
  divergentes, role cross-Encontro e excesso estrutural.
- Histórico somente para `TRABALHOU`; nenhum `PerfilAlpinista` ou `Frequencia`
  criado; rollback e concorrência real.

### D.3D

- Ordem de reuniões, presença única, vínculo cross-Encontro rejeitado,
  correção idempotente, flag derivado de revisão e ausência sem remoção
  automática.

### D.3E

- Vínculo User/Pessoa, default deny, Coordenação Geral apropriada, outra
  coordenação negada, cross-Encontro negado, lifecycle final/cancelado negado,
  bypass técnico e roles administrativas preservados.

### D.3F

- Cada código de elegibilidade/aviso, adaptador exato de atividade, ausência
  de evidência, override humano, caminhos de conclusão e regras conservadoras
  de AVC/Acampamento.

### D.3G

- Contratos antigos e novos, frontend, autorização transversal, migrations,
  suíte integral e cenários concorrentes no PostgreSQL real isolado.

## Débitos e pendências humanas

- Não há decisão humana que bloqueie D.3B. A modelagem não depende de mapear
  os textos atuais.
- As regras adicionais de elegibilidade de trabalho para AVC e Acampamento não
  estão demonstradas. A decisão técnica conservadora é aviso e revisão humana,
  nunca bloqueio inventado; uma regra de produto futura poderá especializar o
  evaluator sem alterar o schema.
- A fonte canônica de atividade do Alpinista ainda não existe fora do legado.
  A policy adaptadora evita acoplar permanentemente o evaluator a
  `Alpinista.status`.
- Backfill e depreciação física permanecem bloqueados por reconciliação do
  catálogo e evidência de comparecimento, mas não bloqueiam a expansão.
- Resultados terminais não terão comando de correção nesta fase. Uma futura
  necessidade excepcional exigirá regra própria antes de ampliar a API, sem
  bloquear o fluxo operacional aprovado.

## Arquivos relevantes inspecionados na D.3A

- `backend/core/models.py`
- `backend/core/services/participacoes.py`
- `backend/core/services/encontros.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/urls.py`
- `backend/core/permissions.py`
- `backend/core/roles.py`
- `backend/core/admin.py`
- `backend/core/legacy/contracts.py`
- `backend/core/legacy/mappings.py`
- `backend/core/legacy/transformers/participacoes.py`
- migrations `0006`, `0007`, `0015`, `0021` e `0029`
- testes de participação, contratos, autorização, migrations e núcleo de
  Encontros diretamente relacionados
- `frontend/src/app/(painel)/encontros/[id]/page.tsx`
- `frontend/src/lib/sia-profile-contracts.ts`

## Documentação alterada na D.3A

- `docs/workplans/PHASE_1B_D3.md`

`docs/PROJECT_STATE.md` e `docs/00_HOME.md` não mudam: o estado global ainda é
Fase 1B.3D.3 em andamento e o roteamento já aponta para os documentos certos.

## Próximo passo

D.3C — implementar os services transacionais de preparação dos snapshots,
convite de trabalho, criação do trabalho confirmado, alocação, realocação,
resultado, retirada e substituição, com locks e testes de concorrência. Os
blocos de reuniões, autorização, elegibilidade e cutover permanecem em
D.3D–D.3G.

## Padrão de relatórios durante a D.3

Ao finalizar cada bloco:

1. registrar detalhes completos neste workplan;
2. não repetir regras estáveis do documento de domínio;
3. atualizar `docs/PROJECT_STATE.md` somente diante de mudança global;
4. atualizar `docs/00_HOME.md` somente quando o roteamento mudar;
5. entregar no chat apenas um resumo executivo curto.

## Histórico de execução

- 2026-10-04 — Vault preparado. Regras estáveis separadas do relatório vivo;
  nenhuma implementação iniciada.
- 2026-10-04 — D.3A concluída por inspeção estática. O legado foi inventariado,
  o desenho expansivo e transacional foi fechado, não foi identificado
  backfill seguro e D.3B foi definido como próximo bloco.
- 2026-10-04 — D.3B concluída. Models, migration expansiva e 12 testes
  estruturais foram adicionados; a suíte backend aprovou 308 testes, sem
  alteração ou população automática da estrutura legada.
