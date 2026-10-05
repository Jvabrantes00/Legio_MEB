# Fase 1B.3D.3 — Equipes e Trabalho em Encontro

## Status geral

Fase em andamento. D.3A a D.3F estão concluídas. A fundação de equipes e
trabalho, services transacionais, reuniões, autorização contextual e
elegibilidade foram implementados e validados; D.3G é o próximo bloco.

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

Status: concluída em 2026-10-05.

### D.3D — Reuniões preparatórias e presença

Status: concluída em 2026-10-05.

### D.3E — Autorização contextual da Coordenação Geral

Status: concluída em 2026-10-05.

### D.3F — Elegibilidade e avisos para trabalhar

Status: concluída em 2026-10-05.

### D.3G — Compatibilidade, PostgreSQL, regressão e fechamento

Status: próximo bloco.

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

## Resultado da D.3C

### Services implementados

Foi criado `core/services/trabalhos.py` com operações explícitas, sem lógica em
`model.save()`, serializer ou signal:

- `preparar_equipes_encontro`: materializa templates ativos do tipo do
  Encontro, copia roles ativas e devolve o snapshot congelado. Catálogo vazio
  permanece vazio; uma repetição após a primeira materialização preserva
  integralmente os snapshots existentes.
- `criar_convite_trabalho`: reutiliza o service de convite da D.2 com
  finalidade `TRABALHAR`, aceita role proposta do mesmo snapshot e não cria
  trabalho implicitamente.
- `iniciar_trabalho_confirmado`: exige convite de trabalho confirmado, cria o
  vínculo de forma idempotente e usa `AGUARDANDO_ALOCACAO` sem proposta ou
  `ALOCADO` com proposta válida.
- `alocar_trabalho` e `desalocar_trabalho`: atribuem, realocam ou removem a
  role atual antes de resultado final, sempre dentro do snapshot do mesmo
  Encontro.
- `retirar_trabalho`: finaliza operacionalmente a escala sem registrar
  comparecimento e preserva a última role quando existente.
- `registrar_resultado_trabalho`: aceita somente `TRABALHOU` ou `FALTOU` para
  trabalho alocado; o mesmo resultado é idempotente e estados finais não são
  reabertos.
- `substituir_trabalho`: retira o ocupante anterior e aloca outra Pessoa na
  mesma role em uma única transação, sem entidade, timeline ou FK de
  substituição.

Convite de participação, convite não confirmado, role de outro Encontro e
role cuja origem seja incompatível com a equipe snapshot são rejeitados. As
capacidades recomendadas não bloqueiam alocação; somente
`quantidade_estrutural`, quando informada, é tratada como limite rígido.

### Transações, locks e concorrência

- Todas as mutações públicas usam `transaction.atomic`.
- A ordem normal de locks é Pessoa → Encontro → convite → trabalho → role;
  substituição bloqueia Pessoas, convites e trabalhos em ordem de PK antes da
  role compartilhada.
- A materialização bloqueia o Encontro antes de snapshots e templates. Isso
  serializa duas preparações e impede snapshots duplicados.
- Criação do trabalho bloqueia Pessoa, Encontro e convite e mantém as
  constraints de one-to-one e Pessoa/Encontro como defesa final.
- Alocação/realocação e resultado bloqueiam o trabalho; quantidade estrutural
  bloqueia a role antes de contar ocupantes `ALOCADO`.
- `IntegrityError` de criação concorrente é traduzido para erro de domínio;
  rollback transacional cobre falhas intermediárias da substituição.

Cinco testes de corrida real foram adicionados e condicionados a PostgreSQL:
materialização concorrente, criação concorrente do trabalho, alocação
concorrente sob quantidade estrutural, realocação concorrente e resultados
finais concorrentes. Eles permanecem pendentes de execução real na D.3G; não
foi solicitada saída da sandbox nesta etapa.

### Testes e validações

- Adicionados 22 testes de service: 17 aprovados na suíte SQLite e 5
  condicionados a PostgreSQL.
- Cobertura: snapshots por tipo, catálogo vazio, idempotência, independência
  do template, convite com e sem proposta, separação convite/trabalho,
  confirmação, criação do trabalho, cross-FK, alocação, realocação,
  desalocação, capacidade consultiva, quantidade estrutural, retirada,
  resultado, substituição, rollback e ausência de `Frequencia`.
- Suíte backend: 330/330 testes aprovados; 7 skips condicionais no total.
- `python manage.py check --settings=setup.test_settings`: aprovado.
- `python manage.py makemigrations --check --dry-run
  --settings=setup.test_settings`: nenhuma mudança detectada.
- Nenhum model ou migration precisou ser alterado na D.3C.

### Débitos da D.3C

- Os cinco testes concorrentes novos aguardam PostgreSQL real isolado na
  D.3G.
- O catálogo de templates permanece sem população automática.
- Auditoria de comandos será integrada na camada de API quando os novos
  contratos forem expostos; os services não recebem `User` nem registram PII.
- Reuniões/presença, autorização contextual, elegibilidade/avisos e cutover
  continuam fora deste bloco.
- Histórico e contadores públicos ainda usam o contrato legado até D.3G;
  canonicamente, o novo domínio já distingue `TRABALHOU` dos demais estados.

### Arquivos alterados na D.3C

- `backend/core/services/trabalhos.py`
- `backend/core/tests/test_encontro_trabalho_services.py`
- `docs/workplans/PHASE_1B_D3.md`

## D.3D — implementação de reuniões preparatórias e presença

### Models, migration e integridade

- `ReuniaoPreparatoriaEncontro` foi adicionada com Encontro protegido, ordem,
  data, horário, local, observações e timestamps. A ordem é positiva e única
  por Encontro; os índices cobrem ordenação e consulta por data no contexto da
  edição.
- `PresencaPreparatoria` foi adicionada com FKs protegidas para reunião,
  trabalho e `User` registrador, os três estados aprovados, justificativa
  opcional e timestamps.
- A unicidade reunião/trabalho e o conjunto válido de estados são protegidos
  no banco. A coerência cross-Encontro permanece no service, sem constraint
  SQL baseada em joins.
- A migration expansiva
  `0031_expand_reunioes_presencas_preparatorias` cria somente as duas tabelas,
  índices e constraints novos. Não há `RunPython`, transformação do legado ou
  backfill automático.

### Services e estado de revisão

- `criar_reuniao_preparatoria` e `editar_reuniao_preparatoria` serializam a
  ordem pelo lock do Encontro e traduzem conflitos de unicidade para erro de
  domínio. Edição não permite reatribuir a reunião a outro Encontro.
- `registrar_presenca_preparatoria` bloqueia o contexto operacional do
  trabalho antes da reunião e da presença, rejeita cross-FK e é idempotente
  quando o comando é repetido sem alteração.
- `corrigir_presenca_preparatoria` atualiza o registro existente sob lock e
  não cria uma segunda presença.
- `anotar_revisao_permanencia` expõe `requer_revisao` por `Exists` das
  ausências sem justificativa atuais; `trabalho_requer_revisao` oferece a
  mesma derivação pontual. Nenhum booleano redundante é persistido.
- Corrigir uma presença recalcula naturalmente o estado a partir do conjunto
  atual. Ausência injustificada não altera status ou role do trabalho e não
  cria `Frequencia`.

### Transações e concorrência

- Todas as mutações públicas usam `transaction.atomic`.
- Criação e reordenação bloqueiam o Encontro antes da reunião. Registro e
  correção preservam a ordem Pessoa → Encontro → convite → trabalho → reunião
  → presença, reutilizando o bloqueio transacional do contexto de trabalho.
- `UniqueConstraint` permanece a defesa final para ordem e presença em uma
  corrida. Esta etapa não antecipa os cinco testes PostgreSQL já reservados
  para a D.3G.

### Testes e validações

- Foram adicionados 13 testes estruturais, de service e migration: múltiplas
  reuniões, ordenação, conflito por Encontro, mesma ordem entre edições,
  edição, estados e justificativa, unicidade e idempotência, cross-FK,
  correção, derivação do estado de revisão pelo conjunto atual, ausência sem
  retirada, `PROTECT`, rollback, ausência de `Frequencia` e expansão sem
  população automática.
- Testes novos: 13/13 aprovados.
- Suíte backend: 343/343 testes aprovados; 7 skips condicionais já esperados.
- `python manage.py check --settings=setup.test_settings`: aprovado.
- `python manage.py makemigrations --check --dry-run
  --settings=setup.test_settings`: nenhuma mudança detectada.
- A validação desta etapa usou SQLite em memória. Nenhuma característica nova
  da D.3D exigiu PostgreSQL, e os testes concorrentes da D.3C permanecem para
  a D.3G conforme planejado.

### Débitos da D.3D

- Autorização contextual, permissions e contratos de API continuam fora do
  bloco e serão tratados na D.3E.
- O indicador de revisão já está disponível no domínio, mas sua exposição em
  contrato ocorrerá apenas junto da API apropriada.
- Elegibilidade, cutover legado e regressão PostgreSQL permanecem em D.3F e
  D.3G. Nenhuma remoção física ou dual-write foi introduzida.

### Arquivos alterados na D.3D

- `backend/core/models.py`
- `backend/core/migrations/0031_expand_reunioes_presencas_preparatorias.py`
- `backend/core/services/reunioes_preparatorias.py`
- `backend/core/tests/test_encontro_reunioes_preparatorias.py`
- `docs/workplans/PHASE_1B_D3.md`

## D.3E — autorização contextual da Coordenação Geral

### Vínculo explícito entre identidade e domínio

- `VinculoUsuarioPessoa` liga exatamente um `User` técnico a exatamente uma
  `Pessoa`, com FKs `PROTECT` e timestamps. Não há associação por nome, e-mail
  ou grupo Django, nem criação ou exclusão automática de conta.
- A migration expansiva `0032_vinculousuariopessoa` cria somente a tabela do
  vínculo e nasce vazia. Nenhum dado legado foi associado ou classificado.
- O vínculo é requisito apenas para a capability contextual. Suporte,
  Diretoria e Fichas continuam autorizados por seus papéis globais, sem
  converter Alpinistas operacionais em grupos administrativos.

### Policy e lifecycle

- `pode_registrar_presenca_preparatoria(user, encontro)` exige usuário
  autenticado e ativo. Para o caminho contextual, exige também vínculo
  explícito, `TrabalhoEncontro` atualmente `ALOCADO` no mesmo Encontro, role
  snapshot com `concede_registro_presenca=True` e origem estrutural coerente
  com o template da equipe snapshot.
- A checagem não depende do nome de apresentação da equipe ou da role.
  Coordenadores de outras equipes e integrantes comuns não recebem a
  capability.
- O acesso contextual é negado em `FINALIZADO` e `CANCELADO`; os demais
  estados preservam a avaliação operacional. Superuser técnico e os papéis
  administrativos Fichas, Diretoria e Suporte continuam sujeitos à matriz
  global, sem serem transformados em vínculo contextual.
- A permission DRF aplica default deny tanto na entrada quanto ao objeto.
  Ausência de vínculo é negada antes da resolução do payload; outro Encontro,
  trabalho retirado e role não elegível são negados sem escrita.

### API, services e auditoria

- `POST /api/presencas-preparatorias/` registra presença e
  `PATCH /api/presencas-preparatorias/{id}/corrigir/` corrige o registro.
  Não foram expostos listagem, leitura genérica, exclusão ou CRUD de equipes.
- A view limita-se a autorização, transação e auditoria. Criação e correção
  reutilizam os services da D.3D, que permanecem responsáveis por status,
  unicidade e coerência reunião/trabalho.
- O contrato usa allowlist e expõe somente IDs, status, justificativa e
  timestamps operacionais. Não há campos de saúde ou perfil pessoal.
- `registrada_por` preserva o autor no próprio registro. `LogSistema` registra
  criação/correção apenas por identificadores; falha do log reverte a mudança
  de presença na mesma transação.

### Testes e validações

- Foram adicionados 15 testes para vínculo one-to-one e `PROTECT`, migration
  vazia, papéis Fichas/Diretoria/Suporte, Coordenação Geral apropriada,
  coordenador de outra equipe, integrante comum, cross-Encontro, ausência de
  vínculo explícito, usuário inativo, lifecycle, trabalho retirado, registro,
  correção, auditoria e rollback, escopo global/saúde e preservação de `User`.
- Suíte backend: 358/358 testes aprovados; 7 skips condicionais já esperados.
- `python manage.py check --settings=setup.test_settings`: aprovado.
- `python manage.py makemigrations --check --dry-run
  --settings=setup.test_settings`: nenhuma mudança detectada.
- A etapa não exigiu PostgreSQL. Os testes concorrentes continuam reservados
  para a D.3G.

### Débitos da D.3E

- O processo administrativo de provisionar contas e vínculos explícitos
  permanece separado deste endpoint operacional; nenhuma API pública de
  gestão de `User` foi criada.
- Frontend para presença, elegibilidade/avisos e cutover continuam em blocos
  posteriores. A capability não concede gestão de equipe, participantes,
  saúde ou qualquer papel global.

### Arquivos alterados na D.3E

- `backend/core/models.py`
- `backend/core/migrations/0032_vinculousuariopessoa.py`
- `backend/core/permissions.py`
- `backend/core/serializers.py`
- `backend/core/views.py`
- `backend/core/urls.py`
- `backend/core/tests/test_encontro_autorizacao_contextual.py`
- `backend/core/tests/test_serializer_contracts.py`
- `docs/AUTHORIZATION_MATRIX.md`
- `docs/workplans/PHASE_1B_D3.md`

## D.3F — elegibilidade e avisos para trabalhar

### Motor e resultado estruturado

- `core/services/elegibilidade_trabalho.py` concentra toda a avaliação sem
  escrita ou dependência de permission DRF. `AvaliacaoElegibilidade` retorna
  `ELEGIVEL`, `AVISO` ou `BLOQUEIO`, motivos ordenados, códigos estáveis,
  mensagens humanas e contexto operacional serializável.
- O código distingue `AvisosElegibilidadePendentes` de
  `BloqueioElegibilidadeTrabalho`. Ambas as exceções preservam a avaliação
  completa para consumo futuro por serializer, API e auditoria.
- Avisos e bloqueios permanecem derivados; não foi criada tabela de alerta,
  histórico paralelo ou migration.

### Regras implementadas

- `PerfilAlpinista` ausente gera `PERFIL_ALPINISTA_AUSENTE`. A atividade lê
  somente o `Alpinista` legado ligado exatamente à mesma `Pessoa`: inatividade
  gera `ALPINISTA_INATIVO` e evidência ausente ou não conclusiva gera
  `ATIVIDADE_NAO_DETERMINADA`.
- Conclusões são lidas exclusivamente de `ParticipacaoEncontro` canônica com
  resultado `CONCLUIU`. O caminho Escalada sem AVC produz o bloqueio
  `AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA`; os caminhos aprovados por ESPPA e por
  Escalada mais AVC permanecem elegíveis.
- Ausência de evidência suficiente do caminho produz
  `CAMINHO_FORMATIVO_NAO_DETERMINADO`, sem inferência pelo legado. AVC e
  Acampamento produzem os códigos conservadores de revisão manual previstos,
  sem novo bloqueio de produto.
- Nenhuma regra consulta saúde, vínculo conjugal, frequência, nome livre de
  equipe ou quantidade anual de trabalhos.

### Capacidade e composição

- `avaliar_capacidade_equipe` calcula ocupação `ALOCADO` e emite avisos de
  mínimo não atingido ou máximo excedido. Referências consultivas nunca
  bloqueiam a operação.
- `avaliar_composicao_estrutural` usa somente
  `quantidade_estrutural` congelada nas roles snapshot. Falta de ocupantes é
  pendência/aviso; excesso é bloqueio estrutural.
- `avaliar_alocacao_trabalho` combina elegibilidade da Pessoa, capacidade da
  equipe e limite estrutural prospectivo da role, inclusive em realocação.

### Integração com os services

- Convite de trabalho, início com role proposta, alocação, realocação e
  substituição executam o mesmo evaluator centralizado. Bloqueios abortam a
  transação; avisos exigem `confirmar_avisos=True` para decisão humana
  explícita.
- A avaliação é anexada ao objeto retornado como
  `avaliacao_elegibilidade`, sem persistência redundante, para a futura API
  registrar a decisão e os códigos na auditoria.
- Reavaliações usam o estado atual, mas nunca reabrem nem alteram
  `TrabalhoEncontro` já finalizado. Os locks e constraints da D.3C continuam
  sendo a defesa transacional final.

### Testes e validações

- Foram adicionados 16 testes para Alpinista ativo/inativo, ausência de perfil
  ou atividade determinada, caminhos Escalada/ESPPA/AVC/Acampamento, códigos
  e mensagens, capacidades mínima/máxima, composição pendente/válida/excedida,
  convite, override, bloqueio de alocação, realocação, saúde, `Frequencia` e
  preservação do histórico concluído.
- Os testes existentes dos services foram adaptados para confirmar
  explicitamente os avisos dos fixtures legados sem perfil/conclusões, sem
  enfraquecer os cenários de bloqueio ou concorrência.
- Testes novos: 16/16 aprovados.
- Suíte backend: 374/374 testes aprovados; 7 skips condicionais já esperados.
- `python manage.py check --settings=setup.test_settings`: aprovado.
- `python manage.py makemigrations --check --dry-run
  --settings=setup.test_settings`: nenhuma mudança detectada.
- PostgreSQL não foi necessário; os cinco testes concorrentes permanecem para
  execução real na D.3G.

### Débitos da D.3F

- A futura API de comandos de trabalho deverá expor a avaliação estruturada e
  auditar `confirmar_avisos` com os códigos, sem dados pessoais sensíveis.
- A fonte canônica de atividade continua pendente; o adaptador legado exato é
  deliberadamente isolado no evaluator.
- Regras adicionais de trabalho em AVC/Acampamento continuam dependendo de
  decisão de produto e permanecem como revisão manual, não bloqueio.

### Arquivos alterados na D.3F

- `backend/core/services/elegibilidade_trabalho.py`
- `backend/core/services/trabalhos.py`
- `backend/core/tests/test_encontro_trabalho_elegibilidade.py`
- `backend/core/tests/test_encontro_trabalho_services.py`
- `docs/workplans/PHASE_1B_D3.md`

## Migrations previstas

1. `0030_expand_equipes_trabalho_encontro`: implementada na D.3B.
2. `0031_expand_reunioes_presencas_preparatorias`: implementada na D.3D.
3. `0032_vinculousuariopessoa`: implementada na D.3E.
4. Próxima numeração disponível: `0033`; nenhuma migration é antecipada antes
   de mudança real de schema.

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

- Concluída: snapshots, convite de trabalho, criação idempotente do vínculo,
  alocação, realocação, retirada, substituição e resultados finais.
- Validações de finalidade, confirmação, Pessoa/Encontro, origem da role,
  quantidade estrutural, rollback e ausência de `Frequencia` cobertas.
- Cinco cenários concorrentes estão implementados e condicionados ao
  PostgreSQL para execução na D.3G.

### D.3D

- Concluída: ordem de reuniões, presença única, vínculo cross-Encontro
  rejeitado, correção idempotente, flag derivado de revisão e ausência sem
  remoção automática.

### D.3E

- Concluída: vínculo User/Pessoa, default deny, Coordenação Geral apropriada,
  outra coordenação negada, cross-Encontro negado, lifecycle
  final/cancelado negado, bypass técnico e roles administrativas preservados.

### D.3F

- Concluída: códigos estruturados, adaptador exato de atividade, ausência de
  evidência, override humano, caminhos de conclusão, capacidade/composição e
  regras conservadoras de AVC/Acampamento.

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

D.3G — executar compatibilidade, validação PostgreSQL, regressão e fechamento
da Fase 1B.3D.3.

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
- 2026-10-05 — D.3C concluída. Services transacionais e 22 testes foram
  adicionados; a suíte backend aprovou 330 testes e os cinco novos cenários
  concorrentes permaneceram reservados para validação PostgreSQL na D.3G.
- 2026-10-05 — D.3D concluída. Reuniões preparatórias, presenças, services
  transacionais, migration expansiva e 13 testes foram adicionados; a suíte
  backend aprovou 343 testes, sem backfill ou alteração do fluxo legado.
- 2026-10-05 — D.3E concluída. Vínculo explícito User/Pessoa, policy
  contextual e API restrita de presença foram implementados; a suíte backend
  aprovou 358 testes sem criação automática de contas ou acesso a saúde.
- 2026-10-05 — D.3F concluída. Motor derivado de elegibilidade, capacidade e
  composição foi integrado aos services de trabalho; a suíte backend aprovou
  374 testes sem migration, nova tabela de alertas ou regra de saúde.
