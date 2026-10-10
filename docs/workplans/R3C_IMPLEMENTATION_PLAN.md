# R.3C.7 — Plano de implementação

## Status

A arquitetura, a ficha pública e a modelagem conceitual foram aprovadas. Este
documento decompõe a implementação futura, mas não inicia código, migrations,
infraestrutura, testes ou cutover.

R.3C pode ser encerrada como checkpoint de arquitetura e planejamento depois
desta decomposição. R.3 permanece aberta. O primeiro bloco futuro será
`R.3I.1`.

## Estratégia

- Implementar por expansão, com commits pequenos e reversíveis.
- Preservar `Inscricao`, `ConviteEncontro`, frontend e endpoints legados até
  cutover explícito.
- Separar models/migrations, services, API, BFF, frontend, autorização e
  infraestrutura sempre que puderem ser revisados isoladamente.
- Introduzir auditoria estruturada antes dos comandos sensíveis que dependem
  dela.
- Não expor endpoint público pelo frontend antes de backend e BFF possuírem
  minimização, CSRF/Origin, throttling e sanitização próprias.
- Validar concorrência real somente nos checkpoints PostgreSQL definidos.
- Escrever testes em cada bloco; suítes completas, PostgreSQL e build são
  comandos manuais do usuário.
- Fazer cutover apenas depois de backend canônico, operação interna, fluxo
  público e regressão estarem aprovados.

## Dependências reais

- O domínio Django permanece concentrado em `backend/core/models.py`; a
  migration mais recente é `0038_calendario_publicacao_layout`.
- Services novos seguem os módulos em `backend/core/services/`, com
  `transaction.atomic`, `select_for_update` e tradução de `IntegrityError`.
- Serializers, views, rotas e policies ainda são centralizados em
  `serializers.py`, `views.py`, `urls.py` e `permissions.py`; novos domínios
  devem manter contratos allowlist e default deny.
- `ConviteEncontro` já garante unicidade Pessoa × Encontro × finalidade e é a
  autoridade lógica a preservar. `ParticipacaoEncontro` e `TrabalhoEncontro`
  continuam fatos separados.
- `CalendarioEncontro`/`DiaEncontro` fornecem as datas oficiais e o comando de
  reprogramação que deverá disparar reconciliação de elegibilidade.
- `VinculoUsuarioPessoa`, `TrabalhoEncontro`, `RoleEquipeEncontro` e
  `EquipeEncontro.codigo` permitem derivar o vínculo contextual com Coordenação
  Geral sem cadastro paralelo.
- A API Django aplica `HasAnySiaRole` por padrão; qualquer endpoint anônimo
  exigirá permission explícita, contrato mínimo e throttle próprios.
- O BFF interno `/api/sia/[...path]` é autenticado e usa allowlist. O fluxo
  público precisa de rota separada, sem ampliar genericamente essa allowlist.
- `frontend/src/proxy.ts` protege apenas rotas privadas conhecidas; a rota
  pública deverá ser excluída deliberadamente do guard autenticado.
- A aplicação já possui double-submit e validação exata de Origin reutilizáveis
  no BFF, mas não possui contratos públicos de negócio ou antiabuso.
- Mídia é privada e entregue por actions autenticadas. A foto ainda não
  resolvida exigirá novo vínculo protegido, sem `/media` público.
- WeasyPrint e o padrão de `FileResponse` já existem para o Calendário; os PDFs
  do Pré podem reutilizar a infraestrutura de renderer, não o model de
  publicação.
- Redis, Celery, Beat, adapters de envio e configuração SMTP ainda não existem
  nas dependências/settings e devem entrar depois da lógica de domínio.
- A tela `frontend/src/app/(painel)/encontros/[id]/page.tsx` é monolítica e
  opera contratos legados. A integração canônica deve criar componentes e
  contratos novos antes de retirar o comportamento antigo.
- `seed_demo.py` e seu teste são únicos; só devem mudar quando as entidades e
  services correspondentes já existirem.

## Sequência de blocos

### R.3I.1 — Fundação de auditoria estruturada

**Prioridade:** FUNDACIONAL.

**Objetivo:** criar a entidade imutável e o service mínimo de auditoria de
Encontro, sem integrar ainda todos os comandos existentes.

**Depende de:** modelagem R.3C.6.

**Alterações:** model, migration expansiva, escrita estruturada atômica,
permission/read model restrito e testes de imutabilidade/minimização.

**Arquivos prováveis:** `backend/core/models.py`, nova migration,
`backend/core/services/auditoria_encontros.py`, `backend/core/permissions.py`,
`backend/core/tests/test_encontro_auditoria.py`.

**Testes a escrever:** constraints, ator/Encontro/objeto, justificativa,
imutabilidade, rollback e ausência de PII em descrição/log técnico.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_encontro_auditoria --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

**Critério de conclusão:** migration expansiva e service auditável aprovados,
sem alterar `LogSistema` ou consumidores legados.

**Commit sugerido:** `feat: add structured encounter audit foundation`

**Riscos:** duplicar PII na auditoria ou permitir alteração de eventos.

### R.3I.2 — Configuração estrutural de encontristas

**Prioridade:** FUNDACIONAL.

**Objetivo:** implementar `ConfiguracaoEncontristasEncontro` com capacidade,
faixa etária e janela.

**Depende de:** R.3I.1 para auditar capacidade futuramente.

**Alterações:** model one-to-one, migration expansiva, constraints locais,
admin opcional apenas se necessário e testes estruturais.

**Arquivos prováveis:** `models.py`, nova migration,
`test_encontristas_configuracao_models.py`.

**Testes a escrever:** unicidade por Encontro, capacidade positiva, idades e
janela coerentes, `PROTECT` e ausência de efeitos no legado.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_encontristas_configuracao_models --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

**Critério de conclusão:** configuração persiste sem alterar Encontro ou criar
backfill automático.

**Commit sugerido:** `feat: add encounter participant configuration`

**Riscos:** inserir regras cross-model em constraints frágeis.

### R.3I.3 — Services de configuração e elegibilidade

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** separar comandos de configuração, avaliação etária/conclusão e
reconciliação por reprogramação.

**Depende de:** R.3I.1–I.2, `DiaEncontro`, `ParticipacaoEncontro` e comandos de
reprogramação D.6.

**Alterações:** services distintos para capacidade/janela, elegibilidade e
reprogramação; resultado `não avaliável`; pendência de revisão; autorização
Diretoria/Suporte e leitura operacional de Fichas.

**Arquivos prováveis:** novos módulos em `core/services/`,
`permissions.py`, testes focados e integração mínima em
`services/comandos_calendario.py`.

**Testes a escrever:** limites de idade, aviso de mínima futura, conclusão
anterior, falta de calendário, aumento/redução, reprogramação antes/depois do
convite e auditoria.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_encontristas_configuracao_services core.tests.test_encontristas_elegibilidade --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** regras vivem no backend, sem fallback legado ou
cálculo duplicado no frontend.

**Commit sugerido:** `feat: add participant configuration and eligibility services`

**Riscos:** acoplar recálculo à transação do Calendário ou cancelar convite
automaticamente.

### R.3I.4 — Models da ficha e InscricaoEncontro

**Prioridade:** FUNDACIONAL.

**Objetivo:** criar inscrição, dados declarados/snapshot, responsável, ESPPA,
cuidado e correspondência cadastral.

**Depende de:** R.3I.2 e revisão final dos nomes concretos dentro do desenho
aprovado.

**Alterações:** models e migration expansiva, sem `RunPython`, cutover ou
backfill; unicidade parcial Pessoa × Encontro somente após resolução.

**Arquivos prováveis:** `models.py`, nova migration,
`test_inscricao_encontro_models.py`, `test_migrations.py`.

**Testes a escrever:** estados/origens, Pessoa nula, snapshot atual, CPF de
responsável repetido, duplicidade declarada permitida, unicidade após resolução,
componentes condicionais e proteção dos relacionamentos.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_inscricao_encontro_models core.tests.test_migrations --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

**Critério de conclusão:** fundação modular criada ao lado de `Inscricao`, sem
criar Pessoa, perfil ou vínculo institucional.

**Commit sugerido:** `feat: add encounter registration data model`

**Riscos:** model monolítico, constraint indevida sobre CPF declarado ou
exposição acidental de cuidado.

### R.3I.5 — Services de submissão e manutenção da ficha

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** implementar finalização atômica, validações da R.3C.4, snapshot
atual, cancelamento/reativação administrativa e nenhuma persistência de
rascunho.

**Depende de:** R.3I.3–I.4.

**Alterações:** services e validadores; separação CPF participante/responsável;
nenhuma associação cadastral automática.

**Arquivos prováveis:** `core/services/inscricoes_encontro.py`,
`validators.py`, `test_inscricao_encontro_services.py`.

**Testes a escrever:** Escalada/ESPPA, contato alternativo, endereço, menor,
sacramentos, cuidado condicional, cônjuge/referência, snapshot, rollback,
cancelamento/reativação e ausência de efeitos em Pessoa/Perfil.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_inscricao_encontro_services --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** uma chamada final cria a ficha coerente e nenhuma
falha parcial deixa registros órfãos.

**Commit sugerido:** `feat: add encounter registration services`

**Riscos:** snapshot divergente dos campos estruturados ou validação baseada
em estado do frontend.

### R.3I.6 — Resolução cadastral interna

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** permitir a Fichas comparar, rejeitar, vincular, criar Pessoa e
aplicar campos selecionados, sempre com auditoria.

**Depende de:** R.3I.1, I.4 e I.5.

**Alterações:** service de correspondências e resolução, serializers internos,
commands/API mínimos e permissions de Fichas/Diretoria/Suporte.

**Arquivos prováveis:** `services/resolucao_cadastral.py`, `serializers.py`,
`views.py`, `urls.py`, `permissions.py`, testes de service/API.

**Testes a escrever:** sugestão sem auto-match, rejeição, vínculo, criação,
seleção de campos, colisão Pessoa × Encontro, CPF coincidente não bloqueante,
rollback, auditoria e negações.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_inscricao_resolucao_services core.tests.test_inscricao_resolucao_api --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** Fichas resolve cadastro sem modificar snapshot nem
consolidar fichas incompatíveis silenciosamente.

**Commit sugerido:** `feat: add registration identity resolution flow`

**Riscos:** auto-merge indireto ou auditoria contendo PII integral.

### R.3I.7 — API pública inicial de inscrição

**Prioridade:** NECESSÁRIO PARA MVP; SEGURANÇA OBRIGATÓRIA.

**Objetivo:** expor somente leitura mínima do Encontro e submissão final.

**Depende de:** R.3I.3–I.5.

**Alterações:** serializers públicos allowlist, views explícitas anônimas,
throttle dedicado, minimização de erro/resposta e rotas separadas da API
privada. Nenhuma edição/cancelamento ainda.

**Arquivos prováveis:** `serializers.py`, `views.py`, `urls.py`,
`permissions.py`, `settings.py`, `test_inscricao_publica_api.py`.

**Testes a escrever:** janela/tipo, resposta mínima, ausência de IDs/PII,
default deny nos endpoints internos, throttling, payload inválido, logs
sanitizados e AVC/Acampamento negados.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_inscricao_publica_api --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** backend aceita submissão anônima segura sem tornar
nenhuma API interna pública.

**Commit sugerido:** `feat: add minimal public registration api`

**Riscos:** `AllowAny` amplo, enumeração de encontros ou PII em respostas.

### R.3I.8 — BFF público e fronteira de segurança

**Prioridade:** NECESSÁRIO PARA MVP; SEGURANÇA OBRIGATÓRIA.

**Objetivo:** criar gateway público mínimo distinto de `/api/sia`.

**Depende de:** R.3I.7.

**Alterações:** rotas BFF específicas, allowlist fixa, limites de corpo,
double-submit, Origin exata, no-store, timeouts/erros mínimos e rota pública
fora do guard de sessão. Nenhum JWT no browser.

**Arquivos prováveis:** `frontend/src/app/api/public/...`, novos helpers em
`lib/server/`, `proxy.ts`, testes de segurança BFF.

**Testes a escrever:** path traversal/destino arbitrário, CSRF, Origin,
métodos, tamanho de payload, indisponibilidade Django, ausência de cookies JWT
e preservação dos status públicos.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/server/public-bff-security.test.ts
npx tsc --noEmit --incremental false
npm run lint
```

**Critério de conclusão:** somente os contratos públicos aprovados atravessam
o BFF, sem relaxar a fronteira autenticada.

**Commit sugerido:** `feat: add secure public registration bff`

**Riscos:** compartilhar indevidamente refresh/JWT ou enfraquecer CSRF.

### R.3I.9 — Frontend público da ficha

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** implementar preenchimento, condicionais, revisão e confirmação
final em rota pública isolada.

**Depende de:** R.3I.8 e contrato R.3C.4.

**Alterações:** rota fora de `(painel)`, componentes por seção, contrato
TypeScript, validação, revisão, sucesso e acessibilidade/responsividade.

**Arquivos prováveis:** `frontend/src/app/inscricoes/...`, componentes públicos,
`lib/public-registration-contract.ts` e testes.

**Testes a escrever:** campos obrigatórios, contato alternativo, menor,
responsável, ESPPA, cuidado condicional, “Outro”, revisão/volta, submissão única,
sucesso e ausência de navegação privada.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/public-registration-contract.test.ts src/components/PublicRegistrationForm.test.tsx
npx tsc --noEmit --incremental false
npm run lint
```

**Critério de conclusão:** fluxo público cria inscrição somente na finalização
e não exibe dados internos.

**Commit sugerido:** `feat: add public encounter registration form`

**Riscos:** persistir rascunho, duplicar regra etária ou misturar layout privado.

### R.3I.10 — Edição e cancelamento públicos

**Prioridade:** PÓS-MVP / pode esperar após validação da submissão inicial.

**Objetivo:** permitir recuperar, editar, cancelar e reativar durante a janela
por mecanismo seguro.

**Depende de:** R.3I.7–I.9 e decisão técnica de token/rate limit.

**Alterações:** credencial opaca com armazenamento seguro, expiração/revogação,
commands backend, BFF e UI pública; sem expor identificador interno.

**Arquivos prováveis:** models/migration se necessária, services, API pública,
BFF, componentes e testes de segurança.

**Testes a escrever:** token inválido/expirado/revogado, tentativas, janela
fechada, cancelamento sem delete, reativação sem duplicar e resposta mínima.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_inscricao_publica_acesso --settings=setup.test_settings
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/public-registration-access.test.ts
npx tsc --noEmit --incremental false
```

**Critério de conclusão:** somente o titular do segredo consegue operar dentro
da janela, sem reutilização indevida.

**Commit sugerido:** `feat: add secure public registration management`

**Riscos:** tratar data de nascimento como senha ou armazenar token em claro.

### R.3I.11 — Models de campanha, rodada, oportunidade e entrega

**Estado:** concluída em 9 de outubro de 2026.

**Prioridade:** FUNDACIONAL para campanha.

**Objetivo:** criar as quatro estruturas ao redor de `ConviteEncontro`.

**Depende de:** R.3I.2, I.4 e semântica D.2 preservada.

**Alterações:** models, migration expansiva, estados/constraints/índices e
nenhum envio real.

**Arquivos prováveis:** `models.py`, nova migration,
`test_campanha_convites_models.py`.

**Testes a escrever:** cardinalidades, sequência de rodada, oportunidade única,
token/digest único, entregas por canal, checks de timestamps e `PROTECT`.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_campanha_convites_models --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

**Critério de conclusão:** schema expansivo sem alterar status ou constraints de
`ConviteEncontro`.

**Commit sugerido:** `feat: add encounter invitation campaign models`

**Riscos:** transformar convite em linha por rodada ou guardar token reversível.

**Implementação:** a migration expansiva
`0044_expand_campanha_convites` adicionou as quatro estruturas sem alterar
`ConviteEncontro`. A campanha preserva início, autor, prazo e encerramento; a
rodada possui sequência e tipo canônicos; a oportunidade liga uma rodada ao
convite lógico e armazena somente digest SHA-256; a entrega mantém uma linha
lógica por oportunidade/canal, contador e timestamps de tentativas, resultado,
retry, erro técnico sanitizável e chave de idempotência. Os vínculos históricos
usam `PROTECT`, e constraints locais cobrem escolhas, unicidades e coerência
temporal. Não há envio, endpoint, geração/validação HTTP de token ou service de
lifecycle nesta etapa.

Em termos canônicos: `ConviteEncontro` continua sendo o vínculo lógico;
`OportunidadeConviteEncontro`, a oportunidade daquela rodada; e
`EntregaConviteEncontro`, a operação de transporte por canal. Uma nova rodada
nunca cria outro convite lógico para representar a mesma relação.

**Validação:** os testes estruturais foram escritos em
`core/tests/test_campanha_convites_models.py`. A execução permanece manual,
conforme a política do projeto; foram executados apenas os checks baratos
registrados na entrega da etapa.

### R.3I.12 — Services de campanha e lista de espera

**Estado:** concluída em 9 de outubro de 2026.

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** implementar início manual, prazo, rodadas, prorrogação, recusa,
reabertura e projeção da lista de espera.

**Depende de:** R.3I.3, I.6 e I.11.

**Alterações:** services separados de lifecycle, seleção elegível e rodada;
commands internos e auditoria; sem transporte assíncrono.

**Arquivos prováveis:** `services/campanhas_convites.py`, serializers/views,
permissions e testes.

**Testes a escrever:** início único, prazo, aguardando decisão, encerramento,
prorrogação sem ressuscitar link, recusa sem reenvio automático, lista derivada
sem prioridade, nova vaga e ausência de canal.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_campanha_convites_services core.tests.test_campanha_convites_api --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** campanha opera deterministicamente sobre inscrições
resolvidas e convites existentes, sem enviar mensagens.

**Commit sugerido:** `feat: add invitation campaign lifecycle`

**Riscos:** lista de espera persistida como prioridade ou reenvio de recusados.

**Implementação:** `core.services.campanhas_convites` concentra seleção,
projeção e comandos transacionais sobre inscrições resolvidas e
`ConviteEncontro` existentes. O início manual cria uma única campanha e uma
rodada `INICIAL`; o vencimento leva de forma idempotente a
`AGUARDANDO_DECISAO`, quando Fichas decide entre encerrar ou prorrogar. A
prorrogação cria outra rodada e outros digests, sem ressuscitar oportunidades
anteriores. Recusa explícita não causa reenvio automático; eventual reabertura
é manual, justificada, auditada e cria somente para o convite escolhido uma
nova oportunidade em rodada `REPOSICAO`.

A espera é uma projeção sem posição ou prioridade persistida. Quando uma vaga
surge, a reposição oferece novas oportunidades a todos os elegíveis aplicáveis,
sem eleger um primeiro colocado. Ausência de e-mail e WhatsApp permanece
visível como `sem_canal`, sem tornar a Pessoa inelegível nem criar uma entrega
fictícia. Fichas conduz os comandos internos; Diretoria e Suporte possuem
somente consulta da campanha e das projeções, e o superuser permanece como
bypass técnico. Os contratos mínimos não expõem token, digest ou PII de
contato. Esta etapa não implementa transporte, resposta pública ou
concorrência da última vaga.

**Validação:** foram escritos testes focados de services e API para lifecycle,
autorização, atomicidade, idempotência, auditoria minimizada e projeções. Sua
execução permanece manual conforme a política do projeto; não houve alteração
de schema nem migration nesta etapa.

**Correção one-shot:** cada oportunidade nova persiste somente o digest
SHA-256 e retorna o token bruto uma única vez em
`EmissaoOportunidadeConvite`, estrutura transitória tipada cujo campo sensível
é omitido de `repr`. Início, prorrogação, reabertura manual e reposição expõem
ao caller autorizado somente as emissões realmente novas; uma operação
idempotente sobre oportunidades existentes retorna zero emissões. Models ORM,
auditoria e respostas da API interna nunca fornecem token ou digest.

Um adapter futuro deverá consumir esse material ainda no boundary de emissão.
Se o transporte assíncrono exigir durabilidade depois desse boundary, o bloco
de transporte precisará aprovar explicitamente outra arquitetura segura; esta
correção não cria armazenamento reversível, outbox ou envio.

### R.3I.13 — Link público e resposta ao convite

**Estado:** concluída em 9 de outubro de 2026.

**Prioridade:** NECESSÁRIO PARA MVP; SEGURANÇA OBRIGATÓRIA.

**Objetivo:** consumir oportunidade uma única vez após token e nascimento,
atualizando `ConviteEncontro` atomicamente.

**Depende de:** R.3I.8, I.11 e I.12.

**Alterações:** service transacional, endpoint/BFF públicos mínimos, limitação
de tentativas, suspensão/expiração/invalidação e UI de confirmar/recusar.

**Arquivos prováveis:** services de oportunidades, API, BFF público, página de
convite e testes backend/frontend.

**Testes a escrever:** token imprevisível/digest, nascimento inválido,
rate limit, resposta única, recusa, link read-only, suspensão por reprogramação,
expiração, minimização e consistência convite/oportunidade.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_oportunidade_convite_services core.tests.test_convite_publico_api --settings=setup.test_settings
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/public-invitation.test.ts
npx tsc --noEmit --incremental false
```

Teste isolado da última vaga em PostgreSQL efêmero, sem acesso ao `sia_dev`:

```bash
cd /home/vinicius/projects/Legio_MEB/backend
pg_virtualenv -v 16 bash -c '
export DJANGO_SECRET_KEY="test-only-key-not-for-production"
export JWT_SIGNING_KEY="test-only-jwt-key-not-for-production"
export DJANGO_ALLOWED_HOSTS="testserver,localhost"
export POSTGRES_DB="$PGDATABASE"
export POSTGRES_USER="$PGUSER"
export POSTGRES_PASSWORD="$PGPASSWORD"
export POSTGRES_HOST="$PGHOST"
export POSTGRES_PORT="$PGPORT"
exec ./.venv/bin/python manage.py test \
  core.tests.test_oportunidade_convite_services.OportunidadeConviteConcurrencyTests \
  --settings=setup.settings --verbosity=2 --noinput
'
```

**Critério de conclusão:** cada oportunidade aceita no máximo uma decisão e
nenhuma resposta isolada ultrapassa capacidade.

**Commit sugerido:** `feat: add secure public invitation response`

**Riscos:** enumeração, replay, data de nascimento como segredo único e corrida
na última vaga.

**Implementação:** o segredo one-shot emitido pela campanha permanece somente
em memória no boundary de emissão; o banco conserva exclusivamente seu digest
SHA-256. A superfície pública exige token opaco e nascimento canônico da
`Pessoa`, responde de forma uniforme antes dessa autenticação completa e é
protegida por throttle próprio. Depois da validação, o contrato allowlist
expõe apenas título, datas, prazo, finalidade e estado necessários à decisão.

Confirmação e recusa bloqueiam a configuração de encontristas como mutex,
recarregam oportunidade e convite e produzem uma única decisão transacional.
A confirmação revalida prazo, campanha, rodada, elegibilidade e capacidade. A
primeira confirmação que ocupa a última vaga vence; as demais oportunidades
pendentes da mesma rodada são invalidadas sem transformar seus convites em
recusa. Uma vaga futura exige nova rodada `REPOSICAO` e novos tokens. Replay de
uma oportunidade consumida é somente leitura e não altera a primeira decisão
nem duplica auditoria.

Expiração é reconciliada de modo lazy. Reprogramação chama explicitamente a
reconciliação de elegibilidade e suspende oportunidades pendentes afetadas,
sem signal e sem resposta automática. Confirmação, recusa, suspensão e
invalidação por lotação geram auditoria estruturada sem token, digest,
nascimento ou PII.

A correção estrutural posterior criou a migration expansiva
`0045_alter_eventoauditoriaencontro_ator`: `ator` passou a aceitar `NULL` para
ações públicas reais, preservando `PROTECT` quando houver usuário interno. O
service canônico exige ator ativo para origem interna e aceita ator ausente
somente quando a origem pública é informada explicitamente; nesse caso, a
origem também integra os JSONs minimizados do evento. Não foi criada constraint
SQL de ator/origem porque `origem` não é coluna do model, mas dado estruturado
nos JSONs de auditoria; a invariável permanece centralizada no service, sem
ator técnico ou fallback para o iniciador da campanha.

O mutex de capacidade da configuração de encontristas e a contagem de
confirmações foram compartilhados pelos caminhos público e interno. Assim,
qualquer Encontro com capacidade configurada rejeita uma confirmação interna
que produziria `N + 1`, e a corrida pública × interna fica reservada ao teste
focado em PostgreSQL isolado.

O BFF usa endpoint Django fixo, payload allowlist, timeout, `no-store`,
same-origin e CSRF double-submit, sem encaminhar JWT, cookies ou headers do
browser. A página pública `/convites/[token]` aplica `noindex` e política de
referrer, solicita nascimento antes de revelar o Encontro, exige confirmação
explícita para recusar e remove ações após qualquer estado terminal. O token
não integra chamadas internas por URL nem headers e não é registrado por
telemetria custom.

**Validação:** foram escritos testes focados de service, API, BFF e componente,
além dos testes PostgreSQL para a corrida pública × pública e pública ×
interna pela última vaga. Os testes focados em SQLite e Vitest são executados
separadamente; os testes concorrentes permanecem reservados à execução manual
em PostgreSQL isolado, conforme a política do projeto.

### R.3I.14 — Adapters de e-mail e WhatsApp

**Estado:** concluída em 10 de outubro de 2026.

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** definir interfaces independentes de provider e implementações de
desenvolvimento.

**Depende de:** R.3I.11.

**Alterações:** adapter SMTP configurável/Mailpit, mock WhatsApp sucesso/falha,
configuração por ambiente e testes sem rede.

**Arquivos prováveis:** `core/notifications/`, `settings.py`, `.env.example` se
existir, requirements somente se tecnicamente necessário e testes de adapters.

**Testes a escrever:** payload mínimo, sucesso/falha, timeout sanitizado,
configuração ausente e nenhuma credencial/log sensível.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_convite_delivery_adapters --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** campanha conhece somente a interface e os testes não
dependem de SMTP/WhatsApp reais.

**Commit sugerido:** `feat: add invitation delivery adapters`

**Riscos:** acoplar provider ou registrar conteúdo/telefone/e-mail.

**Implementação:** `core.notifications` define contrato, payload e resultado
tipados, sem dependência de ORM ou do lifecycle da campanha. O payload contém
somente destinatário, nome público do Encontro, prazo e link seguro; os campos
de destinatário e link ficam fora de `repr`. O token one-shot pode atravessar
esse boundary apenas como dado transitório para compor a mensagem e não é
persistido, recuperado de digest, registrado ou devolvido no resultado.

E-mail usa um adapter SMTP baseado na infraestrutura nativa do Django, com
host, porta, TLS/SSL, autenticação, remetente e timeout configuráveis por
ambiente. Mailpit é somente uma configuração SMTP de desenvolvimento
documentada em `.env.example`, sem acoplamento do domínio. A mensagem textual
é mínima e não confunde resposta ao convite com presença, vaga garantida ou
participação concluída.

WhatsApp possui somente adapter mock determinístico nos modos `sucesso`,
`falha` e `timeout`, sem SDK, HTTP ou provider real. A factory resolve adapters
por settings e falha explicitamente para backends desconhecidos, permitindo
substituição futura sem alterar a campanha. Falhas de configuração, payload,
timeout, conexão e autenticação são reduzidas a códigos e categorias
sanitizados; nenhum payload é logado.

`EntregaConviteEncontro` não foi alterado nem persistido pelos adapters. O
orquestrador que registrará tentativas/resultados e o transporte assíncrono
durável continuam fora deste bloco e exigem decisão própria. Não houve
migration, endpoint, UI, disparo automático ou integração da campanha a um
provider concreto.

**Validação:** foram escritos testes sem rede em
`core/tests/test_convite_delivery_adapters.py` para contrato substituível,
payload mínimo, SMTP, remetente/timeout configuráveis, falhas sanitizadas,
segredo ausente de `repr` e logs, factory sem fallback e os três modos do mock
WhatsApp. A execução focada e os checks baratos ficam registrados na entrega
do bloco; nenhuma suíte completa foi executada.

### R.3I.15 — Infraestrutura assíncrona e tasks

**Estado:** concluída em 10 de outubro de 2026.

**Prioridade:** NECESSÁRIO PARA MVP operacional.

**Objetivo:** introduzir Redis, Celery Worker/Beat e tasks idempotentes após a
lógica estar estável.

**Depende de:** R.3I.12 e I.14.

**Alterações:** dependências, settings, app Celery, tasks de entrega/retry/prazo
e reconciliação, health/ops mínimos e configuração local documentada.

**Arquivos prováveis:** `requirements.txt`, `setup/celery.py`, settings,
`core/tasks.py` ou pacote de tasks, units/systemd locais documentadas e testes.

**Testes a escrever:** idempotência, retry limitado, prazo, falha total não
bloqueante, capacidade reaberta e task duplicada.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_convite_tasks --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/celery -A setup inspect ping
```

**Critério de conclusão:** PostgreSQL segue como autoridade e reiniciar worker
não duplica oportunidade ou entrega.

**Commit sugerido:** `chore: add asynchronous invitation processing`

**Riscos:** estado de negócio no Redis, task publicada antes do commit ou
dependência operacional não documentada.

**Implementação:** Celery/Redis foram introduzidos somente como transporte e
agendamento operacional. PostgreSQL preserva todo estado canônico. Cada nova
oportunidade com canal aplicável cria, na mesma transação, uma única outbox com
token cifrado via Fernet e uma entrega por canal; `on_commit` publica somente o
ID da outbox. O worker resolve destinatários no momento do envio, processa
e-mail e WhatsApp mock de modo independente, limita cada canal a três
tentativas com backoff determinístico e destrói o ciphertext quando todos os
canais terminam. O Beat reconcilia outboxes, prazos vencidos e sinais duráveis
de reposição, permitindo recuperar perda de publicação no broker sem inventar
token para oportunidades históricas.

O processamento automático de prazo somente leva a campanha a
`AGUARDANDO_DECISAO`; prorrogar e encerrar continuam decisões humanas de
Fichas. Reposição automática exige `SinalReposicaoCampanha` criado numa
transição observável de lotado para disponível. O aumento de capacidade já
produz esse sinal no mesmo fluxo transacional. Não foi encontrado no domínio
atual um command legítimo para retirar/corrigir um convite já `CONFIRMADO`;
portanto, nenhum fluxo novo foi inventado, e a primitive de registro da
transição fica disponível para integração pelo futuro command legítimo.

A auditoria distingue `interna`, `publica` e `automatica`: somente a interna
aceita e exige usuário ativo; pública e automática exigem `ator=None`. A
migration expansiva `0046_expand_outbox_e_sinal_reposicao` não altera nem
preenche oportunidades anteriores. Operação local, saúde, configuração e
exemplos de systemd estão em `docs/operations/INVITATION_ASYNC.md`.

**Validação:** `core/tests/test_convite_tasks.py` cobre atomicidade,
criptografia, publicação pós-commit, falha do broker, reconciliação,
independência dos canais, retries, idempotência, limpeza do segredo, prazo
automático, auditoria automática e sinal de reposição. O módulo focado e os
checks baratos foram executados; suíte completa e serviços externos reais
permanecem para validação manual/checkpoint.

### R.3I.16 — Checkpoint PostgreSQL de campanha e capacidade

**Estado:** preparado em 10 de outubro de 2026; execução PostgreSQL manual
pendente de revalidação após correções do primeiro checkpoint.

**Prioridade:** NECESSÁRIO PARA MVP; CHECKPOINT.

**Objetivo:** validar locks, constraints e idempotência em PostgreSQL real.

**Depende de:** R.3I.11–I.15.

**Alterações:** somente testes concorrentes e correções mínimas comprovadas.

**Arquivos prováveis:** `test_campanha_convites_concurrency.py` e services
afetados.

**Testes a escrever:** última vaga, resposta duplicada, oportunidade/rodada
duplicadas, retry duplicado, aumento/redução de capacidade e confirmação ×
reprogramação.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
pg_virtualenv -v 16 bash -c '
export DJANGO_SECRET_KEY="test-only-key-not-for-production"
export JWT_SIGNING_KEY="test-only-jwt-key-not-for-production"
export DJANGO_ALLOWED_HOSTS="testserver,localhost"
export POSTGRES_DB="$PGDATABASE"
export POSTGRES_USER="$PGUSER"
export POSTGRES_PASSWORD="$PGPASSWORD"
export POSTGRES_HOST="$PGHOST"
export POSTGRES_PORT="$PGPORT"
exec ./.venv/bin/python manage.py test core.tests.test_campanha_convites_concurrency --settings=setup.settings --verbosity=2 --noinput
'
```

**Critério de conclusão:** nenhuma execução produz overbooking ou duplicação e
o cluster temporário é removido sem acessar `sia_dev`.

**Commit sugerido:** `test: validate invitation concurrency on postgres`

**Riscos:** teste artificial que não abre conexões reais por thread.

**Checkpoint preparado:**
`core/tests/test_campanha_convites_concurrency.py` reúne onze cenários que
exigem `connection.vendor == "postgresql"`, usam `TransactionTestCase`, uma
conexão Django por thread, `Barrier` e fechamento explícito das conexões. Os
dois cenários de última vaga da I.13 foram reutilizados e reforçados com
asserts de auditoria e ausência de recusa falsa. Os demais cobrem resposta
duplicada (`confirmar × confirmar` e `confirmar × recusar`), colisão da
unicidade oportunidade/rodada, sinal processado simultaneamente, outbox/task
duplicada, retry vencido concorrente, aumento de capacidade × processamento
do sinal, redução de capacidade × confirmação e confirmação × reprogramação.

As asserções verificam diretamente contagens, estados, sequências, auditoria,
limite de tentativas, unicidades, ciphertext e ausência de overbooking. SMTP,
WhatsApp e Redis reais não são usados. A execução SQLite foi feita apenas para
validar import/discovery e produziu 11 skips explícitos; ela não constitui
evidência de concorrência.

**Auditoria de locks:** confirmação pública e interna compartilham a
configuração de encontristas como mutex antes de contar ocupação. Alteração de
capacidade bloqueia configuração e depois consulta campanha/sinal;
reprogramação bloqueia Encontro/calendário antes de reconciliar oportunidades;
outbox e entregas são bloqueadas nessa ordem; processamento da reposição
bloqueia sinal, campanha e configuração. A ordem configuração → campanha do
aumento e campanha → configuração do processamento é uma inversão potencial;
o cenário capacidade × sinal foi escrito especificamente para tentar
reproduzi-la no PostgreSQL. Na preparação inicial, não houve refatoração
preventiva antes dessa evidência real.

**Primeira execução PostgreSQL:** 8/11 cenários passaram. PostgreSQL reproduziu
deadlock em capacidade × reposição e confirmação × reprogramação; o cenário de
reposição restante falhou por usar `aberta_em` em 2030 e tentar encerrar a
rodada com o relógio real de 2026. A colisão
`op_conv_rod_convite_unica` ocorreu dentro do cenário esperado e o respectivo
teste passou, confirmando a constraint.

**Correções preparadas para revalidação:** os fluxos compartilhados agora
adquirem explicitamente `Encontro → ConfiguracaoEncontristasEncontro` antes dos
demais recursos. O processamento de sinal continua com campanha e sinal nessa
ordem posterior; confirmação bloqueia oportunidade e convite somente depois
do mutex de Encontro/configuração. Consultas com `select_related()` restringem
`FOR UPDATE` a `of=("self",)`, removendo locks implícitos dos joins. O teste usa
um instante relativo a `timezone.now()`, preservando
`rod_conv_datas_coerentes`. Não foi adicionado retry de deadlock, nenhuma
constraint foi relaxada e nenhuma migration foi criada. A aprovação do
checkpoint continua dependente da reexecução dos mesmos onze cenários no
PostgreSQL 16 descartável.

### R.3I.17 — Models de Pré-Encontro e atendimento

**Estado:** implementada em 10 de outubro de 2026; validação focada aprovada.

**Prioridade:** FUNDACIONAL para Pré-Encontro.

**Objetivo:** criar `PreEncontro` zero-ou-um, atendimento, fatos operacionais e
foto privada vinculável.

**Depende de:** R.3I.1, I.2 e I.4.

**Alterações:** models/migration expansiva para Pré, atendimento, pagamento,
decisão de vaga e referência privada de foto; sem renderer ou UI.

**Arquivos prováveis:** `models.py`, migration,
`test_pre_encontro_models.py`.

**Testes a escrever:** unicidade do Pré, atendimento com/sem ficha/Pessoa,
unicidades condicionais, pagamento, regularização preservando origem, foto
privada e ausência de relação com Preparatória.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_pre_encontro_models --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

**Critério de conclusão:** estrutura suporta os três cenários de chegada sem
criar aptidão ou overbooking por `save()`.

**Commit sugerido:** `feat: add pre-encounter check-in models`

**Riscos:** confundir Pré com reunião preparatória ou exigir Pessoa/inscrição.

**Implementação:** a migration expansiva `0047` adiciona `PreEncontro`,
`AtendimentoPreEncontro`, `PagamentoPreEncontro`,
`DecisaoVagaPreEncontro` e `FotoTemporariaPreEncontro`. O atendimento aceita
inscrição, Pessoa ou snapshot avulso mínimo e preserva os dados informados
quando os vínculos são acrescentados. Unicidades condicionais protegem
inscrição, Pessoa e CPF conhecido dentro do mesmo Pré. Pagamento, decisão e
foto são fatos separados e nenhum model calcula aptidão, altera capacidade ou
promove a inscrição.

A foto reutiliza a referência de arquivo protegida do projeto, com chave
aleatória sob `pre_encontros/fotos/`, e permanece ligada ao atendimento mesmo
após a associação de Pessoa. Não foi criado endpoint nem exposição por
`/media`; `Pessoa.foto` e os arquivos existentes não foram alterados. O
`PreEncontro` referencia apenas `Encontro` e não possui relação com Agenda ou
reunião preparatória.

**Validação executada:** os 16 testes focados de
`core.tests.test_pre_encontro_models` passaram em SQLite, incluindo constraints
estruturais, regularização sem perda do snapshot e ausência de efeitos em
capacidade, convite, inscrição e `PerfilAlpinista`. `manage.py check`,
`makemigrations --check --dry-run`, `compileall` e `git diff --check` completam
as validações baratas do bloco.

### R.3I.18 — Services, capacidade e autorização do Pré

**Estado:** implementada em 10 de outubro de 2026; validação focada aprovada.

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** registrar presença, regularizar, conferir cuidado, pagamento,
resolver vagas e derivar aptidão.

**Depende de:** R.3I.3, I.6 e I.17.

**Alterações:** services separados por check-in, regularização, pagamento e
vaga; disputa `AGUARDANDO_DECISAO_DIRETORIA`; policy contextual via
Coordenação Geral canônica; auditoria.

**Arquivos prováveis:** `services/pre_encontro.py`, `permissions.py`, testes de
service/autorização.

**Testes a escrever:** três cenários de chegada, sem prioridade por check-in,
decisão só Diretoria, aumento por Suporte/Diretoria, não pago apto, foto/cuidado
não bloqueantes, outro Encontro negado, lifecycle FINALIZADO/CANCELADO/ADIADO e
papéis globais.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_pre_encontro_services core.tests.test_pre_encontro_authorization --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** aptidão é derivada e somente Diretoria resolve
disputa excepcional, sem cadastro paralelo de coordenador.

**Commit sugerido:** `feat: add pre-encounter operational services`

**Riscos:** reutilizar `concede_registro_presenca` para cuidado ou escolher por
ordem de chegada.

**Implementação:** `core.services.pre_encontro` separa check-in,
regularização, pagamento, conferência de cuidados, derivação de aptidão,
resolução de disputa e aumento de capacidade. Atendimento avulso puro não é
apto; pagamento, foto e conferência não entram na fórmula. Quando os candidatos
não confirmados excedem as vagas restantes, todos os indefinidos ficam em
`AGUARDANDO_DECISAO_DIRETORIA`, sem escolha por instante de chegada. Somente
Diretoria resolve a disputa de negócio; o aumento reutiliza o comando canônico
de configuração e vagas excepcionalmente aprovadas também protegem contra
redução que produziria overbooking.

A policy contextual deriva da cadeia `VinculoUsuarioPessoa` →
`TrabalhoEncontro` → equipe snapshot com código `coordenacao-geral`, sem usar
`concede_registro_presenca` e sem identidade paralela. Essa Coordenação pode
registrar pagamento e conferir cuidados apenas no próprio Encontro. Fichas e
as policies administrativas preservam seus comandos explícitos; decisão de
vaga não foi ampliada.

A migration expansiva `0048` cria somente
`ConferenciaCuidadoPreEncontro`, uma linha por atendimento, com referência aos
`DadosCuidadoInscricao`, ator, instante e marker `atualizado_em` observado. A
repetição atualiza a mesma linha; `EventoAuditoriaEncontro` registra cada ação
sem funcionar como estado operacional. Nenhum backfill foi criado.

**Validação executada:** 22 testes focados de services e autorização
passaram em SQLite. Eles cobrem as três origens, idempotência, contexto,
lifecycle, aptidão derivada, disputa sem prioridade, decisão exclusiva,
capacidade, marker dos cuidados, auditoria e negações. Os checks baratos do
bloco completam a validação local; PostgreSQL concorrente permanece fora deste
bloco.

### R.3I.19 — APIs internas do Pré-Encontro

**Estado:** implementada em 10 de outubro de 2026; validações focadas
aprovadas.

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** expor consultas e commands mínimos para a operação digital.

**Depende de:** R.3I.18.

**Alterações:** serializers por finalidade, endpoints de busca/check-in,
pagamento, cuidado, foto/regularização e decisão de vaga; BFF allowlist interna
mínima.

**Arquivos prováveis:** serializers/views/urls/permissions, `sia-proxy.ts` e
testes backend/BFF.

**Testes a escrever:** escopo por Encontro, nested mismatch `404`, contratos
sem cuidado por padrão, commands autorizados, default deny e proxy allowlist.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_pre_encontro_api --settings=setup.test_settings
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/server/pre-encounter-bff.test.ts
npx tsc --noEmit --incremental false
```

**Critério de conclusão:** API não oferece CRUD genérico nem vaza dados de
cuidado em contratos operacionais comuns.

**Commit sugerido:** `feat: expose pre-encounter operation api`

**Riscos:** ampliar `/api/sia` além dos paths necessários.

**Implementação:** a API interna ficou aninhada em
`/api/encontros/{encontro_id}/pre-encontro/`, com lista paginada, busca
escopada, detalhe operacional e commands explícitos para check-in,
regularização, pagamento, conferência de cuidados, foto, decisão de vaga e
aumento autorizado de capacidade. Os contratos comuns expõem somente
identificação operacional, origem e indicadores; o conteúdo de cuidado existe
exclusivamente no endpoint restrito próprio. Recursos pertencentes a outro
Encontro são resolvidos como `404`, e não foi criado CRUD genérico.

Comunicação pode consultar a projeção operacional mínima e operar upload,
substituição e preview autenticado da foto privada. Essa permissão não alcança
check-in, regularização, pagamento, cuidados, vaga ou capacidade. A foto usa
chave aleatória, não retorna storage key nem `/media`, e a substituição remove
o arquivo anterior somente depois do commit. As demais autorizações continuam
delegadas às policies e aos services canônicos da I.18.

O BFF ganhou uma allowlist específica que combina método e formato exato do
path de Pré-Encontro, valida IDs inteiros e rejeita traversal, URL absoluta,
segmentos extras e métodos não previstos. O browser continua sem acesso ao
JWT, e o proxy genérico não ganhou wildcard novo.

Como complemento de contrato para a I.20, o endpoint contextual
`capabilities/` passou a projetar consulta, check-in e capacidade no nível do
Encontro. O detalhe projeta regularização, pagamento, cuidados, foto e decisão
de vaga no nível do atendimento. Todas as flags reutilizam as policies
canônicas e incorporam a disponibilidade pelo lifecycle atual; lista e busca
permanecem leves. O client não precisa conhecer role nem vínculo contextual.

O fluxo guiado também recebeu lookups paginados e contextuais para inscrições
e Pessoas no novo atendimento, além de lookups aninhados no atendimento para
regularização. Os contratos retornam `inscricao_id` e `pessoa_id` canônicos,
nunca usam `Alpinista.id` como Pessoa, mascaram CPF/telefone e não expõem
cuidado ou perfil completo. A busca global de Pessoa não foi aberta: exige
termo e passa exclusivamente pela rota do Pré. O BFF permite somente os GETs
com shapes explícitos.

**Validação executada:** 26 testes focados de API backend e 35 casos focados
da allowlist BFF passaram. `manage.py check`, `compileall`, TypeScript e
`makemigrations --check --dry-run` também foram executados; nenhuma migration
foi gerada. A advertência do migration check corresponde apenas à
indisponibilidade esperada do PostgreSQL local dentro da sandbox.

### R.3I.20 — Frontend de check-in do Pré-Encontro

**Prioridade:** NECESSÁRIO PARA MVP.

**Objetivo:** criar tela operacional de busca, presença, regularização,
pagamento, foto, cuidado e decisão de vaga.

**Depende de:** R.3I.19.

**Alterações:** componentes e contratos separados por capability, estados de
conflito e operação responsiva; sem crachás.

**Arquivos prováveis:** componentes/rota de Pré dentro do workspace,
capabilities, contratos e testes frontend.

**Testes a escrever:** papéis, coordenação contextual, dados mínimos, disputa
pendente, ações da Diretoria, pagamento não bloqueante, ausência de ficha e
erros do backend.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/pre-encounter-contract.test.ts src/components/PreEncounterCheckin.test.tsx
npx tsc --noEmit --incremental false
npm run lint
```

**Critério de conclusão:** operação digital cobre os casos aprovados sem
recalcular autorização ou aptidão no client.

**Commit sugerido:** `feat: add pre-encounter check-in workspace`

**Riscos:** UI esconder conflito sem impedir comando ou exibir cuidado sem
capability.

### R.3I.21 — Fluxo protegido de foto

**Prioridade:** NECESSÁRIO PARA MVP do Pré.

**Objetivo:** armazenar foto privada antes da resolução e associá-la depois à
Pessoa, sem descarte.

**Depende de:** R.3I.17–I.19 e storage protegido existente.

**Alterações:** upload/download autenticados, associação transacional,
retenção/path definidos na implementação e BFF de mídia explícito.

**Arquivos prováveis:** model/migration se ajustada, service, views, storage,
`sia-proxy.ts` MEDIA_PATHS e testes.

**Testes a escrever:** não resolvida, associação posterior, arquivo ausente,
IDOR, rollback, privacidade e nenhuma rota `/media`.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_pre_encontro_fotos --settings=setup.test_settings
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/server/pre-encounter-media.test.ts
```

**Critério de conclusão:** foto continua acessível apenas a autorizados e pode
ser vinculada sem perder a origem.

**Commit sugerido:** `feat: add protected pre-encounter photo flow`

**Riscos:** órfãos de storage e exposição direta de mídia.

### R.3I.22 — PDFs sob demanda do Pré-Encontro

**Prioridade:** PÓS-MVP / pode esperar após check-in digital.

**Objetivo:** gerar lista operacional e documento restrito de cuidado, sem
persistência.

**Depende de:** R.3I.19, autorização de cuidado e WeasyPrint existente.

**Alterações:** projeções/renderer separados, templates, views `FileResponse`,
autorização e BFF/download; nenhum model de publicação.

**Arquivos prováveis:** `services/exportacao_pre_encontro.py`, templates,
views/urls e testes.

**Testes a escrever:** conteúdo mínimo, linhas extras, marcação restrita,
ausência de saúde no PDF geral, autorização, bytes PDF e nenhum arquivo salvo.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_pre_encontro_pdfs --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** ambos os PDFs são transitórios e o restrito nunca é
gerado por usuário sem acesso aos dados.

**Commit sugerido:** `feat: add on-demand pre-encounter pdfs`

**Riscos:** reutilizar publicação do Calendário ou persistir PDF sensível.

### R.3I.23 — Auditoria das correções históricas existentes

**Prioridade:** NECESSÁRIO ANTES DO CUTOVER.

**Objetivo:** integrar auditoria estruturada a participação, trabalho/equipe,
capacidade e resolução cadastral.

**Depende de:** R.3I.1 e services canônicos correspondentes.

**Alterações:** commands de correção pós-finalização com justificativa onde
aprovada; leitura restrita da trilha.

**Arquivos prováveis:** services de participação/trabalho/configuração,
serializers/views de auditoria e testes.

**Testes a escrever:** justificativa obrigatória pós-finalizado, valores
anterior/novo, rollback, capacidade sem justificativa obrigatória e foto sem
exigência indevida.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_encontro_correcoes_auditadas --settings=setup.test_settings
./.venv/bin/python manage.py check
```

**Critério de conclusão:** correções sensíveis não ocorrem sem trilha atômica.

**Commit sugerido:** `feat: audit historical encounter corrections`

**Riscos:** mudar fluxo normal de fotos/palestrantes ou copiar valores sensíveis.

### R.3I.24 — Projeção canônica do Workspace e BFF interno

**Prioridade:** NECESSÁRIO PARA MVP de produto.

**Objetivo:** oferecer consultas agregadas e commands mínimos para Visão geral
e Encontristas sem consumir legado.

**Depende de:** R.3I.3–I.6, I.12–I.13 e I.18–I.19.

**Alterações:** projection service, serializers summary/full por capability,
API aninhada e allowlist BFF explícita; integração com Equipe, Formação e
Agenda existentes sem duplicá-las.

**Arquivos prováveis:** novo service de workspace, serializers/views/urls,
permissions, `sia-proxy.ts` e testes.

**Testes a escrever:** lifecycle, contagens reais, situações de encontristas,
privacidade, papéis, nested mismatch, paginação e nenhuma leitura de
`Alpinista.status`/vínculo legado.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_encontro_workspace_api --settings=setup.test_settings
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/server/encounter-workspace-bff.test.ts
```

**Critério de conclusão:** backend fornece uma fonte canônica completa para o
novo workspace, sem remover contratos antigos.

**Commit sugerido:** `feat: expose canonical encounter workspace`

**Riscos:** endpoint gigante, N+1 e contrato full para papéis summary.

### R.3I.25 — Frontend do Workspace de Encontros

**Prioridade:** NECESSÁRIO PARA MVP de produto.

**Objetivo:** substituir incrementalmente a página monolítica por Visão geral,
Encontristas, Equipe, Formação aplicável e Agenda.

**Depende de:** R.3I.20 e I.24.

**Alterações:** decomposição em componentes/contratos, capabilities e ações
canônicas; MME/Formação mantêm visões restritas próprias.

**Arquivos prováveis:** `app/(painel)/encontros/[id]/page.tsx`, novos
componentes, contracts/capabilities e testes.

**Testes a escrever:** áreas por papel/tipo/lifecycle, ações visíveis,
Encontristas canônicos, Equipe/Formação/Agenda preservadas, erros e mobile.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/frontend
npm test -- src/lib/encounter-workspace.test.ts src/components/EncounterWorkspace.test.tsx
npx tsc --noEmit --incremental false
npm run lint
```

**Critério de conclusão:** nova interface não usa fila, status ou ações legadas
para representar encontristas/equipe.

**Commit sugerido:** `feat: add canonical encounter workspace`

**Riscos:** cutover visual antecipado ou quebra das áreas D.3–D.6.

### R.3I.26 — Dataset de demonstração do novo fluxo

**Prioridade:** NECESSÁRIO PARA VALIDAÇÃO MANUAL; após models/services.

**Objetivo:** adicionar cenários controlados sem PII real e sem criar regras
paralelas ao domínio.

**Depende de:** R.3I.15, I.18 e I.24.

**Alterações:** `seed_demo.py` idempotente e teste do comando.

**Arquivos prováveis:** `management/commands/seed_demo.py`,
`test_seed_demo_command.py`, `docs/workplans/DEV_SEED.md`.

**Testes a escrever:** inscrições resolvida/não resolvida, menor/responsável,
cuidado, campanha, espera, Pré, sem confirmação, sem ficha regularizada,
pagamento, disputa e Coordenação Geral contextual.

**Validação manual:**

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test core.tests.test_seed_demo_command --settings=setup.test_settings
./.venv/bin/python manage.py seed_demo --reset
```

**Critério de conclusão:** duas execuções convergem e todos os cenários são
demonstráveis sem alterar autorização.

**Commit sugerido:** `chore: extend demo seed for encounter registration`

**Riscos:** seed contornar services ou conceder capability indevida.

### R.3I.27 — Cutover controlado e fechamento

**Prioridade:** NECESSÁRIO APÓS MVP VALIDADO.

**Objetivo:** tornar o fluxo canônico a interface operacional, preservar
compatibilidade e executar regressão final antes de qualquer depreciação.

**Depende de:** todos os blocos MVP, R.3I.16, I.23–I.26 e checkpoints manuais.

**Alterações:** remover chamadas legadas apenas do frontend, congelar endpoints
antigos como compatibilidade, documentar métricas/observação e marcar
depreciação futura. Nenhuma remoção física neste bloco.

**Arquivos prováveis:** página de Encontro, proxy/BFF, documentação de domínio,
`AUTHORIZATION_MATRIX`, `PROJECT_STATE` somente quando implementado, workplan
de execução e testes de regressão.

**Testes a escrever:** ausência de uso frontend de `Alpinista.status`,
`VinculoEncontroLegado`, `efetivar-encontristas` e `FuncaoEncontro`; contratos
canônicos, compatibilidade e autorização transversal.

**Validação manual:** comandos completos do checkpoint final descritos abaixo.

**Critério de conclusão:** frontend opera exclusivamente pelo domínio canônico,
legado permanece compatível e regressão/checkpoints são aprovados.

**Commit sugerido:** `feat: cut over encounter participant workspace`

**Riscos:** confundir retirada do frontend com autorização para apagar tabelas
ou endpoints.

## Checkpoints de regressão

Suítes completas não são executadas em cada bloco. O usuário executa os
checkpoints abaixo.

### C1 — Fundação e migrations, após R.3I.5

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

### C2 — Fluxo público inicial, após R.3I.9

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test --settings=setup.test_settings
cd /home/vinicius/projects/Legio_MEB/frontend
npm test
npm run lint
npx tsc --noEmit --incremental false
npm run build
```

### C3 — Campanha e concorrência, após R.3I.16

Executar a suíte backend completa e o comando PostgreSQL isolado documentado
em R.3I.16. Não usar `sia_dev`.

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
```

### C4 — Pré-Encontro, após R.3I.21

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test --settings=setup.test_settings
cd /home/vinicius/projects/Legio_MEB/frontend
npm test
npm run lint
npx tsc --noEmit --incremental false
```

Executar também o checkpoint PostgreSQL manual da disputa de capacidade quando
o teste existir:

```bash
cd /home/vinicius/projects/Legio_MEB/backend
pg_virtualenv -v 16 bash -c '
export DJANGO_SECRET_KEY="test-only-key-not-for-production"
export JWT_SIGNING_KEY="test-only-jwt-key-not-for-production"
export DJANGO_ALLOWED_HOSTS="testserver,localhost"
export POSTGRES_DB="$PGDATABASE"
export POSTGRES_USER="$PGUSER"
export POSTGRES_PASSWORD="$PGPASSWORD"
export POSTGRES_HOST="$PGHOST"
export POSTGRES_PORT="$PGPORT"
exec ./.venv/bin/python manage.py test core.tests.test_pre_encontro_concurrency --settings=setup.settings --verbosity=2 --noinput
'
```

### C5 — Antes do cutover, após R.3I.26

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py test --settings=setup.test_settings
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
cd /home/vinicius/projects/Legio_MEB/frontend
npm test
npm run lint
npx tsc --noEmit --incremental false
npm run build
```

Executar também os dois checkpoints PostgreSQL de campanha e Pré-Encontro.

### C6 — Fechamento, após R.3I.27

Repetir C5, validar migrations aplicadas em banco temporário, executar smoke
manual do fluxo público → resolução → campanha → convite → Pré → workspace e
registrar os resultados no workplan de implementação.

## Plano de commits

- Um commit por bloco concluído, salvo quando revisão humana pedir separação
  adicional entre migration, service, API ou frontend.
- Prefixos sugeridos: `feat:` para capacidades, `test:` para checkpoints
  isolados, `chore:` para infraestrutura/seed e `docs:` para fechamentos.
- Nunca usar `git add .`; stage apenas dos arquivos auditados no bloco.
- Migration e model correspondente ficam no mesmo commit; infraestrutura não
  entra junto da lógica de campanha.
- Cutover e remoção física nunca compartilham commit.

## Cutover

Marcos objetivos:

1. **Nova inscrição substitui a antiga:** submissão pública, resolução,
   campanha e operação interna aprovadas; frontend não cria `Inscricao` legada.
2. **Encontristas deixa `Alpinista.status`:** projeção do workspace cobre
   inscrição, convite, espera, Pré e participação, com regressão aprovada.
3. **Fila e `VinculoEncontroLegado` saem do frontend:** nenhum import, fetch ou
   action visível depende deles; endpoints antigos continuam compatíveis.
4. **`FuncaoEncontro` deixa a equipe:** UI usa `EquipeEncontro`, roles snapshot
   e `TrabalhoEncontro` em todos os comandos.
5. **Endpoints legados entram em depreciação:** telemetria/revisão comprova que
   não há consumidor conhecido e documentação aponta alternativa canônica.
6. **Remoção física:** somente workplan/migration futura, após ciclo de
   depreciação, profiling do legado e aprovação humana específica.

## MVP

O MVP ponta a ponta inclui R.3I.1–I.9, I.11–I.21 e I.24–I.26:

- configuração/elegibilidade;
- inscrição pública inicial e resolução;
- campanha, oportunidade, entrega mock/SMTP e concorrência;
- check-in, cuidado, pagamento, foto, aptidão e decisão de capacidade;
- workspace canônico e dataset demonstrável.

Segurança, privacidade, atomicidade e auditoria fundacional são obrigatórias e
não podem ser reclassificadas como refinamento.

## Pós-MVP

Podem esperar a primeira validação controlada, mas permanecem no escopo antes
do fechamento definitivo quando aplicável:

- R.3I.10 — edição/cancelamento público posterior;
- R.3I.22 — PDFs sob demanda;
- provider real de WhatsApp;
- refinamentos operacionais de retries/observabilidade;
- crachás, número de grupo da Pré e cores continuam backlog fora da primeira
  implementação.

R.3I.23 e o cutover não são opcionais: apenas ocorrem depois do MVP validado.

## Decisões bloqueantes

Não restou decisão de produto que impeça iniciar R.3I.1. As definições técnicas
de schema concreto, nomes finais, token, throttle, storage, renderer e tasks
devem ser fechadas dentro do bloco correspondente antes de escrever sua
migration ou expor seu contrato, sempre dentro das fronteiras já aprovadas.

Provider real de WhatsApp não bloqueia o MVP porque o mock de desenvolvimento
foi aprovado. SMTP institucional definitivo também não bloqueia adapters e
Mailpit locais.

## Critério de encerramento da R.3C

R.3C está suficientemente fechada para encerrar como checkpoint documental:

- regras funcionais e arquitetura aprovadas;
- modelagem revisada humanamente;
- dependências reais mapeadas;
- blocos, validações, checkpoints e cutover definidos;
- nenhuma decisão de produto bloqueia a fundação.

Isso não encerra R.3 nem declara implementação iniciada. O próximo checkpoint
é R.3I.1 — fundação de auditoria estruturada.
