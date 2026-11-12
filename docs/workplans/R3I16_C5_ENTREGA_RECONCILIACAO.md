# R.3I.16-C5 — Entrega externa de convites e reconciliação

> **Status: decisões funcionais e operacionais do C5.2 consolidadas (J1–J10,
> P1–P7, R3–R6.1 e D1–D5 [APR]); C5.3-B1 (schema e integridade, seção 16)
> implementado, aceito tecnicamente (A1, seção 16.15) e commitado localmente
> (C1, seção 16.16), sem ativação; demais mecanismos técnicos [REC] não
> aprovados; B2, B3 e B4 não iniciados.**
> Este documento consolida o diagnóstico C5.1 e a especificação C5.2. O código
> do B1 (models, migrations `0051`/`0052` e testes) está no commit local C1
> `1c42f634cda238e476f4e9376f4db7b307df288a`. Não autoriza B2–B4, C5.4, ativação, push, merge, deploy ou
> cutover. O estado corrente do
> projeto continua em [[../PROJECT_STATE|Estado do projeto]].

## Convenção

- **[APR]** — decisão aprovada pelo responsável do projeto.
- **[REC]** — proposta técnica do ARCH. **Não é aprovada** por constar aqui.
  Exige aprovação expressa antes de ser implementada.
- **[FATO]** — comportamento do código atual verificado por leitura estática.
  Nenhum teste, banco ou provedor foi executado na elaboração.

Referências de linha são do working tree no momento da consolidação e podem
deslocar-se.

## 1. Escopo e fora de escopo

Dentro: entrega externa de convites (outbox, entrega, tentativa), tratamento de
resultado incerto, reconciliação por Fichas, pendências internas, auditoria,
transição do legado e ativação segura.

Fora: API interna de aprovação de encaminhamentos por Fichas (frente
reservada e separada); provedor real de WhatsApp [APR J8-A]; reemissão de
convite, oportunidade, rodada ou token; qualquer alteração de D23-A, D24-A e
D25-A. A aprovação por Fichas não gera envio automático.

## 2. Diagnóstico (C5.1) — fatos

- [FATO] `processar_outbox_entrega_convite`
  (`backend/core/services/entregas_convites.py`) é `@transaction.atomic` e
  chama `adapter.entregar` dentro da transação, com `select_for_update` na
  outbox e nas entregas. Se o provedor aceitar e o commit ou a gravação do
  resultado falhar, tudo sofre rollback e o retry reenvia: semântica
  *at-least-once* sem deduplicação.
- [FATO] `EntregaConviteEncontro.chave_idempotencia` existe
  (`backend/core/models.py`) e nenhum código a utiliza; o payload do adapter
  não a contém.
- [FATO] O estado `ENVIANDO` existe no model e no CHECK e nunca é gravado.
- [FATO] Não existe estado para resultado incerto, nem identificador externo,
  nem histórico de tentativas (só contador e datas na própria entrega).
- [FATO] Timeout de SMTP e do mock de WhatsApp é classificado como temporário
  e reenviado automaticamente. Qualquer exceção SMTP fora de conexão é
  classificada como falha permanente.
- [FATO] Uma exceção não tratada do adapter propaga dentro do `atomic` e
  desfaz o registro de tentativas.
- [FATO] A outbox conclui e destrói o segredo cifrado quando todas as entregas
  estão `ENTREGUE` ou `FALHOU`; o CHECK `out_conv_segredo_lifecycle` exige
  segredo nulo em `concluida`.
- [FATO] O código atual não verifica `expira_em` da oportunidade antes de
  enviar.
- [FATO] O adapter SMTP não oferece idempotência, ID externo nem consulta de
  status. O adapter de WhatsApp é apenas mock determinístico.
- [FATO] Nenhum código fora de `entregas_convites.py`, dos testes e de
  `models.py` lê o status de entrega; reposição e campanhas não dependem dele
  hoje.

## 3. Princípios [APR]

1. Aceitação técnica pelo provedor **não equivale** a recebimento pelo
   destinatário.
2. Reenvios automáticos são suspensos enquanto o resultado externo for
   desconhecido.
3. Retomada automática apenas com prova confiável de que a chamada externa não
   começou. Ausência de registro de sucesso não é prova de não envio.
4. Fichas decide a reconciliação. Suporte investiga e apresenta evidências, sem
   autorizar reenvio.
5. Não há mensagens externas adicionais, oportunidades ou confirmações geradas
   pela reconciliação ou pelos alertas.
6. Nenhuma garantia *exactly-once* é prometida sem mecanismo externo
   verificável do provedor.

## 4. Decisões aprovadas

| Código | Decisão [APR] |
|---|---|
| J1 | Em condições normais, reconciliação exclusiva de Fichas. Sem bypass implícito de Diretoria, Suporte ou superusuário. A única exceção é a emergência formal por indisponibilidade de Fichas (P7), limitada e formalmente autorizada, cuja convivência com Fichas é regulada por R4-B (seção 9.2). |
| J2 | Alertas somente internos, na Central de Pendências. |
| J3-B | Falha comprovadamente anterior ao I/O suspende sem consumir tentativa; alerta técnico agrupado; recuperação controlada. |
| J4 | Token cifrado retido apenas durante a validade e a necessidade legítima. |
| J5 | Convite expirado não é enviado: registra `FALHOU`, sem consumir tentativa externa, com pendência para Fichas. |
| J6-A | Resultado tardio gera evidência e não altera automaticamente `INCERTA`. |
| J7-C | Lease configurável; valor inicial sujeito à homologação. |
| J8-A | WhatsApp real fora do C5.3; mantém-se o mock. |
| J9-A | Uma autorização de Fichas concede exatamente uma nova chamada externa, sem ciclo adicional de retries. |
| J10-A | Ativação controlada; rollback *fail-closed*, sem retorno automático ao worker antigo. |

### 4.1 Decisões P1–P7 [APR]

| Código | Decisão [APR] |
|---|---|
| P1-A | Alertas técnicos agrupados por causa, provedor e ambiente. Suporte recebe detalhes e a contagem dos convites afetados; Fichas recebe visão resumida na Central. Sem e-mails automáticos e sem retomada automática. |
| P2-A | Retomada de `SUSPENSA`: Suporte corrige a falha e registra evidências; Fichas autoriza a retomada, individual ou em lote; cada convite é revalidado antes do processamento; não consome tentativa quando comprovado que nenhuma chamada externa começou. |
| P3-A | Legado `PENDENTE` com tentativas anteriores e sem prova confiável: reenvio automático bloqueado. Identificação lógica `LEGADO_SEM_PROVA`, sem impor novo status no banco. Reconciliação por Fichas; Suporte apenas investiga. Inventário prévio antes de gerar pendências em massa. |
| P4-A | Lease configurável. 120 s é só referência provisória. Validação obrigatória na homologação antes da ativação; falha na validação bloqueia a ativação. |
| P5-A | Feature flag própria, desativada por padrão; fila Celery dedicada; configuração independente do lease. Nomes definitivos sujeitos à análise das convenções do repositório. |
| P6-A | Entrega `FALHOU` com oportunidade expirada permanece `FALHOU`. Novo envio nessa oportunidade é proibido. Fichas pode encerrar a pendência com justificativa e auditoria. Eventual nova oportunidade pertence a outro fluxo. |
| P7 | Emergência por indisponibilidade de Fichas, nos termos da seção 9.2. |

### 4.2 Decisões R3–R6 [APR]

| Código | Decisão [APR] |
|---|---|
| R3-A | Operador emergencial: o solicitante pode operar após aprovação independente. Suporte solicita e Diretoria aprova, ou vice-versa. Autoaprovação proibida. A autorização é vinculada a operador, escopo, ocorrências e prazo. |
| R3.1-A | Prazo de espera configurável por nível de urgência; exige tentativas de contato documentadas e critérios objetivos. Valores numéricos ainda não homologados. |
| R4-B | O retorno de Fichas não revoga automaticamente a autorização emergencial. Fichas, Suporte e Diretoria podem atuar simultaneamente dentro das respectivas competências. A autorização vale somente até o prazo originalmente concedido, dentro do escopo. Decisões concorrentes incompatíveis sobre a mesma ocorrência são impedidas. A exceção não vira acesso permanente. |
| R5-A | O operador emergencial não pode encerrar pendência `INCERTA` com resultado desconhecido; pode investigar e registrar evidências. A decisão institucional e o reenvio excepcional sem confirmação permanecem exclusivos de Fichas. |
| R6-A | `LEGADO_SEM_PROVA` deve ser bloqueado **obrigatoriamente no serviço/backend**, sem depender apenas de fila, task, reconciliador ou migration. Sem reenvio automático. Reconciliação e eventual autorização expressa por Fichas. Registros e histórico existentes preservados. |

### 4.3 Decisão R6.1-A [APR]

| Código | Decisão [APR] |
|---|---|
| R6.1-A | Entregas legadas `PENDENTE` sem prova confiável de não envio ficam bloqueadas **independentemente do contador de tentativas**. Zero tentativas não comprova ausência de envio no processamento antigo. Inventariar e classificar antes de gerar pendências em massa. Bloqueio obrigatório no serviço/backend. Liberação somente mediante evidência segura ou reconciliação autorizada por Fichas, respeitando auditoria, incerteza, validade e J9-A. Substitui qualquer afirmação anterior de elegibilidade automática do legado `PENDENTE` com zero tentativas. |

### 4.4 Decisões D1–D4 [APR]

| Código | Decisão [APR] |
|---|---|
| D1-A | B1 limitado ao schema essencial de entregas, tentativas, autorizações individuais, pendências e evidências. Emergências, alertas técnicos agrupados e retomadas em lote ficam para B3. Compatibilidade com legado e rollback fail-closed obrigatórios. O B1 não modifica o comportamento de workers, services ou adapters. |
| D2-A | Toda entrega legada bloqueada exige autorização explícita e auditada de Fichas, **mesmo quando existe prova conclusiva de não envio**. Suporte investiga e registra evidências, mas não autoriza liberação. A oportunidade é revalidada antes de qualquer processamento. J9-A preservado: uma chamada externa por autorização. |
| D3-A | Registros críticos de tentativas, autorizações, evidências e auditoria são protegidos no Django ORM **e no PostgreSQL**. Preveem-se triggers que impeçam alterações e exclusões indevidas, permitindo apenas transições legítimas (como a finalização de tentativa aberta). Exigem testes específicos e compatibilidade com o legado. Não se presume inviolabilidade contra administradores privilegiados. |
| D4-A | Prova confiável exige evidência positiva e verificável de que a chamada externa **não começou**, **ou** confirmação inequívoca de **não aceitação** pelo provedor. Ausência de sucesso, logs incompletos e contador zero não constituem prova. Sem evidência conclusiva, mantém-se o bloqueio e encaminha-se à reconciliação por Fichas. Diferenciam-se comprovação de não início e confirmação de não aceitação. |

### 4.5 Decisões O1–O5 [APR]

Estas decisões são **diretrizes**. Elas **não homologam** os detalhes de
models, migrations ou triggers da seção 16, que permanecem [REC] até aprovação
expressa.

| Código | Decisão [APR] |
|---|---|
| O1-A | Auditoria imutável nas operações normais. Tratamento excepcional de dados pessoais somente por procedimento separado, autorizado e auditado. |
| O2-A | Evidências conclusivas com referências verificáveis adequadas à origem, interna ou externa. |
| O3-A | Separar futuramente os privilégios PostgreSQL de runtime e de migrations, após validação. Nenhuma credencial é alterada nesta etapa. |
| O4-A | Usar o conjunto mínimo suficiente de constraints e triggers. Mecanismos adicionais exigem justificativa concreta. |
| O5-A | Seguir as convenções existentes de nomenclatura, evitando renomeações desnecessárias. |

Também [APR]: limite atual de três tentativas preservado; esgotamento ou
falha definitiva comprovada gera `FALHOU` sem reabertura automática; auditoria
append-only de tentativas, evidências e decisões; pendência com encerramento
somente por decisão conclusiva e auditada de Fichas (leitura não encerra);
reabertura formal somente por Fichas, com justificativa; evidência nova pode
alertar mas não reabre nem reenvia; Central com filtros por Encontro, status e
data; uma pendência lógica por ocorrência.

## 5. Contrato de estados e transições

### 5.1 Entrega (`EntregaConviteEncontro`)

Estados: `PENDENTE`, `ENVIANDO` (já existe, hoje sem uso), `ENTREGUE`,
`FALHOU`, e os novos `INCERTA` e `SUSPENSA` [REC].

- `ENTREGUE` mantém o valor para preservar o legado; a semântica passa a ser
  **aceitação técnica** [APR princípio 1]. `entregue_em` passa a significar
  "aceita em" [REC]; nenhuma coluna é renomeada.
- `SUSPENSA` [REC] representa suspensão técnica anterior ao I/O (J3-B). É
  distinta de `INCERTA`: aqui há prova de que nada foi enviado.

| De | Para | Gatilho | Automático |
|---|---|---|---|
| `PENDENTE` | `ENVIANDO` | reivindicação (Tx1) | sim |
| `PENDENTE` | `SUSPENSA` | falha provada anterior ao I/O: configuração, adapter indisponível, destinatário ausente [APR J3-B]; não consome tentativa | sim |
| `PENDENTE` | `FALHOU` | oportunidade expirada [APR J5]; não consome tentativa | sim |
| `ENVIANDO` | `ENTREGUE` | adapter retornou aceitação | sim |
| `ENVIANDO` | `PENDENTE` | não aceitação comprovada, temporária, tentativa automática < 3; backoff | sim |
| `ENVIANDO` | `FALHOU` | não aceitação permanente, ou esgotamento do limite | sim |
| `ENVIANDO` | `INCERTA` | resultado ambíguo, exceção do adapter ou lease vencido | sim |
| `INCERTA` | `ENTREGUE` | Fichas confirma aceitação | não |
| `INCERTA` | `PENDENTE` | Fichas confirma não aceitação, ou autoriza reenvio excepcional com ciência de duplicidade | não |
| `FALHOU` | `PENDENTE` | Fichas autoriza nova chamada; **somente se a oportunidade ainda for válida** [APR P6-A] | não |
| `FALHOU` (oportunidade expirada) | `FALHOU` | permanece; novo envio proibido; Fichas encerra a pendência com justificativa [APR P6-A] | não |
| `INCERTA`, `FALHOU` | `FALHOU` (pendência encerrada) | Fichas encerra sem reenvio [REC] | não |
| `SUSPENSA` | `PENDENTE` | retomada autorizada por Fichas após correção e evidência de Suporte, com revalidação por convite [APR P2-A] (ver 11.3) | não |

Regras:

- [APR J6-A] Resultado tardio de uma chamada cujo lease já virou `INCERTA`
  grava evidência e atualiza `ultima_evidencia_em` da pendência; não muda o
  estado da entrega nem encerra a pendência.
- [APR J9-A] A autorização de Fichas concede **exatamente uma** nova chamada.
  Se essa chamada falhar (temporária ou ambígua), a entrega vai para `FALHOU`
  ou `INCERTA` com **nova pendência** (nova ocorrência), sem retry automático
  nem backoff.
- [REC] Mecânica de contagem (substitui a proposta anterior de um contador
  `chamadas_autorizadas`): `tentativas` segue como total de chamadas externas.
  Cada concessão de Fichas é uma linha de autorização individual
  (seção 16), consumida por **no máximo uma** tentativa, garantido por chave
  única no banco. A tentativa originada de autorização tem `origem='autorizada'`
  e nunca agenda retry automático nem backoff. A elegibilidade de retry
  automático conta somente tentativas de origem automática, derivadas das
  linhas de tentativa, sem contador redundante.
- Tentativas que não chegaram ao I/O (`SUSPENSA`, expiração) **não** incrementam
  `tentativas` [APR J3-B, J5].

### 5.2 Outbox

[REC] Estados `PENDENTE` e `CONCLUIDA` não mudam. O reconciliador deve
republicar apenas outboxes com entrega `PENDENTE` elegível ou `ENVIANDO` com
lease vencido; `INCERTA`, `SUSPENSA` e `FALHOU` aguardando decisão não geram
republicação em loop.

## 6. Tentativas, evidências, pendências e auditoria [REC, salvo indicação]

Todas as estruturas abaixo são **propostas** [REC]; apenas os requisitos
funcionais (histórico append-only, pendência única por ocorrência, etc.) são
[APR]. A especificação final do B1, que prevalece sobre os detalhes desta
seção, está na seção 16.

- **`TentativaEntregaConvite`** (nova): uma linha por chamada externa.
  Campos: `entrega` (FK PROTECT), `numero`, `origem` (`automatica` ou
  `autorizada`), `chave_idempotencia`, `provider`, `iniciada_em`,
  `lease_expira_em`, `finalizada_em`, `desfecho` (`iniciada`, `aceita`,
  `nao_aceita`, `ambigua`, `interrompida`), `categoria_falha`, `codigo_erro`,
  `id_externo` (opcional), `evidencia_tecnica` (curta, minimizada).
  Constraints: UNIQUE `(entrega, numero)`; UNIQUE parcial `(entrega)` onde
  `desfecho='iniciada'` (no máximo uma tentativa aberta por entrega, no
  banco). A linha muda apenas uma vez, de `iniciada` para um desfecho final;
  imutabilidade aplicada em `save` e no queryset, no padrão de
  `EventoAuditoriaEncontroQuerySet`.
- **`PendenciaEntregaConvite`** (nova): `encontro` (denormalizado para
  filtro), `entrega`, `tipo` (`incerta`, `falhou`, `legado_sem_prova`), `status` (`aberta`,
  `encerrada`), `aberta_em`, `ultima_evidencia_em`, `encerrada_em`,
  `encerrada_por`, `decisao`, `reaberturas`, `versao`. UNIQUE parcial
  `(entrega)` onde `status='aberta'`. Encerrada exige `encerrada_em`,
  `encerrada_por` e `decisao`; aberta exige os três nulos. Índices por
  `(encontro, status, aberta_em)` e `(tipo, status)`. A própria criação da
  pendência, na mesma transação da transição da entrega, é o alerta interno:
  não depende de `on_commit` e não duplica por repetição.
- **`EvidenciaEntregaConvite`** (nova, append-only): `pendencia`, `autor`
  (nulo para o sistema), `tipo` (`suporte_nota`,
  `provedor_confirmou_aceitacao`, `provedor_confirmou_nao_aceitacao`,
  `provedor_desconhecido`, `resultado_tardio_adapter`), `texto` curto
  minimizado, `origem` e `referencia` (ver 16.4), `criado_em`. Sem token, credencial ou PII
  desnecessária.
- **Auditoria de decisões e transições:** reutilizar `EventoAuditoriaEncontro`
  (imutável, com ator, valores anterior e novo e justificativa). Registrar
  ator, instante, motivo, estados anterior e posterior, IDs de tentativa e
  pendência e, quando aplicável, a ciência expressa de duplicidade [APR] e se
  o adapter declarava idempotência. A evidência técnica bruta fica na
  tentativa, não na auditoria, porque a auditoria tem leitores mais amplos.
- **Alerta técnico agrupado** [APR J3-B, P1-A]: falhas anteriores ao I/O não
  geram uma pendência por entrega. São agrupadas por **causa, provedor e
  ambiente**. Suporte recebe os detalhes e a contagem dos convites afetados;
  Fichas recebe visão resumida na Central. Sem e-mail automático e sem
  retomada automática.
  [REC] Mecânica: uma ocorrência técnica (model próprio, a definir) ligada às
  entregas afetadas, com contagem derivada. O projeto não possui hoje
  identificador de ambiente nas configurações; seria necessária uma variável
  nova, com nome a definir (seção 11.1).
- **Legado sem prova** [APR P3-A]: ver seção 10. As pendências de legado
  usam o tipo lógico `legado_sem_prova` [REC], sem novo status de entrega.
- **Pendência e estado técnico são ortogonais** [REC]. Encerrar a pendência
  nunca é operação independente: é sempre efeito de uma decisão de
  reconciliação, na mesma transação e com a mesma auditoria. Eventos técnicos
  automáticos (evidência tardia) nunca encerram. Reabertura formal incrementa
  `reaberturas` e não altera sozinha o estado técnico. Uma nova ocorrência após
  uma chamada autorizada cria nova pendência.
- **Central de Pendências** [APR funcional]: filtros por Encontro, status e
  data; histórico acessível após encerramento; leitura não encerra.
  [REC] Fichas vê resumo legível; Suporte vê também código, categoria, ID
  externo e evidência técnica; serializers separados por perfil, com
  allowlist.

## 7. Fronteiras transacionais, lease, fencing e duplicidade [REC]

**Invariante I1.** Existe I/O externo para uma entrega somente se existir uma
`TentativaEntregaConvite` com `desfecho='iniciada'` **commitada antes** da
chamada ao adapter. Para isso:

- a chamada ao adapter ocorre somente após o commit da Tx1, fora de qualquer
  `atomic`; `on_commit` não serve para isso;
- existe um único ponto de chamada ao adapter no código;
- não há retry interno no adapter.

Consequência: entrega `PENDENTE` sem tentativa aberta, no protocolo novo, é
prova durável de que nenhuma chamada começou. Limites declarados: entregas
legadas com `tentativas > 0` não têm linhas de tentativa (ver seção 10);
workers antigos fora do controle de implantação podem chamar o adapter sem
tentativa (ver seção 11); o adapter não pode ter I/O interno anterior à
chamada.

**Fluxo.**

1. **Tx1 (curta):** trava outbox, entregas e, quando necessário, pendência, na
   ordem global **outbox → entrega → pendência**. Recupera tentativas com
   lease vencido (tentativa `interrompida`, entrega `INCERTA`, pendência e
   auditoria na mesma transação). Aplica as guardas anteriores ao I/O
   (expiração, configuração, destinatário). Cria a tentativa `iniciada` com
   lease, move a entrega para `ENVIANDO`, incrementa `tentativas`. Commit.
2. **I/O:** fora de transação e sem locks. Descriptografa o token, monta o
   payload com `chave_idempotencia` e chama o adapter. Qualquer exceção,
   exceto falha de configuração comprovadamente anterior à chamada, é tratada
   como resultado ambíguo.
3. **Tx2 (curta):** trava a entrega e confere que a tentativa continua
   `iniciada` e que o `numero` coincide. Se sim, aplica o desfecho. Caso
   contrário (recuperação já agiu), grava somente evidência tardia [APR J6-A].

**Fencing.** Recuperação e Tx2 serializam-se pelo lock da entrega: quem chega
primeiro vence; a outra observa o estado e segue o caminho de evidência. Não
há fencing capaz de impedir um envio externo já em andamento, apenas de
impedir gravação de estado divergente. Decisões de Fichas exigem
`estado_esperado` e `versao` da pendência; divergência retorna conflito sem
aplicar. UNIQUE parciais de tentativa aberta e de pendência aberta são defesa
no banco.

**Falhas entre persistência e chamada.** Queda entre o commit da Tx1 e a
chamada resulta em `INCERTA` ao vencer o lease: não é possível provar que a
chamada não começou. Falha da Tx2, inclusive commit falho, também resulta em
`INCERTA` e nunca em reenvio. O custo é maior volume de `INCERTA` quando a
infraestrutura falha; é consequência assumida de [APR princípio 3].

**Lease** [APR J7-C, P4-A]: configurável, em configuração independente da
flag. 120 segundos é apenas referência provisória. A validação na homologação
(C5.4) é obrigatória antes da ativação, e falha na validação bloqueia a
ativação. [REC] O lease deve ser maior que o timeout máximo do adapter com
margem; validar a relação na inicialização.

**Recuperação** [REC]: executada na Tx1 e em task periódica do Beat, com
`skip_locked` para não bloquear atrás de worker lento.

**Celery** [FATO/REC]: `acks_late`, `reject_on_worker_lost` e prefetch 1
permanecem. O estado do banco é a fonte de verdade, e a task é segura a
redelivery. Tasks continuam carregando apenas IDs técnicos.

## 8. Adapters: idempotência e limitações

- [REC] `ResultadoEntregaConvite` passa a distinguir `ACEITA`, `NAO_ACEITA`
  (comprovada) e `AMBIGUA`, com `id_externo` opcional e `evidencia` mínima.
- [REC] `PayloadEntregaConvite` recebe `chave_idempotencia`, estável por
  entrega lógica e reutilizada em todas as tentativas, inclusive a autorizada.
  Reutilizá-la só protege contra duplicidade se o provedor a honrar.
- [REC] Cada adapter declara capacidades (idempotência nativa, ID externo,
  consulta de status, callback). Nada é presumido.
- **SMTP** [REC]: provado não enviado apenas em configuração inválida, payload
  inválido, falha ao abrir conexão, autenticação recusada e destinatário ou
  remetente recusado antes do DATA. Todo o restante, inclusive timeout e
  desconexão, é `AMBIGUA`. Exige abrir a conexão explicitamente. Sem
  idempotência, ID externo ou consulta. `Message-ID` derivado da chave serve
  apenas de correlação em logs do MTA, não de deduplicação.
- **WhatsApp mock** [APR J8-A mantém o mock] [REC] timeout passa a `AMBIGUA`;
  modo opcional para ID externo. Não comprova capacidade de provedor real.
  Testes que hoje esperam timeout temporário precisarão ser atualizados.
- **Provedor real:** fora do C5.3. Antes de qualquer implementação é
  necessário conhecer idempotência e janela de validade, ID de mensagem,
  consulta de status, webhook com assinatura, limites de taxa e semântica de
  timeout.

## 9. Segurança, permissões e retenção de segredo

### 9.1 Condições normais

**Autorização** [APR J1]: em condições normais, reconciliação e reenvio são
exclusivos de Fichas. A única exceção é a emergência formal da seção 9.2.

- [REC] Função nova de permissão: usuário ativo, Encontro não cancelado nem
  finalizado, perfil Fichas. **Sem** `is_superuser`, **sem**
  `FULL_ADMIN_ROLES` e **sem** reutilizar `FICHAS_MANAGEMENT_ROLES`
  (`backend/core/roles.py`), que inclui Suporte e Diretoria. O padrão de
  `pode_aprovar_encaminhamento_encontrista` inclui superusuário e **não** deve
  ser copiado.
- [REC] Validar no serviço (não só na view), recebendo o ator.
- [REC] `ModelAdmin` dos novos models somente leitura, porque superusuário do
  Django pode editar linhas diretamente. Isso não cria caminho de emergência:
  o único caminho excepcional aprovado é o da seção 9.2.
- Suporte: consulta técnica e registro de evidência, sem decidir [APR].

### 9.2 Emergência por indisponibilidade de Fichas [APR P7]

**Condições de indisponibilidade [APR P7.1].** Exigidas **simultaneamente**:
nenhum responsável habilitado de Fichas disponível dentro do prazo necessário;
urgência operacional justificada; evidências documentadas; prazo de espera
configurável. Demora normal, discordância ou recusa de Fichas **não**
justificam emergência.

**Ativação [APR P7.2, R3-A].** Aprovação cruzada entre Suporte e Diretoria:
Suporte solicita e Diretoria aprova, ou o inverso. Solicitante e aprovador são
distintos; autoaprovação é proibida. Justificativa, evidências, escopo
delimitado, expiração e auditoria são obrigatórios. O **solicitante pode
operar** depois da aprovação independente. A autorização fica **vinculada a
operador, escopo, ocorrências e prazo**.

**Prazo de espera [APR R3.1-A].** Configurável **por nível de urgência**. A
solicitação exige tentativas de contato documentadas e critérios objetivos.
Os valores numéricos **ainda não estão homologados** e este documento não os
fixa.

**Poderes excepcionais [APR P7.3].** Um operador emergencial autorizado pode
decidir casos com **evidência conclusiva**:

- confirmar aceite do provedor;
- autorizar **uma única** chamada quando houver prova de não aceitação;
- manter a suspensão;
- concluir a pendência quando cabível.

Limites [APR]: o **reenvio excepcional de `INCERTA` sem confirmação do
provedor continua exclusivo de Fichas, inclusive durante a emergência**. J9-A
permanece: uma chamada externa por autorização. Nenhum bypass de validade da
oportunidade, de segurança ou de auditoria.

**`INCERTA` sem evidência conclusiva [APR R5-A].** O operador emergencial
**não pode encerrar** pendência `INCERTA` com resultado desconhecido. Pode
investigar e registrar evidências. A decisão institucional permanece reservada
a Fichas, assim como o reenvio excepcional sem confirmação. Portanto, em
emergência, "concluir a pendência quando cabível" **não** alcança `INCERTA`
desconhecida.

**Colaboração e retorno de Fichas [APR R4-B].**

- O retorno de Fichas **não revoga automaticamente** a autorização
  emergencial.
- Fichas, Suporte e Diretoria podem atuar simultaneamente, cada um dentro da
  sua competência.
- A autorização permanece válida **somente até o prazo originalmente
  concedido**, dentro do escopo; não é prorrogada pelo uso nem pelo retorno de
  Fichas.
- Decisões concorrentes incompatíveis sobre a mesma ocorrência são
  impedidas.
- A exceção não se transforma em acesso permanente.

**Relação entre J1, P7 e R4.** J1 estabelece Fichas como decisora em condições
normais. P7 cria uma exceção estreita, aprovada de forma cruzada, com poderes
limitados e prazo. R4-B regula a convivência: o retorno de Fichas não encerra a
exceção, mas Fichas mantém a competência plena (inclusive as decisões
reservadas a ela por R5-A e P7.3) e as decisões incompatíveis são serializadas.
A exceção nunca amplia a competência além de P7.3 nem sobrevive ao prazo
concedido.

**Mecânica [REC], não aprovada:**

- Registro de autorização emergencial (model próprio, a definir) com
  solicitante, aprovador, operador (que pode ser o solicitante, R3-A), escopo
  (Encontro e ocorrências listadas), justificativa, evidências, tentativas de
  contato, nível de urgência, `criada_em`, `expira_em`. Constraints e
  validação de serviço garantem solicitante ≠ aprovador e que um seja Suporte
  e o outro Diretoria. Superusuário não aprova nem opera.
- O prazo de espera por nível de urgência vem de configuração (nomes e
  valores a definir). O sistema pode verificar o tempo decorrido desde a
  abertura da pendência; as demais condições de P7.1 e os critérios objetivos
  são declarados com evidência e auditados, pois o sistema não os comprova
  sozinho.
- Cada ação emergencial grava, em `EventoAuditoriaEncontro`, a marca de
  emergência e o ID da autorização, além dos campos já exigidos.
- Fichas é sinalizada na Central quando uma emergência é aberta ou usada.
- O serviço rejeita, mesmo em emergência, o reenvio de `INCERTA` sem evidência
  de não aceitação confirmada pelo provedor, o encerramento de `INCERTA`
  desconhecida, e qualquer decisão fora do escopo, das ocorrências listadas ou
  após a expiração.
- Impedimento de decisões concorrentes: reaproveitar a ordem global de locks
  e o `estado_esperado` e `versao` da pendência (seção 7), de modo que uma
  decisão de Fichas e uma emergencial sobre a mesma ocorrência se serializem e
  a segunda observe o estado e seja recusada se incompatível.
- A interpretação de "concluir pendência quando cabível" fica, em emergência,
  restrita a pendências cuja conclusão não depende de resolver risco de
  duplicidade (aceite confirmado, `FALHOU` com prova, oportunidade expirada).

### 9.3 Operações de reconciliação e guardas

**Operações de reconciliação** [REC]: registrar evidência; confirmar aceitação
(exige evidência de aceitação); autorizar nova chamada após não aceitação
confirmada (exige evidência correspondente para `INCERTA`; para `FALHOU` basta
justificativa); reenvio excepcional (somente `INCERTA`, com ciência de
duplicidade e justificativa); manter suspensa (sem encerrar); encerrar sem
reenvio; reabrir pendência.

**Guardas para decisão que leve a `PENDENTE`** [REC], relidas sob lock:
oportunidade `PENDENTE` e não expirada; campanha não bloqueada; token
disponível e decifrável. Se falhar, `autorizar` e `reenvio excepcional` são
recusados com erro tipado; `confirmar aceitação` e `encerrar sem reenvio`
continuam permitidos. A reconciliação apenas **lê** oportunidade e campanha; não
cria nem altera oportunidade, rodada, convite ou token (D23-A, D24-A e D25-A
preservados).

**Retenção de segredo** [APR J4 como princípio] [REC mecânica]: a outbox só
conclui e destrói o segredo quando não há necessidade legítima, isto é,
quando: todas as entregas estão `ENTREGUE`; ou as pendências abertas foram
encerradas; ou a oportunidade deixou de ser válida (expirada, invalidada,
consumida, suspensa). Enquanto houver entrega `PENDENTE`, `ENVIANDO`,
`INCERTA`, `SUSPENSA` ou `FALHOU` com pendência aberta e a oportunidade
válida, o token cifrado permanece. A destruição por expiração é feita pelo
reconciliador. Esta mecânica não altera o CHECK `out_conv_segredo_lifecycle`
(segredo nulo apenas em `concluida`). O CHECK de status da entrega precisa ser
ampliado para `incerta` e `suspensa`.

**Dados e logs:** sem token, link, credencial, e-mail ou telefone em logs,
auditoria ou argumentos Celery.

## 10. Transição do legado [APR política]

| Estado legado | Tratamento |
|---|---|
| `PENDENTE` sem prova confiável de não envio, **com qualquer contador de tentativas, inclusive zero** | `LEGADO_SEM_PROVA`: bloqueada; sem reenvio automático; liberação somente por evidência segura ou reconciliação autorizada por Fichas [APR P3-A, R6.1-A]. |
| `ENTREGUE` ou `FALHOU` | Preservar estado e histórico. |
| `ENVIANDO` | Não deveria existir (nunca é gravado); se o inventário encontrar, tratar como resultado incerto. |

- Não inferir aceitação externa a partir de ausência de registro.
- Linhas de tentativa não são retroativamente criadas; nenhum backfill.
- [APR P3-A] `PENDENTE` legada com tentativas anteriores e sem prova
  confiável tem o reenvio automático **bloqueado** e recebe a identificação
  lógica `LEGADO_SEM_PROVA`, **sem novo status no banco**. A reconciliação é de
  Fichas; Suporte apenas investiga. O inventário prévio precede qualquer
  geração de pendências em massa.
- [APR R6-A] O bloqueio é **obrigatório no serviço/backend**: não pode
  depender apenas de fila, task, reconciliador ou migration. Preservam-se
  registros e histórico existentes. Sem reenvio automático; reconciliação e
  eventual autorização expressa por Fichas.
- [APR R6.1-A] Entregas legadas `PENDENTE` sem prova confiável de não envio
  ficam bloqueadas **independentemente do contador de tentativas**. Zero
  tentativas **não comprova** ausência de envio no processamento antigo, porque
  o fluxo antigo só gravava o resultado em commit bem-sucedido e uma
  duplicidade ou envio não registrado deixava `tentativas = 0`. Esta regra
  **substitui** qualquer afirmação anterior de elegibilidade automática do
  legado `PENDENTE` com zero tentativas. Inventariar e classificar **antes** de
  gerar pendências em massa. O bloqueio é obrigatório no serviço/backend. A
  liberação ocorre somente por evidência segura ou reconciliação autorizada
  por Fichas, respeitando auditoria, incerteza, validade da oportunidade e
  J9-A (uma chamada por autorização).
- [REC] Mecânica sem novo status, **fail-closed por padrão**: a entrega
  permanece `PENDENTE` no banco e é identificada como legado por um marcador de
  protocolo **nulo** (seção 16). Somente entregas criadas pelo código novo
  recebem o marcador `v2`. Qualquer linha sem marcador, inclusive criada por
  código antigo depois da migration, é tratada como legado e bloqueada. O
  predicado é avaliado **dentro da função de serviço que reivindica a entrega e
  cria a tentativa (Tx1)**, único ponto de entrada para a chamada externa, sob
  o lock da entrega. Qualquer chamador (task, reconciliador, comando de gestão
  ou teste) passa por essa guarda e recebe recusa tipada. Filtros na task e no
  reconciliador servem só para evitar trabalho inútil, não como proteção. A
  guarda vale desde a ativação, sem data migration e sem alterar linhas
  existentes. A flag desligada (fail-closed) é independente desta guarda.
- [REC] Liberação: toda liberação gera uma **autorização individual de
  reenvio** (seção 16), consumida por exatamente uma chamada. Uma liberação por
  "evidência segura" também exige essa autorização (ver pendência D2 na seção
  15). Após a chamada, a tentativa existe e a entrega deixa de ser tratada como
  legado sem prova. As pendências `legado_sem_prova` são geradas por operação
  explícita e controlada, **depois** do inventário e da classificação, em lotes
  verificáveis, não por migration.
- **Inventário (pré-requisito operacional futuro; não realizado nesta
  etapa):** contagem por status e por `tentativas`; existência de `enviando`;
  outboxes `PENDENTE` com segredo; oportunidades expiradas com entrega
  `PENDENTE`. Requer acesso ao PostgreSQL com aprovação pontual conforme
  `AGENTS.md`.
- **Workers:** workers antigos e novos não podem processar a mesma fila
  simultaneamente (seção 11).

## 11. Ativação, suspensão e rollback *fail-closed* [APR J10-A]

### 11.1 Feature flag

[APR P5-A] Feature flag própria, desativada por padrão, fila Celery dedicada
e configuração de lease independente. Nomes definitivos ficam sujeitos à
análise das convenções do repositório.

[REC] Convenções observadas em `backend/setup/settings.py`: variáveis com
prefixo `SIA_`, leitura por `env_bool`, `env_int` e `env_float`; configurações
de convites usam `SIA_INVITATION_*`; o arquivo não define filas nem
`CELERY_TASK_ROUTES` hoje. Sugestões, **não aprovadas**:
`SIA_INVITATION_DELIVERY_ENABLED` (flag, `env_bool`, padrão falso),
`SIA_INVITATION_DELIVERY_LEASE_SECONDS`, uma fila dedicada roteada por
`CELERY_TASK_ROUTES`, `SIA_INVITATION_EMERGENCY_WAIT_MINUTES` e um
identificador de ambiente para o agrupamento de alertas. A flag, o lease e a
fila são configurados de forma independente.

O estado *desligado* é **fail-closed**:
o worker não realiza nenhuma chamada externa e não reverte para o
processamento antigo. O código antigo de envio é **removido** na implementação,
não mantido como alternativa.

### 11.2 Isolamento de workers antigos e novos [REC]

- A task nova usa **nome novo e fila dedicada**. O nome antigo
  (`core.processar_outbox_convite`) passa a ser um *shim* inerte que não chama
  adapter; mensagens antigas residuais no broker ficam inofensivas e o Beat
  republica pelo nome novo.
- Ordem de implantação: parar worker e Beat; confirmar que não restam
  processos consumindo (`celery inspect`); implantar; executar o inventário;
  aplicar a transição do legado; só então ativar a flag e iniciar worker e
  Beat. Critério de bloqueio: qualquer worker antigo ativo.

### 11.3 Recuperação de `SUSPENSA`

[APR P2-A] Suporte corrige a falha e registra evidências. Fichas autoriza a
retomada, individual ou em lote. Cada convite é revalidado antes do
processamento. Não se consome tentativa quando comprovado que nenhuma chamada
externa começou.

[REC] Mecânica: a autorização de lote referencia a ocorrência técnica (seção 6) e
gera uma decisão auditada por entrega. A revalidação por convite repete as
guardas da seção 9.3 (oportunidade válida e não expirada, campanha, segredo,
configuração, destinatário); se alguma falhar, a entrega segue o caminho
correspondente (por exemplo, `FALHOU` por expiração, J5) sem tentativa. Como há
prova de que nada foi enviado, não é exigida ciência de duplicidade, mas são
registrados ator, instante, causa e evidência. A retomada nunca é automática.

### 11.4 Suspensão e rollback

- Suspensão: desligar a flag. Nenhuma chamada externa ocorre; as entregas
  permanecem em seus estados; a outbox e o segredo cifrado permanecem.
- Rollback: **não** há retorno ao worker antigo. Reverter implica desligar a
  flag e investigar. Se for necessário reverter o código, só após drenar
  workers e confirmar, via inventário, que não há `ENVIANDO`, `INCERTA` ou
  `SUSPENSA` que o código antigo não compreenderia (o worker antigo ignora
  esses estados e deixa a outbox pendente, sem efeito colateral, mas isso não
  autoriza o retorno automático).
- Reversão de migration (apenas adições) descarta as linhas novas; só deve ser
  considerada com a flag desligada e após exportar o que Fichas precisar
  preservar. A decisão cabe ao responsável.

### 11.5 Critérios de bloqueio da ativação

Inventário não feito ou com `ENVIANDO` não explicado; worker antigo ativo;
migration `0051` não aplicada e verificada; chave Fernet ausente; lease
não validado na homologação ou inconsistente com o timeout do adapter
[APR P4-A]; inventário não concluído antes de gerar pendências de legado
[APR P3-A]; homologação C5.4 sem os cenários
críticos aprovados; Central indisponível para Fichas (alertas sem destino).

## 12. Plano incremental [REC]

**Pré-requisito comum:** a migration `0050_preselecaoencontrista` pertence a
outra frente (Pré-seleção) e foi incluída no C0 (`426b177`); não deve ser
alterada nem presumida aplicada no banco. A migration nova (provisoriamente
`0051`) depende dela e só deve ser criada depois que `0050` esteja estável, para
não renumerar. Antes de propor a migration, `makemigrations --check --dry-run`.

**C5.3 — implementação (independente de provedor real). Cada bloco exige
autorização expressa.**

- **B1 — modelo.** Especificação final proposta na seção 16.
  `backend/core/models.py`, migrations `0051` (schema) e `0052` (triggers
  PostgreSQL) e testes de modelo, constraints e integridade. Entrega: status
  `incerta` e `suspensa`, marcador de protocolo, tabelas de tentativa,
  autorização individual de reenvio, pendência e evidência, e triggers
  [APR D3-A]. **Emergências, alertas técnicos agrupados e retomadas em lote
  ficam fora do B1** [APR D1-A] e entram em B3 por migration aditiva própria.
  O B1 não modifica workers, services nem adapters [APR D1-A]. Aceite: seções
  16.7 e 16.12. Rollback: seção 16.8.
- **B2 — worker e adapters.** `services/entregas_convites.py`,
  `notifications/{contracts,smtp,whatsapp_mock,factory}.py`, `tasks.py`,
  configuração de lease e flag. Entrega: Tx1, I/O fora de `atomic`, Tx2, lease,
  fencing, reclassificação de resultados, suspensão anterior ao I/O, não envio
  de convite expirado, nome de task novo e *shim*. Aceite: I1 demonstrada em
  teste; cenários da seção 13 verdes. Rollback: flag desligada (fail-closed).
- **B3 — reconciliação.** Serviço de reconciliação, função de permissão,
  evidências, auditoria, retenção do segredo, `ModelAdmin` somente leitura,
  retomada de `SUSPENSA` em lote com revalidação, bloqueio de
  `LEGADO_SEM_PROVA` e emergência P7 (ativação cruzada, escopo, expiração,
  limites de poder). Aceite: Fichas como único decisor em condições normais, sem
  bypass; emergência restrita a P7.3; ordem de locks; `versao`. Rollback: sem
  exposição enquanto B4 não existir.
- **B4 — Central (API).** Serializers por perfil, filtros, ações. Somente com
  autorização separada. A API de aprovação de encaminhamentos de Fichas
  **permanece fora**.

**C5.4 — homologação.** Cenários da seção 13 em PostgreSQL real e adapter
simulado; janela de deploy sem workers antigos; inventário e transição do
legado em ambiente de homologação; calibragem do lease. UI da Central em bloco
separado, se autorizada.

**Depende de provedor real (fora do C5.3):** idempotência nativa, ID externo
real, consulta de status, webhook e ajuste final do lease.

**Pontos para revisão independente do QA:** I1; fencing e ordem de locks;
função de permissão sem bypass; guardas de expiração e segredo; mecânica de
autorização individual de reenvio e `origem` da tentativa (J9-A); bloqueio do
legado no serviço (R6.1-A); diff de
`campanhas_convites.py` do WIP.

## 13. Matriz de testes e falhas [REC]

Testes padrão rodam em SQLite em memória (`setup/test_settings.py`). Os marcados
PG exigem PostgreSQL real e são executados manualmente, conforme `AGENTS.md`.

| Cenário | Tipo | Esperado |
|---|---|---|
| Rollback da Tx2 após aceite simulado | PG | tentativa `iniciada`; lease vence; `INCERTA`; nenhum reenvio |
| Timeout ambíguo | simulado | `INCERTA`; pendência única; sem retry |
| Exceção do adapter | simulado | `INCERTA`; nunca propaga nem faz rollback do registro |
| Worker interrompido entre Tx1 e chamada | simulado | `INCERTA` ao vencer o lease |
| Falha anterior à Tx1 | simulado | segue `PENDENTE` e retoma sozinha |
| I1: tentativa visível a uma segunda conexão durante a chamada | PG | tentativa `iniciada` commitada antes do adapter |
| Dois workers na mesma entrega | PG | uma chamada |
| Tentativa aberta duplicada | PG | UNIQUE parcial recusa |
| Falha provada anterior ao I/O | simulado | `SUSPENSA`; não consome tentativa; alerta técnico agrupado |
| Convite expirado | simulado | `FALHOU` sem chamada; sem tentativa; pendência a Fichas |
| Limite de três tentativas automáticas | simulado | `FALHOU` sem reabertura automática |
| Autorização de Fichas | simulado | exatamente uma chamada; falha dela não faz retry; nova pendência |
| Resultado tardio | simulado | evidência; `INCERTA` intacta; sem reenvio |
| Decisões concorrentes de Fichas | PG | uma aplica; a outra recebe conflito |
| Ordem de locks outbox → entrega → pendência | PG | sem deadlock |
| Autorização em condições normais | simulado | Suporte, Diretoria e superusuário não decidem; Fichas decide |
| Emergência: autorização inválida | simulado | recusa autoaprovação, mesmo papel (Suporte e Suporte, ou Diretoria e Diretoria), expirada, fora do escopo ou das ocorrências listadas, sem contato documentado ou sem prazo de espera por urgência cumprido |
| Emergência: solicitante opera | simulado | solicitante opera somente após aprovação independente; autorização vinculada a operador, escopo, ocorrências e prazo |
| Emergência: poderes | simulado | confirma aceite, autoriza uma chamada com prova de não aceitação, mantém suspensão; **recusa** reenvio de `INCERTA` sem confirmação do provedor |
| Emergência: `INCERTA` desconhecida (R5-A) | simulado | operador registra evidência; encerramento e reenvio recusados |
| Retorno de Fichas durante emergência (R4-B) | PG | autorização não é revogada; vale só até o prazo original; decisões de Fichas e emergencial concorrentes se serializam e a incompatível é recusada |
| Emergência: auditoria | simulado | marca de emergência e ID da autorização em cada ação; Fichas sinalizada |
| Retomada de `SUSPENSA` em lote | simulado | revalida cada convite; expirado vira `FALHOU` sem tentativa; nada é retomado automaticamente |
| Alerta técnico agrupado | simulado | uma ocorrência por causa, provedor e ambiente; contagem correta; sem e-mail |
| `FALHOU` com oportunidade expirada | simulado | permanece `FALHOU`; autorização de novo envio recusada; Fichas encerra com justificativa |
| `LEGADO_SEM_PROVA`: guarda no serviço (R6-A) | simulado | chamada direta ao serviço, sem passar por task, fila ou reconciliador, é recusada; nenhuma chamada externa; registros intactos |
| `LEGADO_SEM_PROVA`: autorização de Fichas | simulado | libera exatamente uma chamada; depois disso deixa de ser legado sem prova |
| Validação do lease | simulado | lease incompatível com o timeout bloqueia a ativação |
| Auditoria | simulado | ator, instante, motivo, estados, ciência de duplicidade; imutável |
| Dedupe de pendência | PG | uma linha aberta |
| Guardas (oportunidade, campanha, segredo) | simulado | recusa tipada |
| Retenção de segredo | simulado | destruído só quando não há necessidade legítima |
| Reconciliador não republica outbox só com `INCERTA`, `SUSPENSA` ou `FALHOU` | simulado | não republica |
| Legado: `PENDENTE` com zero tentativas e com tentativas | simulado | **ambas** bloqueadas no serviço (R6.1-A); `ENTREGUE` e `FALHOU` preservadas, conforme seção 10 |
| Linha criada por código antigo após a migration (marcador nulo) | simulado | tratada como legado e bloqueada |
| Flag desligada | simulado | nenhuma chamada externa; sem retorno ao fluxo antigo |

Os testes de concorrência e criação existentes devem ser preservados; os que
tratam timeout como temporário precisam ser atualizados.

## 14. Compatibilidade

- Campanhas, rodadas, oportunidades, convites, confirmação, recusa, reabertura e
  reposição: nenhuma alteração de contrato. A reconciliação só lê esses
  objetos [FATO: nada fora do serviço de entrega lê o status de entrega].
- `criar_outbox_entrega_convite` mantém assinatura e canais (`email`,
  `whatsapp`). O WIP de `campanhas_convites.py` altera a origem dos canais
  (`_canais_da_pessoa`) e não a chamada da outbox; o diff completo não foi
  revisado nesta etapa. O WIP de `models.py` (bloco inserido por volta da linha
  1155) não toca entrega nem outbox.
- Constraints existentes de entrega permanecem, exceto o CHECK de status, que
  precisa aceitar os novos valores.
- Revisão da migration `0050_preselecaoencontrista` (leitura estática): depende
  de `0049`, cria apenas `PreSelecaoEncontrista` e não toca entrega, outbox nem
  oportunidade. Não há sobreposição de schema com o B1. Sua aplicação no banco
  **não é presumida**. Não foi possível confirmar, sem executar
  `makemigrations --check --dry-run`, que o working tree de `models.py` esteja
  sem deriva em relação a `0050`; essa verificação é pré-requisito do B1
  (seção 16.6).
- Celery, Beat, `acks_late` e `visibility_timeout` permanecem; muda o nome da
  task e a fila (seção 11.2).

## 15. Riscos residuais, pendências técnicas e dependências

**P1 a P7 e R3 a R6:** decididos [APR] nas seções 4.1 e 4.2. Restam os pontos
abaixo, **não aprovados ou não homologados**:

- **R1** — nomes definitivos da flag, da fila e das variáveis (P5-A):
  confrontar as sugestões da seção 11.1 com as convenções do repositório.
- **R2** — origem do identificador de ambiente usado no agrupamento de
  alertas (P1-A); hoje não existe em `settings.py`.
- **R3.1** — valores numéricos do prazo de espera por nível de urgência, a
  lista de níveis e os critérios objetivos (R3.1-A). Não homologados; este
  documento não os fixa.
- **R4** — se Fichas ou Diretoria podem **revogar manualmente** uma
  autorização emergencial ativa. R4-B decide apenas que o retorno de Fichas não
  revoga automaticamente; a revogação manual não foi decidida.
- **R6.1** — critérios de **classificação** do inventário do legado e
  procedimento de geração das pendências em lotes verificáveis (R6.1-A,
  seção 10). A identificação técnica do legado (marcador nulo) está na
  seção 16 como [REC].
- **D1 a D4:** decididos [APR] na seção 4.4.
- **O1 a O5:** decididos [APR] como diretrizes na seção 4.5. Restam, **não
  aprovados e fora do B1**:
  - **O1** — o procedimento excepcional (quem autoriza, como se audita, como
    se executa no banco) para dados pessoais em eventos de auditoria ainda não
    está definido. Deve ser definido antes de a primeira solicitação desse tipo
    surgir; não é bloqueador técnico do B1.
  - **O2** — regras de adequação de `referencia` por `origem` (B3 e operação).
  - **O3** — separação futura de privilégios de runtime e migrations: validar e
    planejar em operação; nenhuma credencial é alterada nesta etapa.
  - **O4** — o conjunto mínimo de 16.11 e 16.2 é proposta [REC]; qualquer
    mecanismo acrescido exige justificativa.
  - **O5** — nomes propostos nesta seção seguem as convenções existentes
    (prefixo `ent_conv_`, `out_conv_`, `op_conv_`, sufixo `_idx` com até 30
    caracteres); nomes das funções e triggers PostgreSQL (`sia_conv_*`) não têm
    precedente no repositório e são [REC].
- **R7** — modelagem do lote de retomada (P2-A) e da ocorrência técnica
  agrupada.
- **R8** — referência de lease: 120 s é provisória; valor final só após a
  homologação (P4-A).
- Mecânica de exclusão de decisões concorrentes e do registro de autorização
  emergencial: proposta [REC] nas seções 7 e 9.2, não homologada.

**Riscos residuais:**

- Duplicidade não é eliminada: SMTP não honra idempotência; apenas deixa de ser
  silenciosa. Nenhuma garantia *exactly-once*.
- Volume de `INCERTA` pode ser alto em falhas de infraestrutura.
- Retenção do token cifrado enquanto houver necessidade legítima prolonga a
  exposição cifrada, limitada à validade da oportunidade.
- Workers antigos fora do controle de implantação violam I1.
- Mudança de semântica de timeout no mock exige atualizar testes existentes.
- Dependência de ordem com a migration `0050` (outra frente; à época não rastreada, hoje no C0 `426b177`).
- Registro no admin e nome exato da função de bloqueio de campanha não foram
  verificados.

**Não homologado:** todo o desenho acima. Lease, invariante I1, ordem de locks e
comportamento sob PostgreSQL real dependem do C5.4.

## 16. C5.3-B1 — Especificação técnica final do modelo [REC]

Esta seção é **proposta [REC]**, salvo onde indicado [APR]. Nenhum item foi
implementado. As decisões [APR] que ela concretiza (R6.1-A, D1-A a D4-A) são
citadas por código.
Nomes de campos, constraints e índices são propostos e podem ser ajustados na
implementação sem reabrir as decisões.

### 16.1 `EntregaConviteEncontro` — alterações

- `status`: acrescentar `incerta` e `suspensa`. O Django 5.2.16 instalado possui
  `AlterConstraint`, mas sua operação não executa DDL (`database_forwards` é
  vazio; só altera o estado do projeto). Logo, para mudar a condição do CHECK
  é necessário `RemoveConstraint` seguido de `AddConstraint`, mantendo o
  **mesmo nome** `ent_conv_status_valido` [APR O5-A: sem renomear].
- `protocolo`: `CharField(max_length=10, null=True, blank=True,
  editable=False)`, com o único valor `v2`. **`NULL` significa legado**
  (fail-closed): linhas existentes e linhas criadas por código antigo depois da
  migration permanecem `NULL` sem backfill. Somente o código novo (B2) grava
  `v2` na criação. Isto concretiza R6.1-A sem novo status [APR P3-A].
- Constraints novas: `protocolo IS NULL OR protocolo = 'v2'`
  (`ent_conv_protocolo_valido`); e
  `status NOT IN ('enviando','incerta') OR tentativas > 0`
  (`ent_conv_ativa_com_tentativa`). Nomes seguem o prefixo `ent_conv_` já
  existente [APR O5-A].
- **Não** acrescentar o contador `chamadas_autorizadas` (ver 5.1) nem outras
  restrições sobre dados legados, para reduzir o risco de a migration falhar
  em linhas existentes. Constraints adicionais sobre `proxima_tentativa_em`
  ficam fora do B1.
- Constraints e índices existentes (`ent_conv_*`) permanecem, exceto o CHECK de
  status.

### 16.2 `TentativaEntregaConvite` (novo)

Uma linha por chamada externa.

- Campos: `entrega` (FK PROTECT), `numero` (inteiro positivo), `origem`
  (`automatica` ou `autorizada`), `autorizacao` (OneToOne PROTECT, nulo),
  `chave_idempotencia` (UUID copiado da entrega), `provider`, `iniciada_em`,
  `lease_expira_em`, `finalizada_em` (nulo), `desfecho` (`iniciada`, `aceita`,
  `nao_aceita`, `ambigua`, `interrompida`), `categoria_falha`, `codigo_erro`,
  `id_externo` (≤200, vazio por padrão), `evidencia_tecnica` (≤500).
- Constraints [REC, conjunto mínimo conforme O4-A]: UNIQUE `(entrega, numero)`
  (`tent_conv_numero_unico`); UNIQUE parcial `(entrega)` onde
  `desfecho='iniciada'` (`tent_conv_aberta_unica`); `desfecho='iniciada'` ⇔
  `finalizada_em` nulo (`tent_conv_finalizacao_coerente`); `origem='autorizada'`
  ⇔ `autorizacao` não nulo (`tent_conv_origem_autorizacao`).
- **Retiradas do B1 por O4-A** (sem justificativa concreta ainda; reavaliar no
  B2, onde a semântica é usada): `lease_expira_em > iniciada_em`, exigências de
  `categoria_falha` e `codigo_erro` por desfecho, e os índices
  `(entrega, desfecho)`, `(desfecho, lease_expira_em)` e `(chave_idempotencia)`.
  Os índices de FK criados pelo Django e os índices das constraints únicas
  bastam até existir a consulta que os justifique (recuperação de lease no B2).
- Sem token, link, destinatário ou credencial em nenhum campo.

### 16.3 `AutorizacaoEnvioEntregaConvite` (novo) — J9-A

Representa **uma** concessão de Fichas para **uma** chamada externa. Também é o
instrumento de liberação do legado bloqueado.

- Campos: `entrega` (FK PROTECT), `pendencia` (FK PROTECT, nula),
  `evidencia_base` (FK PROTECT para a evidência que fundamenta a decisão,
  nula), `autorizada_por` (FK User PROTECT), `autorizada_em`, `fundamento`,
  `justificativa` (texto não vazio), `ciencia_duplicidade` (booleano),
  `consumida_em` (nulo).
- `fundamento` [REC, refina D2-A e D4-A], distinguindo comprovação de não
  início de confirmação de não aceitação:
  - `nao_aceitacao_confirmada`, `falha_comprovada`, `reenvio_excepcional`
    (entregas do protocolo novo);
  - `legado_prova_nao_inicio`, `legado_nao_aceitacao_confirmada`,
    `legado_sem_prova_reconciliado` (entregas legadas bloqueadas).
  Em **todos** os casos legados a autorização de Fichas é exigida, inclusive
  com prova conclusiva [APR D2-A].
- Constraints: UNIQUE parcial `(entrega)` onde `consumida_em` é nulo, no
  máximo uma autorização em aberto (`aut_conv_aberta_unica`); justificativa
  não vazia (`aut_conv_justificativa`);
  `fundamento IN ('reenvio_excepcional','legado_sem_prova_reconciliado')` exige
  `ciencia_duplicidade = true`, pois sem prova conclusiva há risco de
  duplicidade (`aut_conv_ciencia`);
  `fundamento IN ('nao_aceitacao_confirmada','legado_prova_nao_inicio',
  'legado_nao_aceitacao_confirmada')` exige `evidencia_base` não nula
  [APR D4-A: prova positiva e verificável] (`aut_conv_evidencia_exigida`).
- **D5-A [APR]:** a correspondência entre o `tipo` da evidência e o
  `fundamento` e a pertinência da evidência à mesma entrega são validadas no
  serviço B3, sem trigger correspondente na `0052` do B1. O schema do B1,
  isoladamente, não impede autorização associada a evidência de outra entrega.
  A ativação do novo fluxo exige implementação, testes negativos e homologação
  dessas validações no B3; se insuficientes, reavaliar proteção adicional no
  PostgreSQL antes da ativação.
- **Checkpoint B1 / T2:** testes de reversão e preservação de entrega e outbox
  legados preparados para SQLite e PostgreSQL; concorrência das três constraints
  parciais e `flush` preparados para PostgreSQL. Testes complementares cobrem
  estados, combinações de autorização e evidência, encerramento, imutabilidade e
  proteção de dependências; os casos restantes de SQL direto estão preparados
  para PostgreSQL. A execução PostgreSQL e a regressão nesse banco permanecem
  pendentes. Não há autorização de ativação nem inventário do legado realizado
  neste bloco.
- Índice próprio dispensado por O4-A: a UNIQUE parcial já cobre a consulta da
  autorização aberta por entrega.
- Em emergência (P7), a autorização continua sendo concedida pelo operador
  autorizado, e a marca de emergência é gravada na auditoria. Vínculo com o
  registro de emergência é acrescentado em B3 por coluna nula aditiva.

### 16.4 `PendenciaEntregaConvite` e `EvidenciaEntregaConvite` (novos)

- **Pendência:** `encontro` (FK PROTECT, denormalizado), `entrega` (FK
  PROTECT), `tipo` (`incerta`, `falhou`, `legado_sem_prova`), `motivo` (código
  curto), `status` (`aberta`, `encerrada`), `aberta_em`,
  `ultima_evidencia_em`, `encerrada_em`, `encerrada_por` (FK User PROTECT,
  nula), `decisao` (vazia enquanto aberta), `reaberturas`, `versao`
  (inteiro, incrementado a cada transição). Constraints: UNIQUE parcial
  `(entrega)` onde `status='aberta'` (`pend_conv_aberta_unica`); aberta exige
  `encerrada_em`, `encerrada_por` e `decisao` vazios; encerrada exige os três
  preenchidos (`pend_conv_encerramento_coerente`). A coerência `encontro` =
  encontro da entrega é validada no serviço e em teste. [REC, O4-A] Os
  índices `(encontro, status, aberta_em)` e `(tipo, status)`, voltados aos
  filtros da Central (aprovados funcionalmente), entram no B4, quando a
  consulta existir, por migration aditiva.
- **Evidência (append-only):** `pendencia` (FK PROTECT), `autor` (FK User
  PROTECT, nulo para o sistema), `tipo` (`suporte_nota`,
  `prova_nao_inicio`, `provedor_confirmou_nao_aceitacao`,
  `provedor_confirmou_aceitacao`, `provedor_desconhecido`,
  `resultado_tardio_adapter`), `origem` (`interna` ou `externa`), `referencia`
  (≤200), `texto` (≤1000, minimizado), `criado_em`.
  [REC, concretiza D4-A e O2-A] `prova_nao_inicio` (comprovação positiva de que
  a chamada não começou) e `provedor_confirmou_nao_aceitacao` (confirmação
  inequívoca do provedor) são tipos **distintos**. Os três tipos que podem
  fundamentar uma decisão (`prova_nao_inicio`,
  `provedor_confirmou_nao_aceitacao`, `provedor_confirmou_aceitacao`) exigem
  `referencia` preenchida (`evid_conv_referencia_exigida`), como critério
  mínimo e objetivo de verificabilidade. O campo `origem` existe para que a
  referência seja avaliada conforme sua fonte: interna (por exemplo, um
  identificador de registro do próprio SIA) ou externa (por exemplo,
  identificador do provedor). Substitui o nome `referencia_externa` proposto
  antes, que não comportava referência interna; por ser modelo novo, não há
  renomeação de campo existente [APR O5-A]. `suporte_nota`,
  `provedor_desconhecido` e `resultado_tardio_adapter` nunca constituem prova.
  O que torna uma referência **adequada** a cada origem é regra de B3 e de
  operação, não do schema. Sem índice próprio no B1 (O4-A).

### 16.5 Imutabilidade e auditoria

- Padrão do repositório: proteção em `save`, `delete` e no `QuerySet`
  (`update`, `delete`, `bulk_update`), como em `EventoAuditoriaEncontro`.
- Janelas de mutação permitidas: **tentativa**, uma única transição de
  `iniciada` para um desfecho final, com preenchimento dos campos de resultado;
  **autorização**, `consumida_em` de nulo para valor, uma vez; **evidência**,
  nenhuma; **pendência**, apenas pelos campos de transição, sem exclusão.
  Nenhuma das quatro tabelas admite exclusão.
- Auditoria de decisões e transições: pela função existente
  `registrar_evento_auditoria_encontro`, com allowlist própria de campos e
  `origem` automática para eventos sem ator. Payload somente com IDs, status e
  códigos; nunca token, link ou PII. O evento e a mudança de estado ocorrem na
  mesma transação.
- [APR D3-A] A proteção ocorre **também no PostgreSQL**, por triggers
  (seção 16.11), cobrindo tentativas, autorizações, evidências, pendências e a
  auditoria existente. O ORM continua sendo a primeira barreira e as duas
  camadas devem aplicar as mesmas transições.
- **Limite [APR D3-A]:** não se presume inviolabilidade contra administradores
  privilegiados. O dono da tabela e quem tem privilégio de superusuário no
  PostgreSQL podem desabilitar triggers (`ALTER TABLE ... DISABLE TRIGGER`,
  `session_replication_role`), e o `TRUNCATE` não é coberto (16.11). Triggers
  reduzem alterações acidentais e de código; não impedem um administrador
  malicioso do banco.

### 16.6 Estratégia de migration

- [REC] **Duas migrations**, para poder reverter as triggers separadamente do
  schema: `0051` (schema aditivo) e `0052` (triggers, somente PostgreSQL).
  `0051` tem dependência explícita de `0050_preselecaoencontrista`, que **não é
  alterada**; `0052` depende de `0051`. Se `0050` for renomeada ou renumerada
  antes de ser commitada, a dependência é ajustada (a `0050` foi depois commitada no C0, sem renumeração).
- Operações da `0051`, em ordem: adicionar `protocolo`; recriar o CHECK de
  status e adicionar os CHECKs novos da entrega; criar as tabelas na ordem
  pendência, evidência, autorização, tentativa (dependências de chave
  estrangeira).
- Operações da `0052`: criar funções e triggers, executadas apenas quando
  `schema_editor.connection.vendor == 'postgresql'`; em SQLite (suíte padrão)
  é *no-op*. A reversão remove triggers e funções. O repositório não tem
  precedente de `RunSQL`; a única migration com SQL direto usa cursor
  (`0026_backfill_pessoa`).
- Sem backfill e sem alterar linhas existentes. A `0051` não tem `RunPython`.
  A `0052` usa `RunPython` apenas para executar DDL condicional por vendor.
- **Pré-requisitos antes de gerar a migration:** (a) `makemigrations --check
  --dry-run` sem alterações pendentes, para garantir que o working tree de
  `models.py` não carregue deriva em relação a `0050` que contamine a
  migration; (b) inventário somente leitura confirmando que nenhuma entrega
  está em `enviando` e que as linhas existentes satisfazem os CHECKs novos,
  incluindo `status NOT IN ('enviando','incerta') OR tentativas > 0`. Aplicar a
  migration no PostgreSQL não faz parte do B1 sem aprovação pontual.
- Estimativa **não verificada**: a troca de CHECK em tabela pequena exige lock
  exclusivo breve.

### 16.7 Matriz de testes e critérios de aceite do B1

Testes de modelo e constraints, em SQLite em memória, salvo indicação:

| Cenário | Esperado |
|---|---|
| Status `incerta` e `suspensa` aceitos; valor desconhecido rejeitado | CHECK |
| `enviando` ou `incerta` com `tentativas = 0` | rejeitado |
| `protocolo` fora de `NULL`/`v2` | rejeitado |
| Entregas existentes e novas sem marcador | `protocolo` nulo, sem backfill |
| Duas tentativas abertas na mesma entrega | rejeitada (UNIQUE parcial) |
| `(entrega, numero)` repetido | rejeitado |
| `origem='autorizada'` sem autorização, ou `automatica` com autorização | rejeitado |
| Duas tentativas para a mesma autorização | rejeitada (OneToOne) |
| Duas autorizações abertas para a mesma entrega | rejeitada |
| Autorização consumida permite nova autorização | aceita |
| `reenvio_excepcional` ou `legado_sem_prova_reconciliado` sem ciência | rejeitado |
| `nao_aceitacao_confirmada`, `legado_prova_nao_inicio` ou `legado_nao_aceitacao_confirmada` sem `evidencia_base` | rejeitado |
| Evidência de tipo conclusivo sem `referencia` | rejeitada |
| Pendência aberta duplicada na mesma entrega | rejeitada |
| Pendência encerrada sem `encerrada_por` ou `decisao` | rejeitada |
| Tentativa: segunda mutação após o desfecho final | rejeitada |
| Evidência: update e delete | rejeitados |
| Tentativa, autorização, pendência, evidência: delete e `queryset.update` | rejeitados |
| Exclusão de entrega, usuário ou encontro com dependentes | bloqueada (PROTECT) |
| Registros legados de entrega e outbox intactos após a migration | sem mudança |
| `makemigrations --check --dry-run` após a migration | sem pendências |
| Constraints parciais e triggers em PostgreSQL real | **PG**, ver 16.12 |

Os testes de triggers, que não rodam em SQLite, estão na seção 16.12.

**Critérios de aceite do B1 [REC]** (objetivos e verificáveis):

1. Todos os cenários SQLite desta seção e os cenários PG da seção 16.12
   escritos; os PG executados manualmente pelo responsável, conforme
   `AGENTS.md`, antes do aceite.
2. Alterações somente em `backend/core/models.py`, nas migrations `0051` e
   `0052` novas e em testes novos do B1. Nenhum serviço, task, adapter,
   configuração ou arquivo de teste existente alterado (D1-A).
3. `0050` intacta; nenhum dado legado alterado; nenhum backfill.
4. `makemigrations --check --dry-run` limpo depois das migrations.
5. Suíte padrão (SQLite) sem regressões nos testes existentes de entrega,
   outbox e auditoria.
6. Comportamento do worker idêntico ao anterior ao B1.

**Bloqueadores do B1 [REC]:** `makemigrations --check --dry-run` com deriva
antes de começar; inventário pré-migration não realizado ou com linha que viole
os CHECKs novos; qualquer necessidade de alterar serviço, task ou adapter;
falha em qualquer cenário PG de trigger; conflito entre as triggers e testes
existentes de auditoria, entrega ou outbox. O B1 não altera o comportamento do
worker nem ativa nenhuma garantia operacional: ele só prepara o schema e a
proteção de integridade.

### 16.8 Riscos e rollback de schema

- **Dois conceitos distintos [APR D1-A, J10-A].**
  - *Suspensão operacional fail-closed:* desligar a flag de entrega (B2).
    Não altera schema, não reverte nada e preserva todo o histórico. O B1, por
    não alterar o worker, não tem o que suspender.
  - *Rollback de schema:* reversão das migrations. É medida excepcional e
    **não** substitui a suspensão operacional.
- **Reversão de schema:** primeiro `0052` (remove triggers e funções), depois
  `0051` (remove tabelas e o campo e recria o CHECK antigo). A `0051` **falha**
  se existir entrega em `incerta` ou `suspensa`, porque o CHECK antigo não as
  admite. As triggers não impedem `DROP TABLE`. Antes de qualquer reversão é
  preciso garantir que não existam essas linhas e preservar o histórico que
  Fichas ainda precise, pois a reversão o destrói. Como o B1 não altera o
  worker, uma reversão logo após o B1, sem uso, é limpa.
- Risco de a migration falhar em dados reais legados: mitigado pelo
  inventário prévio (16.6).
- Risco de a migration absorver deriva do WIP: mitigado por
  `makemigrations --check --dry-run` antes (16.6).
- Código antigo que cria entregas depois da migration: cria com marcador nulo
  (legado, bloqueado). Não quebra, porque o campo é nulo.
- Triggers não protegem contra administradores privilegiados nem contra
  `TRUNCATE` (16.11) [APR D3-A].
- **Não homologado:** nomes, tamanhos de campos, índices, funções de trigger e
  comportamento sob PostgreSQL real.

### 16.9 Verificação de J9-A

O modelo garante, **no banco**, que cada autorização gera no máximo uma chamada:
a tentativa referencia a autorização por OneToOne, e só pode existir uma
autorização em aberto por entrega. A autorização é marcada consumida na mesma
transação (Tx1) que cria a tentativa. Se a Tx1 falhar antes do commit, nenhuma
chamada ocorreu (invariante I1) e a autorização continua em aberto. Se a
chamada ocorrer e falhar, a autorização já está consumida: outra chamada exige
**nova** autorização de Fichas.

Para entregas legadas, [REC] uma trigger de inserção de tentativa (16.11)
impede, no banco, que exista tentativa para entrega de `protocolo` nulo sem
autorização, tornando estrutural o bloqueio de R6.1-A e a exigência de
autorização de Fichas de D2-A.

O que o schema **não** garante, e que o B2 deve cumprir e testar: que, após uma
tentativa `autorizada`, a entrega siga para `FALHOU` ou `INCERTA` sem agendar
retry automático nem criar tentativa `automatica`. O marcador `origem` permite
ao B2 contar apenas tentativas automáticas e recusar o backoff, mas a regra de
transição é de serviço, não de constraint.

### 16.10 Dependências futuras

- **B2:** estampar `protocolo='v2'` na criação da entrega; guarda do legado na
  Tx1; criação e consumo de tentativa e autorização; transições de estado;
  uso de `origem` para limitar retries.
- **B3:** serviço de reconciliação sobre pendência, evidência e autorização;
  migration aditiva própria para ocorrência técnica agrupada, lote de retomada
  e autorização emergencial; geração controlada das pendências de legado;
  `ModelAdmin` somente leitura.
- **B4:** serializers por perfil e API da Central, sobre os mesmos modelos.

### 16.11 Triggers PostgreSQL (migration `0052`) [APR D3-A; desenho REC]

Que haja proteção no PostgreSQL é [APR D3-A]. As regras abaixo são o desenho
proposto [REC]. Violação lança erro com `SQLSTATE 23514` (`check_violation`),
que o Django traduz em `IntegrityError`, coerente com as constraints. Funções
com prefixo próprio (por exemplo `sia_conv_*`) e triggers `BEFORE` por linha.

| Tabela | Evento | Regra |
|---|---|---|
| Tentativa | `DELETE` | sempre recusado |
| Tentativa | `UPDATE` | permitido apenas se `OLD.desfecho='iniciada'`, `NEW.desfecho<>'iniciada'` e `NEW.finalizada_em` preenchido; as colunas `id`, `entrega_id`, `numero`, `origem`, `autorizacao_id`, `chave_idempotencia`, `provider`, `iniciada_em` e `lease_expira_em` não podem mudar. Tentativa já finalizada: recusado |
| Tentativa | `INSERT` | se a entrega tem `protocolo` nulo (legado), `autorizacao_id` é obrigatório; se `autorizacao_id` não é nulo, a autorização pertence à mesma entrega |
| Autorização | `DELETE` | sempre recusado |
| Autorização | `UPDATE` | permitido apenas de `consumida_em` nulo para preenchido, uma vez, com as demais colunas inalteradas |
| Evidência | `UPDATE`, `DELETE` | sempre recusados |
| Pendência | `DELETE` | sempre recusado |
| Pendência | `UPDATE` | colunas de identidade (`id`, `encontro_id`, `entrega_id`, `tipo`, `aberta_em`) inalteradas |
| Entrega | `UPDATE` | `protocolo` não pode mudar (`IS DISTINCT FROM`): só é definido na inserção. Isso impede "liberar" um legado trocando o marcador, sem alterar nenhuma outra coluna nem o comportamento do worker antigo |
| Auditoria existente (`EventoAuditoriaEncontro`) | `UPDATE`, `DELETE` | sempre recusados |

**Conjunto mínimo [APR O4-A, aplicação REC].** Cada trigger acima tem
justificativa concreta: as de tentativa, autorização e evidência sustentam
J9-A, D3-A e o histórico append-only; a de `protocolo` e a de `INSERT` de
tentativa tornam estrutural R6.1-A e D2-A; a de auditoria é pedida por D3-A; a
de identidade da pendência evita que uma pendência seja reatribuída a outra
entrega ou Encontro, o que corromperia o histórico. **Retiradas do B1 por falta
de justificativa concreta**, a reavaliar quando houver evidência de
necessidade: monotonicidade de `versao` e `reaberturas` no banco (a
concorrência já é protegida por lock e `estado_esperado`); verificação, por
trigger, de que `evidencia_base` pertence à mesma entrega e de que seu `tipo` é
compatível com o `fundamento`; verificação de que `encontro_id` da pendência
coincide com o da entrega; e a trigger diferida de consumo da autorização.
Essas regras permanecem como validação de serviço e de teste (B3).
Triggers de apoio só serão adicionadas com justificativa documentada.

Consequências e limites:

- Não há trigger de `TRUNCATE`: ela quebraria o `flush` de
  `TransactionTestCase` no PostgreSQL, usado nos testes de concorrência
  existentes. Logo, `TRUNCATE` por administrador não é coberto.
- Não há validação das linhas já existentes ao criar as triggers; só alterações
  futuras são avaliadas.
- Triggers da auditoria: verificado que o único código que tenta atualizar ou
  excluir eventos de auditoria são testes que esperam a recusa do próprio ORM
  (`test_encontro_auditoria.py`), que ocorre antes do banco. Não encontrei
  outro uso. **Consequência a decidir:** pedidos de correção ou anonimização de
  dados pessoais em eventos de auditoria deixam de ser possíveis pela aplicação
  e passam a exigir procedimento excepcional de administrador de banco,
  documentado e auditado (pendência O1).
- A alteração da tabela de auditoria, já estabilizada, é uma mudança de
  contrato de integridade, não de comportamento de serviço; o impacto,
  a migration `0052` e os testes estão descritos aqui, conforme o `AGENTS.md`.
- Triggers só existem em PostgreSQL. A suíte padrão (SQLite em memória) não as
  exercita; os testes de trigger usam `skipUnless(connection.vendor ==
  'postgresql')`, padrão já adotado no repositório.

### 16.12 Testes PostgreSQL de integridade (manuais, `skipUnless`) [REC]

| Cenário | Esperado |
|---|---|
| `UPDATE` de tentativa finalizando uma `iniciada` | aceito |
| `UPDATE` de tentativa já finalizada, ou alterando coluna de identidade | recusado |
| `DELETE` de tentativa, autorização, evidência, pendência | recusado |
| `UPDATE` de evidência | recusado |
| `UPDATE` de autorização preenchendo `consumida_em` uma vez | aceito |
| Segundo `UPDATE` de autorização, ou outra coluna | recusado |
| `UPDATE` de pendência alterando identidade | recusado |
| `UPDATE` de pendência em campos de transição | aceito |
| `UPDATE` de entrega mudando `protocolo` (nulo para `v2`, ou o inverso) | recusado |
| `UPDATE` de entrega legada alterando só `status` e contadores | aceito (código antigo não quebra) |
| `INSERT` de tentativa para entrega legada sem autorização | recusado |
| `INSERT` de tentativa com autorização de outra entrega | recusado |
| `INSERT` de tentativa para entrega `v2` sem autorização, origem automática | aceito |
| `UPDATE` e `DELETE` em `EventoAuditoriaEncontro` por SQL direto | recusados |
| `INSERT` em `EventoAuditoriaEncontro` pela função existente | aceito |
| Constraints parciais únicas (tentativa aberta, autorização aberta, pendência aberta) sob concorrência | uma vence |
| `0052` aplicada e revertida; `0051` aplicada e revertida em banco limpo | sem erro |
| Suíte de testes existente de entrega, outbox e auditoria sob PostgreSQL | sem regressão |
| `TransactionTestCase` com `flush` (`TRUNCATE`) após as triggers | sem erro |

### 16.13 Garantias estruturais e limites a impor por serviço (B2/B3)

**Garantido no schema e nas triggers [REC]:** uma tentativa por autorização;
uma tentativa aberta por entrega; uma autorização e uma pendência abertas por
entrega; tentativa de legado só com autorização; marcador de protocolo
imutável; histórico imutável fora das transições legítimas.

**Não garantido pelo schema, a cumprir e testar nos serviços:**

- apenas Fichas concede autorização (Suporte e emergência conforme J1, P7 e
  R5-A); o banco só registra `autorizada_por`;
- revalidar a oportunidade (válida, não expirada), a campanha e o segredo
  antes de qualquer processamento [APR D2-A];
- após tentativa `autorizada`, nenhum retry automático nem nova tentativa
  `automatica` (J9-A);
- correspondência entre o tipo da evidência e o `fundamento` e suficiência da
  referência verificável [APR D4-A];
- criação das pendências de legado somente após inventário e classificação
  [APR R6.1-A];
- bloqueio do legado no serviço, independente de fila ou task [APR R6-A];
- registro de auditoria na mesma transação de cada decisão.

**Conflitos identificados e propostas [REC]:**

1. *Triggers na auditoria existente × estabilidade do contrato.* Proposta:
   aplicar no `0052` separado, com testes de regressão (16.12) e o
   procedimento excepcional de O1.
2. *Triggers só em PostgreSQL × suíte padrão em SQLite.* Proposta: a
   proteção em Python replica as mesmas transições, e os testes de trigger
   são `skipUnless` e executados manualmente.
3. *D1-A (B1 não altera services) × necessidade do marcador `protocolo`.* Não
   há conflito: o campo é nulo por padrão, e o código existente não precisa
   conhecê-lo; só o B2 passa a gravá-lo.
4. *`TRUNCATE` e administradores privilegiados.* Aceito como limite [APR D3-A].

### 16.14 Parecer de prontidão do B1 (revisão estática) [REC]

> Histórico, anterior à implementação. Os gates abaixo foram superados pelo
> aceite A1 (seção 16.15).

**Parecer: AJUSTES RECOMENDADOS.** Não encontrei impedimento no desenho. Esta é
análise estática; nada foi executado.

**Verificações feitas (leitura):**

- Encadeamento `0049 → 0050 → 0051 → 0052`: `0050` depende de `0049`, cria
  apenas `PreSelecaoEncontrista` e não é referenciada por nenhuma outra
  migration. Um teste da frente de Pré-seleção importa o módulo
  `core.migrations.0050_preselecaoencontrista` pelo nome
  (`test_preselecao_encontristas_models.py`), portanto o arquivo **não pode ser
  renomeado nem renumerado** sem quebrar esse teste.
- Modelos existentes: nomes de tabela padrão (`core_entregaconviteencontro`,
  `core_eventoauditoriaencontro`); constraints existentes de entrega e outbox
  coerentes com as mudanças propostas; `status` de entrega, hoje com 4 valores,
  é o único CHECK recriado.
- Django 5.2.16: troca de CHECK por `RemoveConstraint` e `AddConstraint`
  (16.1). `makemigrations` é usado com `condition=` nas constraints, como no
  restante do repositório.
- Auditoria existente: o único código que tenta `update`/`delete` de eventos de
  auditoria são testes que esperam a recusa do ORM, que ocorre antes do banco.
- `TransactionTestCase` existente no repositório usa `flush`; por isso não há
  trigger de `TRUNCATE`.

**Bloqueadores efetivos do B1 (gates antes de escrever ou aplicar a migration):**

1. `makemigrations --check --dry-run` ainda **não foi executado**. Sem ele não
   se sabe se o `models.py` do WIP carrega deriva em relação à `0050`, o que
   contaminaria a `0051`. Gate do DEV, antes de qualquer código.
2. O arquivo e o número da `0050` precisam estar definitivos antes de criar a
   `0051` (item acima: o teste importa o nome).
3. O inventário somente leitura do legado **não foi realizado**. Ele é gate para
   **aplicar** a `0051` no PostgreSQL (os CHECKs novos validam todas as linhas
   existentes), não para escrever o código. Exige aprovação pontual de acesso ao
   banco, conforme `AGENTS.md`.
4. Os testes PG de trigger só podem ser executados manualmente pelo
   responsável; o aceite do B1 depende disso.

**Pendências futuras (não bloqueiam o B1):**

- *B2:* semântica de `lease`, `categoria_falha`/`codigo_erro` por desfecho,
  índices de recuperação, marcação `v2`, transições de estado, limite de retries
  após tentativa autorizada, guarda do legado no serviço.
- *B3:* regras de adequação de `referencia` por `origem` (O2), correspondência
  entre tipo de evidência e `fundamento`, ocorrência técnica agrupada, lote de
  retomada, emergência, geração das pendências do legado.
- *B4:* índices de filtros da Central e API.
- *Operação:* procedimento excepcional de auditoria (O1), separação de
  privilégios PostgreSQL (O3), configuração de flag, fila e lease.
- *C5.4:* homologação PostgreSQL ampla, lease, concorrência, janela de deploy.

**Não verificado:** comportamento das triggers e das constraints parciais em
PostgreSQL real; migrations aplicadas; dados reais do legado; testes.

### 16.15 Aceite técnico C5.3-B1-A1 [APR]

Aceite técnico humano do bloco B1. Não autoriza commit, implantação, ativação
nem B2.

- **Aceito:** models, constraints e migrations `0051` (schema aditivo) e `0052`
  (triggers PostgreSQL reversíveis, no-op em SQLite), conforme as seções 16.1 a
  16.13, sem alterar services, workers, tasks, adapters, API ou frontend.
- **PG2-B:** 68 testes, 67 aprovados, 1 pulado e nenhuma falha, em PostgreSQL 16
  descartável, executado pelo responsável. SQLite pós-T2: 29 testes, 13
  aprovados e 16 pulados (testes de PostgreSQL).
- **Revisão independente do QA:** aprovada, sem defeito impeditivo.
- **D5-A [APR]:** a correspondência entre evidência, fundamento e entrega é
  validação obrigatória do B3, sem trigger na `0052`. Risco residual: o schema
  do B1, isoladamente, não impede autorização associada a evidência de outra
  entrega. A ativação do novo fluxo exige implementação, testes negativos e
  homologação dessas validações no B3.
- **O1:** procedimento excepcional de auditoria/LGPD **pendente**.
- **Inventário do legado:** dispensado neste ambiente, pois o responsável
  informou não haver dados legados (informação não verificada por consulta).
  Verificação condicional: antes de aplicar a `0051` em qualquer base com
  registros anteriores, confirmar por consulta somente leitura que nenhuma
  entrega está em `enviando` ou `incerta` com `tentativas = 0`
  (`ent_conv_ativa_com_tentativa`).
- **Dependência:** a `0051` depende da `0050_preselecaoencontrista` (outra
  frente), cujo nome não pode mudar (um teste a importa pelo nome).
- **Não autorizado pelo A1:** commit, implantação, ativação e avanço para B2.
  (O commit foi autorizado depois, separadamente; ver 16.16.)

### 16.16 Commit local C1 e homologações do snapshot [FATO, registro]

- **C1:** `1c42f634cda238e476f4e9376f4db7b307df288a`
  (`feat(entrega): adiciona reconciliacao e integridade de convites`), local,
  não publicado, com `models.py` (hunks do B1), migrations `0051` e `0052` e
  quatro arquivos de teste. A `0050` está no C0 (`426b177dc0575711b87bffab58e01b189b14ccb9`).
- **Estado:** B1 commitado, **não ativado**; nenhuma migration aplicada em banco
  persistente.
- **SQLite G-B1:** 29 testes, 13 aprovados, 16 pulados (exigem PostgreSQL).
  **SQLite G-REG:** 39 aprovados. **SQLite G-PRE:** 169 testes, 129 aprovados,
  40 pulados.
- **PostgreSQL descartável sobre o snapshot C1:** 68 testes, 67 aprovados e 1
  pulado; resultado **relatado pelo operador humano, não observado diretamente
  pelo ARCH**. Distinto da homologação PostgreSQL anterior da Pré-seleção (169
  testes, C0-A1) e do PG2-B pré-commit (16.15).
- **Permanecem abertos:** D5-A (validação obrigatória no B3, com testes
  negativos e homologação antes da ativação), O1 (auditoria/LGPD), B2–B4 (não
  autorizados), C5.4 e inventário condicional do legado.
