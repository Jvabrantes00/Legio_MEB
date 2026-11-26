# SIA/MEB — Estado do Projeto

## Estado verificado em 2026-11-24

- **VERIFICADO:** branch `sia/roadmap-rebaseline`, HEAD
  `7547ad0807a6cb4518805eb9d26302c5ed685ddf`; publicação na branch de
  desenvolvimento verificada pelo ARCH. GE-2A (`e4ac93c`), GE-2B-1
  (`db3bc5e`) e GE-2B-2 (`7547ad0`) estão implementados e publicados nessa
  branch, sem merge na main nem implantação em produção, conforme evidência
  fornecida. Antes deles: seed de Coordenação Geral `3e17195`, seed_demo
  idempotente `202f9a1` e autoridade funcional de Suporte `ec9a86f`.
- **VERIFICADO pelo ARCH:** homologação HTTP GE-2B-2 com SQLite descartável,
  cliente → BFF → backend: 153/154 verificações OK. A divergência aceita é
  auditoria redundante na desalocação idempotente, sem mudança de dados.
  Coordenação Geral leu apenas o próprio Encontro (200), recebeu 403 nas
  escritas e em outros Encontros; payloads iguais aos de Fichas. Houve
  conferência de integridade SHA-256 e auditorias Git.
- **REGISTRADO pelo ARCH:** homologação HTTP GE-2B-1, 61/61, em pacote anterior.
- **RELATADO por DEV/QA, não reexecutado pelo ARCH:** frontend 35 arquivos,
  471 testes aprovados, lint sem erros e dois avisos antigos, TypeScript sem
  erros; backend check e migration check limpos, 1116 testes OK e 75 pulados
  em SQLite em memória.
- **RELATADO por pessoas:** validação visual GE-2B-2 em nove cenários; C5 B1
  em PostgreSQL, 67 aprovados e um pulado.
- **NÃO VERIFICADO/PENDENTE:** suíte PostgreSQL completa e build no HEAD,
  produção, backup e homologação com usuários reais; idempotência de
  `iniciar_trabalho_confirmado`, campos de encontristas para Coordenação
  Geral com registros preenchidos, seletor de status e rótulos terminais.
  A auditoria redundante foi aceita como pendência. Faltam catálogo real
  aprovado, telas operacionais e exposição no BFF de retirar, substituir e
  registrar resultado; C5 tem somente schema B1 e não está ativado.
- **Legado:** a meta aprovada é substituir o legado preservando os dados
  históricos; a estratégia de migração ainda não foi homologada. Detalhes no
  [handoff](HANDOFF.md).

## Estado atual

> Snapshot de 11/nov/2026, HEAD 1c42f63 — histórico; leia primeiro o bloco
> 'Estado verificado em 2026-11-24'.

- Snapshot documental atualizado em 11 de novembro de 2026, sem nova
  verificação geral de todo o projeto.
- Branch observada: `sia/roadmap-rebaseline`.
- HEAD observado: `1c42f634cda238e476f4e9376f4db7b307df288a`
  (`feat(entrega): adiciona reconciliacao e integridade de convites`, C1),
  precedido pelo C0 `426b177dc0575711b87bffab58e01b189b14ccb9`
  (`feat(preselecao): implementa pre-selecao de encontristas no backend`) e
  pelo F-01 `a44518c8b76143319974032150950d14d8b9fab8`
  (`fix: restrict communication pre-encounter access`).
- Branch e HEAD registram somente o snapshot desta reconciliação; não são
  identificadores permanentes do estado do projeto.
- **FASE 0 — ESTABILIZAÇÃO: CONCLUÍDA**
- **FASE 1 — REMODELAGEM DE DOMÍNIO: EM ANDAMENTO**
- **ROADMAP RE-BASELINE / IMPLEMENTAÇÃO R.3I: EM ANDAMENTO**

## Roadmap

| Etapa | Estado |
|---|---|
| 0A Segurança e configuração | ✅ Concluída |
| 0B Ambiente, dependências e lint | ✅ Concluída |
| 0C Base de regressão | ✅ Concluída |
| 0D Dados, CPF, atomicidade e dashboard | ✅ Concluída |
| 0E Autorização, privacidade, mídia e auditoria | ✅ Concluída |
| 0F Autenticação, JWT e BFF | ✅ Concluída |
| 0G Integração frontend/API | ✅ Concluída |
| 0H PostgreSQL e legado | ✅ Concluída |
| 0I Débitos técnicos restantes | ✅ Concluída |
| 0J Gate e auditoria final | ✅ Concluída |
| Fase 1 Remodelagem de domínio | Em andamento; 1B.3D.6 Calendário Institucional concluída; Roadmap Re-baseline e implementação R.3I em andamento |

## Estado corrente do Roadmap Re-baseline

### Marcos recentes

- R.3I.24 está implementada e validada de forma focada, conforme os registros
  disponíveis.
- R.3I.25 — Bloco 1 está implementado. Sua conclusão foi confirmada pelo
  usuário e passa a integrar o registro documental neste bloco.
- R.3I.25 — Bloco 2, Encontristas: C3 concluído tecnicamente com ressalvas,
  no commit local `fe6504a`. Pendem build Next.js, validação em navegador
  real, integração com backend e banco e o débito opcional de `useMemo`.
- R.3I.26 e R.3I.27 permanecem planejadas. Suporte parcial eventualmente já
  existente não equivale à conclusão desses blocos.

### Correção de segurança F-01

- **F-01 foi encerrada tecnicamente com ressalva por decisão humana de 26 de
  outubro de 2026.** A correção segregou o acesso mínimo de Comunicação dos
  contratos operacionais completos do Pré-Encontro.
- Backend, BFF e frontend foram implementados e validados nas verificações
  focadas: a suíte backend focada e 101 testes frontend/BFF foram aprovados, e
  TypeScript e ESLint terminaram sem diagnósticos reportados.
- Sete dos oito cenários do smoke test humano foram aprovados: A–D e F–H. O
  cenário E, Coordenação Geral contextual, permanece **adiado e pendente de
  validação manual** por ausência de conta demo contextual preparada; suas
  policies foram inspecionadas e possuem cobertura automatizada.
- A decisão de encerramento técnico, por si só, não autorizou operação Git de
  escrita. Posteriormente, o Bloco 5G.4 autorizou e criou exclusivamente o
  commit local F-01 `a44518c8b76143319974032150950d14d8b9fab8`, com a
  mensagem `fix: restrict communication pre-encounter access` e os 16 arquivos
  de código e testes da correção.
- (obsoleto: publicado; ver bloco de 2026-11-24) O commit F-01 ainda não foi publicado. Os oito commits funcionais anteriores,
  o F-01 e os commits locais C0 e C1 (ver as seções da Pré-seleção e do C5)
  aguardam publicação controlada; nenhum push, merge ou deploy foi realizado ou
  autorizado.
- Os 13 Markdown da reconciliação documental permanecem modificados e sem
  commit. `docs/design/` continua não rastreado e fora da estratégia atual.

### R.3I.16-C5 — Entrega externa de convites e reconciliação

Checkpoint documental. **Somente o C5.3-B1 (schema e integridade) foi
implementado, aceito tecnicamente (A1, abaixo) e commitado localmente no C1
(`1c42f634cda238e476f4e9376f4db7b307df288a`); B2, B3 e B4 não foram iniciados.** O B1 está
commitado, mas **não ativado**: o novo fluxo de entrega não está ativado e
nenhuma migration foi aplicada em banco persistente.

- **C1 — commit local B1:** `1c42f634cda238e476f4e9376f4db7b307df288a`
  (`feat(entrega): adiciona reconciliacao e integridade de convites`), com 7
  arquivos: `models.py` (hunks do B1), migrations `0051` e `0052` e quatro
  arquivos de teste do B1. Foi autorizado após o aceite A1 (que não autorizava
  commit); não foi publicado. (obsoleto: publicado; ver bloco de 2026-11-24)
- **Homologações do snapshot C1:**
  - SQLite G-B1: 29 testes, 13 aprovados, 16 pulados por exigirem PostgreSQL.
  - SQLite G-REG: 39 aprovados.
  - SQLite G-PRE: 169 testes, 129 aprovados, 40 pulados.
  - PostgreSQL descartável: 68 testes, 67 aprovados e 1 pulado, resultado
    **relatado pelo operador humano e não observado diretamente pelo ARCH**.
    Esta cobertura foi executada especificamente sobre o snapshot C1 e é
    distinta da homologação PostgreSQL anterior da Pré-seleção (169 testes, ver
    C0-A1) e do PG2-B pré-commit registrado no A1.

- **C5.3-B1-A1 [APR] — aceite técnico humano:**
  - Implementação aceita: models, constraints e migrations `0051` (schema
    aditivo) e `0052` (triggers PostgreSQL reversíveis, no-op em SQLite), sem
    alterar services, workers, tasks, adapters, API ou frontend.
  - PG2-B: 68 testes, 67 aprovados, 1 pulado e nenhuma falha, em PostgreSQL 16
    descartável. SQLite pós-T2: 29 testes, 13 aprovados e 16 pulados (PG).
  - Revisão independente do QA: aprovada, sem defeito impeditivo.
  - **D5-A [APR]:** a correspondência entre evidência, fundamento e entrega é
    validação obrigatória do B3, sem trigger na `0052`; a ativação do novo
    fluxo depende de sua implementação, testes negativos e homologação.
  - **O1:** procedimento excepcional de auditoria/LGPD continua **pendente**.
  - **Inventário do legado:** dispensado neste ambiente, pois o responsável
    informou não haver dados legados (informação do responsável, não
    verificada por consulta). Permanece verificação condicional antes de
    aplicar a `0051` em base com registros anteriores.
  - **Autorização:** o A1 em si não autorizou commit, implantação nem
    ativação. O commit local C1 foi autorizado posteriormente e separadamente;
    implantação e ativação continuam **sem autorização**.

- **C5.1:** diagnóstico concluído por inspeção estática. O worker atual chama o
  provedor dentro da transação; falha entre aceitação externa e persistência
  pode duplicar o envio. É risco de projeto lido no código, não defeito
  reproduzido.
- **C5.2:** decisões funcionais e operacionais consolidadas (J1–J10, P1–P7,
  R3–R6, R6.1, D1–D4 e O1–O5) em [[workplans/R3I16_C5_ENTREGA_RECONCILIACAO|R.3I.16-C5 — Entrega
  externa e reconciliação]]. Reconciliação exclusiva de Fichas em condições
  normais, com exceção limitada e formal por indisponibilidade de Fichas (P7):
  aprovação cruzada Suporte/Diretoria, solicitante pode operar após aprovação
  independente, prazo de espera por nível de urgência (valores não
  homologados), retorno de Fichas não revoga automaticamente a autorização,
  que vale só até o prazo concedido, e `INCERTA` desconhecida não pode ser
  encerrada por operador emergencial. Resultado incerto suspende reenvios;
  legado `LEGADO_SEM_PROVA` é bloqueado obrigatoriamente no serviço/backend,
  sem reenvio automático; ativação por feature flag com rollback
  *fail-closed*, sem retorno ao worker antigo.
- **R6.1-A [APR]:** entregas legadas `PENDENTE` sem prova confiável de não
  envio ficam bloqueadas **independentemente do contador de tentativas**;
  zero tentativas não comprova ausência de envio no processamento antigo. O
  bloqueio é obrigatório no serviço/backend; a liberação exige evidência
  segura ou reconciliação autorizada por Fichas, com uma chamada por
  autorização (J9-A). Substitui qualquer elegibilidade automática do legado
  com zero tentativas.
- **D1–D4 [APR]:** B1 limitado ao schema essencial (entregas, tentativas,
  autorizações individuais, pendências e evidências), sem alterar workers,
  services ou adapters; emergências, alertas agrupados e retomadas em lote no
  B3. Toda liberação de entrega legada bloqueada exige autorização explícita e
  auditada de Fichas, mesmo com prova conclusiva; Suporte só investiga.
  Integridade protegida no ORM e no PostgreSQL por triggers, sem presumir
  inviolabilidade contra administradores privilegiados. Prova confiável exige
  evidência positiva e verificável de não início **ou** confirmação inequívoca
  de não aceitação pelo provedor; ausência de sucesso, logs incompletos e
  contador zero não são prova.
- **C5.3:** blocos previstos B1 a B4; cada um exige autorização expressa. O B1
  (seção 16 do workplan) está implementado e aceito (A1): duas migrations
  (`0051` schema e `0052` triggers PostgreSQL, dependentes da `0050`),
  marcador de protocolo nulo para legado, autorização individual consumida por
  uma única tentativa, e trigger que impede tentativa de legado sem
  autorização. B2, B3 e B4 **não iniciados e não autorizados**.
- **O1–O5 [APR] (diretrizes, não homologam os detalhes [REC]):** auditoria
  imutável nas operações normais, com tratamento excepcional de dados pessoais
  apenas por procedimento separado, autorizado e auditado; evidências
  conclusivas com referências verificáveis adequadas à origem interna ou
  externa; separação futura de privilégios PostgreSQL de runtime e migrations,
  sem alterar credenciais agora; conjunto mínimo suficiente de constraints e
  triggers; convenções de nomenclatura existentes.
- **Parecer técnico do B1 (revisão estática, anterior à implementação;
  superado pelo A1):** gates então listados. Situação atual: `makemigrations
  --check --dry-run` sem alterações; `0050` estável e preservada (um teste da
  frente de Pré-seleção importa o módulo pelo nome); testes PostgreSQL
  executados pelo responsável (PG2-B); inventário do legado dispensado neste
  ambiente (ver A1).
- **Risco registrado:** as triggers na auditoria existente impedem correção ou
  anonimização de dados pessoais pela aplicação; o procedimento excepcional
  (O1) ainda não está definido, mas não bloqueia o B1.
- **Verificações não realizadas:** aplicação das migrations `0051`/`0052` em
  banco persistente, inventário do legado (dispensado, condicional) e
  homologação do fluxo completo (C5.4).
- **C5.4:** homologação futura, incluindo PostgreSQL e cenários de falha.
- **Dependência:** a migration `0050_preselecaoencontrista` pertence à frente
  Pré-seleção e foi incluída no C0 (`426b177dc0575711b87bffab58e01b189b14ccb9`); as migrations `0051`/`0052` do C5
  dependem dela. Não se presume a aplicação de nenhuma delas em banco
  persistente.
- **Pré-requisito operacional não realizado:** inventário do legado antes de
  qualquer ativação ou geração de pendências.
- **Recomendações técnicas [REC] pendentes de aprovação:** invariante de
  commit da tentativa antes da chamada, estados `INCERTA` e `SUSPENSA`,
  tabelas de tentativa, pendência, evidência, ocorrência técnica e autorização
  emergencial, lease, nomes da flag e da fila. Nada disso foi homologado.
- **Fora de escopo:** API interna de aprovação de encaminhamentos por Fichas e
  provedor real de WhatsApp.
- **Ponto de retomada:** autorização específica para B2, que continua não
  iniciado e não autorizado. B3 (incluindo a validação D5-A) é pré-requisito
  de qualquer ativação; B2–B4 permanecem sem implementação autorizada.

### Pré-seleção de Encontristas (backend) — aceite técnico C0-A1 e commit C0

- **C0 — commit local:** `426b177dc0575711b87bffab58e01b189b14ccb9`
  (`feat(preselecao): implementa pre-selecao de encontristas no backend`), com
  19 arquivos de backend, incluindo a migration `0050_preselecaoencontrista`.
  O commit é local e não foi publicado. O registro C0-A1 abaixo é preservado
  como histórico do aceite técnico, anterior ao commit.

- **C0-A1 [APR]: APROVADO** — aceite técnico humano da frente Pré-seleção
  (backend): `PreSelecaoEncontrista`, migration `0050_preselecaoencontrista`,
  `services/preselecoes_encontristas.py`, novas policies em `permissions.py`,
  projeção em `campanhas_convites.py` e `serializers.py`, e os testes
  correspondentes.
- **Homologação PostgreSQL 16 descartável:** 169 testes, resultado OK, sem
  falhas ou skips reportados, executada pelo operador humano. O ARCH não
  reproduziu essa execução.
- **Revisão independente do QA:** concluída, sem defeitos confirmados; parecer
  favorável consolidado pelo ARCH.
- **Lock-order de participação e trabalho:** aceito (`Encontro` antes de
  `Pessoa` em `participacoes.py` e `trabalhos.py`), com a **ressalva** de que
  não há teste A/B individual por hunk; só o hunk de `criar_convite` tem
  evidência direta de necessidade pelo encaminhamento.
- **Staging seletivo exigido para o C0 (registro histórico; o C0 já foi
  commitado):** `backend/core/models.py` hunk
  1 (`PreSelecaoEncontrista`) pertence à Pré-seleção; os hunks 2–7 pertencem ao
  C5.3-B1. Os demais arquivos compartilhados (`campanhas_convites.py`,
  `serializers.py`, `participacoes.py`, `trabalhos.py`) e os testes modificados
  devem ser conferidos antes do staging; o índice deve ser verificado por
  export antes de qualquer commit.
- **Fora do C0:** o frontend do R.3I.25 — Bloco 2, Encontristas
  (`EncounterCandidatesPanel`, `EncounterWorkspace`, `page` e seus testes).
- **Registro posterior:** o frontend do Bloco 2 foi incluído no C3
  (`fe6504a`), com aceite técnico humano e as ressalvas acima.
- **Workplan:** não existe workplan específico da Pré-seleção em
  `docs/workplans/`; o workplan do C5 (Entrega/Reconciliação) trata de outra
  frente e não foi alterado para este registro.
- **Limite do aceite:** o C0-A1 (autorização técnica) **não** autorizava stage,
  commit, push, aplicação de migrations em banco persistente nem avanço para
  C1, C2 ou B2. O commit C0 foi autorizado posteriormente, em decisão humana
  separada, e a `0050` foi incluída nele. Push, aplicação de migrations em banco
  persistente e B2 continuam não autorizados; a `0050` não é presumida aplicada
  em banco.

### Desenvolvimento autônomo supervisionado

As decisões AUT-01 a AUT-05 e os limites operacionais estão registrados em
[[AUTONOMOUS_DEV_PROTOCOL]]. O piloto AUT-A1 não está autorizado por este registro.

### Pendências preservadas

- R.3I.16 aguarda revalidação dos 11 cenários PostgreSQL depois das correções;
  não há resultado final comprovado no registro disponível.
- R.3I.23 permanece planejada e obrigatória antes do cutover, sem conclusão
  comprovada.
- C3: build Next.js, navegador real, integração com backend e banco e débito
  opcional de estabilização de referências com `useMemo` permanecem pendentes.
- Ressalvas técnicas do ARCH: não há teste A/B individual por hunk da mudança
  de lock-order do C0; a homologação PostgreSQL do C0 foi relatada pelo
  operador humano e não reproduzida pelo ARCH. No C3, falta teste integrando
  os componentes reais `EncounterWorkspace` e `EncounterCandidatesPanel`;
  o TypeScript com `strict: false` limita a abrangência da verificação.
- A homologação ou o fechamento formal de R.3I.1 a R.3I.9 permanece
  documentalmente indeterminado. A existência de implementação e testes não
  permite promovê-las automaticamente a concluídas.
- A ordem das próximas execuções funcionais ainda não foi definida.

A reconciliação V.2 já está aplicada ao working tree, mas ainda não foi
commitada nem publicada. O ledger histórico e detalhado dos blocos permanece
em [[workplans/R3C_IMPLEMENTATION_PLAN|R.3C.7 — Plano de implementação]], sem
substituir este documento como fonte principal do estado vigente.

## Estado da Fase 1

- 1B.3B concluiu a fundação de `Pessoa`, os modelos auxiliares e o backfill
  inicial a partir do `Alpinista` legado.
- O backfill preserva IDs e mantém compatibilidade incremental com o modelo
  legado.
- 1B.3C implementou e validou o domínio de `Paroquia`, `Grupo`,
  `ConfiguracaoGrupo`, `VinculoGrupo`, `CoordenacaoGrupo` e `Frequencia` no
  commit `3b30726 feat: add group and frequency domain`.
- O profiling 1B.3C.2 de `Alpinista.grupo` foi concluído. O valor legado atual
  é insuficiente para criar `Grupo` ou `VinculoGrupo` automaticamente com
  segurança; nenhum backfill será feito neste momento.
- O backfill histórico de Grupo permanece bloqueado até a obtenção e a
  reconciliação do catálogo legado real.
- O backfill automático de `PerfilAlpinista` continua bloqueado até a
  reconciliação das evidências do legado. Para novos resultados inequívocos,
  a conclusão transacional de Escalada ou ESPPA cria o perfil com segurança.
- 1B.3D.0 definiu o Calendário Institucional como HUB que projeta Encontros,
  Eventos e compromissos sem duplicar os objetos dos domínios de origem.
- A decisão aprovou o lifecycle futuro de Encontros, dias não consecutivos,
  planejamento editável antes da confirmação e versionamento das agendas
  oficiais. A arquitetura está registrada em
  [[decisions/ADR-001-calendario-institucional]].
- 1B.3D.1 implementou o lifecycle administrativo de `Encontro` e introduziu
  `CalendarioEncontro` e `DiaEncontro` no commit
  `6e786ef feat: add encounter lifecycle and calendars`.
- O planejamento provisório pode ser editado sem criar versões. Após a
  oficialização, reprogramações preservam a agenda anterior e criam uma nova
  versão.
- A API legada continua preservando seus campos e contratos anteriores.
  `data_referencia` e `data_exato` coexistem temporariamente com o novo
  calendário e permanecem como débito de compatibilidade.
- `status_encontro` continua sendo uma projeção temporal legada baseada em
  data; não representa nem substitui o novo lifecycle administrativo.
- 1B.3D.2 concluiu Inscrição, Convite e Participação. `Inscricao`,
  `ConviteEncontro` e o novo `ParticipacaoEncontro` separam fila, confirmação
  e resultado real; os writes passam por services transacionais.
- Somente `CONCLUIU` em Escalada ou ESPPA pode criar `PerfilAlpinista`.
  Confirmação, falta, desistência, AVC e Acampamento não criam perfil, e
  nenhum fluxo da etapa cria `Frequencia`.
- O cutover lógico removeu a ativação implícita causada pelo vínculo legado,
  preservando temporariamente tabela, rotas, payloads e históricos antigos
  sem dual-write ou backfill heurístico.
- A regressão final aprovou 296/296 testes no PostgreSQL 16 descartável,
  inclusive os dois cenários reais de concorrência, e confirmou migrations
  aplicáveis até `core.0029_expand_inscricao_convite_participacao`.
- 1B.3D.3 concluiu Equipes e Trabalho em Encontro. Templates, snapshots,
  roles, `TrabalhoEncontro`, reuniões preparatórias, presença, autorização
  contextual e elegibilidade foram implementados sem misturar convite,
  alocação e trabalho realizado.
- Novos writes passam por services transacionais. A API canônica exige escopo
  de Encontro, mantém avisos explícitos e aplica default deny como política de
  base. Suporte, Diretoria e Fichas recebem somente as capacidades de Equipes
  expressamente concedidas para cada operação, sem liberação geral baseada no
  papel; saúde permanece fora do domínio.
- Somente `TrabalhoEncontro(status=TRABALHOU)` alimenta `historico_equipes`.
  Rotas e tabelas antigas permanecem temporariamente disponíveis, sem
  dual-write, backfill heurístico ou inferência de trabalho concluído.
- A regressão final aprovou 381/381 testes no PostgreSQL 16 descartável,
  inclusive os cinco cenários reais de concorrência da D.3C. A cadeia limpa de
  migrations foi validada até `core.0032_vinculousuariopessoa`; o cluster de
  teste foi removido ao final.
- Permanecem futuros o frontend canônico de equipes, a reconciliação e remoção
  física do legado, a fonte definitiva de atividade, saúde contextual e regras
  adicionais de AVC/Acampamento.
- 1B.3D.4 concluiu Formação em Encontros. O catálogo fixo em código contém
  nove palestras compartilhadas por Escalada/ESPPA e onze bate-papos de AVC;
  Acampamento permanece sem conteúdo deste domínio.
- `SessaoFormativa` e `PalestranteSessao` preservam snapshots, múltiplos
  palestrantes internos/externos e realização efetiva. O histórico canônico
  deriva somente de sessão `REALIZADA` e Alpinista que `MINISTROU`.
- A API canônica restringe gestão a Formação, Diretoria e Suporte, com Fichas
  somente leitura e default deny para os demais papéis. A regra do AVC exige
  palestrante Alpinista trabalhando no mesmo Encontro.
- `Palestra`, `historico-palestras` e o filtro legado permanecem disponíveis
  para compatibilidade de leitura, sem dual-write, conversão ou backfill
  automático. Consumidores frontend e remoção física permanecem débitos.
- A regressão final aprovou 429/429 testes no PostgreSQL 16.15 descartável,
  incluindo os dois cenários concorrentes, e validou migrations até
  `core.0033_expand_sessoes_formativas`. A baseline SQLite permaneceu OK com
  9 skips PostgreSQL esperados; o cluster temporário foi removido.
- 1B.3D.5 concluiu MME e Propostas de Violeiros. Múltiplas propostas por
  Encontro preservam cinco posições vigentes, histórico de substituições e
  disponibilidade derivada da escala oficial, sem reservar Pessoas ou copiar
  o estado de `TrabalhoEncontro`.
- A API canônica permite gestão a MME, Diretoria e Suporte. Fichas possui
  leitura e aproveitamento oficial, que cria somente
  `ConviteEncontro(TRABALHAR)`; confirmação, alocação e trabalho realizado
  continuam exclusivamente no fluxo da D.3.
- Propostas não criam histórico de trabalho, `Frequencia`,
  `PerfilAlpinista`, saúde ou Formação. O legado musical e de Violeiros foi
  preservado sem dual-write, backfill heurístico ou remoção física.
- A regressão final aprovou 490/490 testes no PostgreSQL 16.15 descartável,
  incluindo os cinco cenários concorrentes, e validou migrations até
  `core.0034_expand_propostas_violeiros`. A baseline SQLite permaneceu OK com
  14 skips PostgreSQL esperados; o cluster temporário foi removido.
- 1B.3D.6 concluiu o Calendário Institucional de Encontros como projeção
  canônica, sem duplicar `Encontro`. Entregou visões mensal/anual, navegação,
  filtros, responsividade, drawer, comandos protegidos e Agenda integrada à
  página canônica com Dias, Preparatórias e Avaliação.
- Datas em `EM_AGENDAMENTO` são provisórias e marcadas com `*`; `AGENDADO`
  oficializa a agenda. Reprogramações oficiais preservam versões, o lifecycle
  permanece manual e conflitos são consultivos.
- A exportação pública/interna suporta mês mensal, ano em 12 páginas mensais
  e anual resumido Modelo B. Publicações preservam snapshot, PDF privado,
  SHA-256 e metadados; republicações coexistem e preview não cria histórico.
- O checkpoint real em PostgreSQL 16 aprovou 6/6 cenários concorrentes sem
  acessar `sia_dev`. Na regressão final, a única falha da bateria backend foi
  a referência antiga da logo, corrigida de forma localizada e validada no
  teste isolado e no módulo de exportação (22/22). O frontend aprovou 131/131
  testes, TypeScript e build Webpack; ESLint ficou sem erros e com dois
  warnings preexistentes de Alpinistas.
- Os checks Django e de models foram aprovados. A cadeia expansiva da D.6 vai
  de `core.0035_diaencontro_data_index` a
  `core.0038_calendario_publicacao_layout`, com `0037` antes de `0038`.
- Permanecem explícitos o risco de arquivo órfão numa interrupção abrupta
  entre storage e commit, sem atomicidade distribuída, e a inexistência do
  domínio de Eventos; a extensibilidade conceitual não representa integração.
- Após a conclusão da D.6, o projeto iniciou o Roadmap Re-baseline e a
  implementação R.3I. O estado corrente dessa execução está consolidado na
  seção específica acima.

## Histórico — Fase 0

| Etapa | Objetivo | Principais entregas | Status |
|---|---|---|---|
| 0A | Segurança e configuração | Secrets removidos do código; DEBUG, hosts, CORS e CSRF configuráveis; ambientes locais ignorados. | Concluída |
| 0B | Ambiente e dependências | Requirements reproduzíveis; versões Python/Node estabilizadas; ESLint, Tailwind e build corrigidos. | Concluída |
| 0C | Base de regressão | Suíte inicial, settings isolados de teste e piso para prevenir regressões. | Concluída |
| 0D | Dados | Status canônicos; CPF nullable, único e normalizado; atomicidade e dashboard estabilizados. | Concluída |
| 0E | Autorização e privacidade | Roles oficiais, default deny, summary/full, domínios especializados, mídia protegida, auditoria e admin técnico separado. | Concluída |
| 0F | Autenticação | JWT via BFF, cookies HttpOnly, CSRF double-submit, Origin exata, rotação, blacklist, logout e guards. | Concluída |
| 0G | Integração frontend/API | Paginação, formulários, payloads, capabilities, summary/full, dashboard, tipos e erros alinhados. | Concluída |
| 0H | PostgreSQL e legado | Schema legado auditado, `core/legacy` criado e PostgreSQL descartável validado sem antecipar migração real. | Concluída |
| 0I | Débitos técnicos | Allowlists, remoção de PII em stdout, atomicidade, limpeza de permissão morta e casos-limite estabilizados. | Concluída |
| 0J | Gate final | Segurança, sessão, autorização, privacidade, dados, mídia, legado, infraestrutura, documentação e regressão aprovados. | Concluída |

O fechamento histórico consolidado está em `docs/PHASE_0_CLOSURE.md`.

## Decisões fechadas

### Alpinista

- Um novo Alpinista nasce com status `pendente`.
- Edição no frontend usa `PATCH`.
- E-mail e telefone são obrigatórios no contrato atual.
- CPF é opcional, normalizado e único quando informado.
- CPF inválido ou duplicado é rejeitado.
- Campos opcionais podem ser limpos com `null` onde o contrato permite.
- Neurodivergência `false` limpa o tipo associado.
- Sacramentos preservam estado tri-state: `true`, `false` ou `null`.
- Papéis de gestão recebem perfil full; demais papéis reconhecidos recebem
  summary.
- A foto é protegida e não é publicada diretamente por `/media`.

### Encontro

- Tipos atuais: `Escalada`, `AVC`, `Esppa` e `Acampamento`.
- O lifecycle administrativo inclui `em_agendamento`, `agendado`,
  `em_preparacao`, `em_andamento`, `finalizado`, `adiado` e `cancelado`.
- O contrato legado de escrita da API permanece limitado a `em_agendamento`
  e `agendado`; os novos fluxos de lifecycle pertencem ao service layer.
- `status_encontro` permanece uma projeção temporal legada e não deve ser
  interpretado como status administrativo.
- Suporte, Diretoria e Fichas recebem full e podem gerir Encontros.
- Comunicação recebe summary e usa a galeria dedicada.
- Participações e funções permanecem recursos próprios e protegidos.

### Calendário Institucional

- A fatia de Encontros está implementada como projeção dos objetos reais,
  não como segunda base de dados. Criar pelo Calendário ou pelo módulo de
  origem alcança o mesmo `Encontro`.
- A Agenda combina Dias, Preparatórias e Avaliação em ordem cronológica.
  Agendas oficiais são versionadas e podem conter dias não consecutivos.
- Todos os papéis de negócio reconhecidos possuem leitura. Diretoria e
  Suporte possuem gestão; o superuser é bypass técnico separado. As operações
  são protegidas no backend.
- PDFs públicos e internos usam WeasyPrint 70, A4 paisagem e o símbolo
  oficial em `backend/core/static/core/branding/logo-escalada.svg`. Arquivos
  publicados permanecem em storage privado e têm download autenticado.
- A visualização pelo calendário não amplia a permissão no objeto de origem.
- Referência normativa:
  [[decisions/ADR-001-calendario-institucional]].

### Dashboard

- Usa agregados calculados pelo backend.
- Nunca infere totais a partir da primeira página de um recurso paginado.
- Não exibe métricas falsas nem “últimas inscrições” inventadas.
- Está disponível para Suporte, Diretoria, Fichas e superuser técnico.

### Autenticação e sessão

- O browser conversa com o BFF do Next.js, não diretamente com Django.
- JWT access e refresh ficam em cookies HttpOnly.
- Refresh usa rotação e blacklist do token anterior.
- `/api/auth/me` fornece a identidade mínima e os papéis reconhecidos.
- O guard diferencia ausência de sessão de identidade autenticada sem role.
- CSRF usa double-submit e validação exata de `Origin`.
- `SIA_APP_ORIGIN` é a origem canônica; aliases de tunnel não são
  intercambiáveis.

## Baseline de testes

Baseline integral final validado na 0J:

| Verificação | Resultado |
|---|---|
| Backend | 192/192 testes passando |
| Frontend | 104/104 testes passando em 9 arquivos |
| Lint | 0 erros; 2 warnings justificados |
| TypeScript | PASS |
| Build Next.js | PASS |
| Django check | PASS |
| Migrations | Nenhuma pendente |

Os dois warnings são de `no-img-element` nas imagens protegidas de
Alpinistas. A decisão atual evita encaminhar cookies de autenticação a um
otimizador de imagens sem um contrato explícito para isso.

## Infraestrutura de desenvolvimento

- Notebook Ubuntu dedicado.
- Acesso de desenvolvimento por VS Code Remote SSH.
- PostgreSQL local no servidor.
- Serviços systemd: `sia-backend.service`, `sia-frontend.service` e
  `sia-tunnel.service`.
- DevTunnel persistente para acesso ao frontend.
- A URL corrente é configuração local e não deve ser documentada ou
  hardcoded.
- `.env`, `.env.local` e arquivos locais do tunnel permanecem fora do Git.

## Resultado da 0I

- Serializers remanescentes usam allowlists explícitas sem mudar contratos.
- O signal de participação não imprime mais o nome do Alpinista em stdout.
- `HasRecognizedSiaRole`, sem uso, foi removido.
- Remoção em lote de encontristas é atômica e possui teste de rollback.
- A seleção da função Encontrista é determinística mesmo diante de duplicatas.
- O histórico reconhece “Coordenador dos Dirigentes” sem diferenciar case.
- Comentários comprovadamente obsoletos de settings foram corrigidos.
- Fluxos de mídia agrupam banco e auditoria em transação, preservam o arquivo
  anterior em rollback e removem novo upload quando a transação falha.

## Resultado da 0J

- Gate final aprovado sem falhas críticas ou altas sem mitigação.
- Um bug de contrato no detalhe gerenciado de Encontro foi corrigido: funções
  e participações não paginadas agora são consumidas como listas diretas.
- O backend preservou listas diretas nesses endpoints e dois testes de regressão
  foram adicionados ao frontend.
- Smoke pelo BFF local validou login, sessão, dashboard, Alpinistas, Encontros,
  logout e rejeição de Origin incorreta, sem deixar dados temporários.
- O smoke externo não foi executado porque a credencial local do DevTunnel
  expirou; a unit permanece habilitada, mas requer novo login e inicialização
  antes da próxima validação remota. Essa pendência operacional não bloqueia a
  remodelagem de domínio da Fase 1.

## Invariantes herdadas da Fase 0

A modelagem e a implementação da Fase 1 devem preservar:

1. Autorização default deny.
2. Superuser técnico separado das roles de negócio.
3. Contratos Alpinista summary/full como fronteira de privacidade.
4. O browser sem acesso ou manipulação de JWT.
5. O BFF do Next.js como fronteira entre browser e backend.
6. Access e refresh em cookies HttpOnly.
7. CSRF double-submit com comparação exata de Origin.
8. Ausência de rota pública para `/media`.
9. Semântica HTTP de `400`, `401`, `403`, `404` e `405`.
10. Paginação sem assumir que a primeira página representa todo o dataset.
11. Migrations incrementais, revisáveis e coerentes com dados existentes.
12. Atomicidade em operações com múltiplas escritas.
13. Preservação de histórico durante a remodelagem.
14. `core/legacy` como fonte de transformação, nunca como modelo-alvo.
15. O baseline de testes da Fase 0, salvo redução explicitamente justificada.

## Manutenção operacional

Tokens expirados da blacklist devem ser removidos periodicamente com:

```bash
cd backend
./.venv/bin/python manage.py flushexpiredtokens
```

A periodicidade pertence à operação do ambiente; a 0I não adiciona scheduler.

## Débitos aceitos ao fim da Fase 0

Esses itens formam backlog conhecido e não bloqueiam a Fase 1.

| Débito | Risco atual | Motivo do deferimento | Gatilho futuro |
|---|---|---|---|
| Logging técnico estruturado | Baixo: diagnóstico descentralizado. | Instância única e auditoria funcional. | Centralização de logs ou observabilidade. |
| Reconciliação periódica de mídia | Baixo: órfãos em falha externa abrupta. | Compensação transacional cobre os fluxos atuais. | Storage remoto ou operação crítica. |
| Refresh distribuído | Baixo: coordenação somente por processo. | BFF executa em uma instância. | Escala horizontal. |
| Duração absoluta máxima de sessão | Médio: ausência de limite adicional ao ciclo dos tokens. | Política formal ainda não definida. | Requisito de segurança ou operação. |
| Agendamento de `flushexpiredtokens` | Baixo: crescimento da blacklist. | Rotina pode ser executada manualmente no ambiente atual. | Operação contínua ou volume relevante. |
| Dois warnings `no-img-element` | Baixo: custo potencial de performance. | Imagens protegidas exigem sessão; otimização não pode vazar cookies. | Loader autenticado com contrato seguro. |
| Unicidade semântica da função Encontrista | Baixo: duplicatas possíveis, com seleção determinística. | Regra de domínio ainda não fechada. | Decisão de domínio na Fase 1. |
| Renovação da credencial DevTunnel | Baixo e operacional: smoke remoto pode ficar indisponível. | Credencial pertence ao ambiente, não ao código. | Expiração ou falha de autenticação do tunnel. |

## Fase 1 — direção de modelagem

A Fase 1 avança pela modelagem do domínio e por migrations incrementais, não
pela implementação isolada de telas. O schema definitivo ainda não está
definido.

Direções conhecidas:

- Grupo pós-encontro como entidade de domínio e preservação do histórico de
  grupo.
- Paróquia e Região Administrativa como conceitos explícitos.
- Status e histórico de vínculo.
- Separação entre pessoa/Alpinista, inscrição e participação.
- Ciclo de Encontros, funções e equipes.
- Regras advisory e explicáveis em vez de hard blocks indevidos.
- Palestras e seus históricos.
- Eventos e evolução futura da área Meu SIA.
- Requisitos e processos LGPD.
- Migração final dos aproximadamente 3000 registros somente depois de domínio,
  mappings e profiling estarem estáveis.
