# Roadmap Re-baseline

## Status

R.1 concluída e validada humanamente. R.2 concluída documentalmente em
2026-10-07. R.3A concluiu a auditoria do gap entre o domínio atual de
Encontros e o frontend operacional; R.3 permanece em andamento e aguarda
checkpoint humano de produto. Este documento não altera, substitui ou
renumera o roadmap.

## Objetivo

Revisar o roadmap histórico após a expansão da Fase 1, separando:

- planejamento histórico;
- estado atual;
- produto realmente resolvido;
- lacunas;
- decisões futuras.

## Etapas

- **R.1 — Auditoria do roadmap histórico:** reconstrói evidências e lacunas;
  não altera o roadmap.
- **R.2 — Planejado × implementado × faltante:** compara os planos com o
  estado observável; não redesenha arquitetura.
- **R.3 — Revisão de maturidade:** avalia a maturidade do produto atual.
- **R.4 — Checkpoint de produto/arquitetura:** exige decisões humanas.
- **R.5 — Roadmap v2:** consolida o novo roadmap.

R.2 somente deve começar depois da aprovação humana da R.1.

## Critério de evidência

- **A — Histórica explícita:** documento versionado atribuía diretamente o
  objetivo ou tema à fase.
- **B — Histórica conversacional validada:** informação recuperada das
  conversas originais e validada humanamente pelo usuário, externa ao Git.
- **C — Atual:** documento atual comprova que o domínio ou a capacidade existe,
  sem provar que pertencia ao plano original daquela fase.
- **D — Inferência:** há semelhança temática, mas falta texto que autorize
  tratá-la como intenção histórica.

Os nomes e as intenções das Fases 0–10 foram validados humanamente a partir do
histórico conversacional original do projeto. A busca dirigida na
documentação atual e no histórico Git continua sem localizar um roadmap
versionado que os consolide. A validação conversacional permite reconstruir a
intenção histórica, mas não deve ser apresentada como evidência existente no
repositório.

## Fontes auditadas

### Documentação atual

- `AGENTS.md` e `docs/00_HOME.md`;
- `docs/PROJECT_STATE.md` e `docs/PHASE_0_CLOSURE.md`;
- `docs/ARCHITECTURE.md` e `docs/AUTHORIZATION_MATRIX.md`;
- `docs/decisions/ADR-001-calendario-institucional.md`;
- documentos diretamente relacionados em `docs/domain/`;
- workplans `PHASE_1B_D2.md` a `PHASE_1B_D6.md`.

### Histórico Git dirigido

- `271a01d` — primeira versão persistente de `PROJECT_STATE`, ainda durante a
  Fase 0, com a direção então conhecida da Fase 1;
- `1989e99` — fechamento da Fase 0 e liberação formal da Fase 1;
- commits documentais e funcionais de `6940877` a `bab3a6d`, usados somente
  para confirmar a expansão factual da Fase 1;
- buscas por `roadmap`, `Fase 2` a `Fase 10` e pelos nomes temáticos em
  documentos atuais, arquivos historicamente versionados e mensagens de
  commit.

Não foi localizado no Git um artefato anterior que descreva explicitamente o
roadmap completo 0–10.

### Validação humana externa ao Git

O usuário validou os nomes e as intenções do roadmap 0–10 com base no histórico
das conversas originais do projeto. Essa fonte é registrada como **evidência
histórica conversacional / validação humana externa ao Git**. Quando existe
documentação adicional para um tema, ela é citada separadamente e não muda a
natureza da validação conversacional.

Para Comunicação, o usuário também confirmou referência documental externa
sobre WhatsApp/e-mail, convites, confirmações, lembretes e notificações. Para
Relatórios, confirmou referência documental externa sobre Excel/PDF,
autorização e minimização. Esses artefatos não foram localizados no corpus
versionado auditado e, portanto, não são classificados como evidência Git.

## R.1 — Auditoria histórica

### Matriz histórica 0–10

| Fase | Nome histórico | Objetivo originalmente documentado | Evidência | Sobreposição atual observável | Lacunas |
|---|---|---|---|---|---|
| 0 | Estabilização | Segurança, configuração/ambiente, testes, consistência, infraestrutura e base segura para remodelagem. | **A:** `PHASE_0_CLOSURE`, `PROJECT_STATE`, commit `1989e99`; **B:** validação humana. | Segurança/configuração, ambiente, regressão, dados, autorização/privacidade, JWT/BFF, integração, PostgreSQL/legado e gate 0A–0J estão documentados. | Nenhuma fonte anterior à subdivisão 0A–0J foi localizada para dizer se esse detalhamento já fazia parte do plano original. |
| 1 | Remodelagem | Remodelar domínio e mappings antes da migração/cutover definitivo do legado. | **A:** `PROJECT_STATE` no commit `271a01d` e fechamento `1989e99`; **B:** validação humana. | Pessoa, Grupo/Frequência, lifecycle e Agenda de Encontros, participação, equipes/trabalho, Preparatórias, Formação, MME e Calendário foram documentados dentro da Fase 1. | Não há um plano-mestre versionado que fixe a decomposição original completa da Fase 1 ou o limite originalmente pretendido para 1B.3D. |
| 2 | Pessoas | Cadastro de Pessoas/Alpinistas, histórico, vínculos e Grupos. | **B:** validação humana externa ao Git; **C:** `PROJECT_STATE` registra esses domínios na Fase 1. | Existe capacidade atual relacionada a Pessoa/Alpinista, perfil, Grupo e histórico de vínculo. | Permanecem por delimitar, nas etapas seguintes, as fronteiras entre o que a Fase 1 implementou e o produto originalmente pretendido. |
| 3 | Encontros | Inscrições, participação e funcionamento/lifecycle dos Encontros. | **B:** validação humana externa ao Git; **C:** ADR-001, documentos de domínio e workplans D.2–D.6. | Existem lifecycle, calendários/dias, inscrição, convite, participação, trabalho, formação, MME e Calendário Institucional de Encontros. | A fronteira exata entre as entregas da Fase 1 e o produto histórico da Fase 3 ainda precisa ser comparada, sem julgamento nesta R.1. |
| 4 | Equipes | Equipes, funções e alocação/trabalho nos Encontros. | **B:** validação humana externa ao Git; **C:** `ENCOUNTER_WORK` e `PHASE_1B_D3`. | Templates, snapshots, roles, `TrabalhoEncontro`, Preparatórias, presença, elegibilidade e autorização contextual existem na documentação atual. | A fronteira exata entre as entregas da Fase 1 e o produto histórico da Fase 4 permanece para comparação posterior. |
| 5 | Sugestões | Motor/capacidades de sugestões explicáveis para apoiar decisões, especialmente formação e alocação de equipes. | **B:** validação humana externa ao Git; **C:** `ENCOUNTER_MME` e `PHASE_1B_D5`. | O sistema documenta propostas explicáveis de Violeiros e capacidades advisory de trabalho. | A correspondência exata entre as capacidades atuais e o motor de sugestões pretendido será examinada somente nas etapas seguintes. |
| 6 | Pastas / Permissões | Capacidades, acessos e permissões por papel/área. | **B:** rótulo e intenção validados humanamente; **C:** `AUTHORIZATION_MATRIX`, Fase 0 e autorizações contextuais da Fase 1. | Default deny, roles, summary/full, capabilities e permissões contextuais estão documentados no sistema atual. | O significado e a necessidade atual de “Pastas” ainda não estão definidos. |
| 7 | Eventos | Eventos, participantes/equipes e integração institucional futura, inclusive com calendário quando pertinente. | **B:** validação humana externa ao Git; **C:** a matriz documenta CRUD legado, enquanto ADR-001 e D.6 reservam o novo domínio/integração. | Há API/capacidade legada autorizada para Eventos; a integração de Eventos ao novo Calendário não existe. | Legado atual e futuro domínio de Eventos não podem ser tratados automaticamente como a mesma solução. |
| 8 | Comunicação | Comunicação institucional futura; referência documental externa sustenta WhatsApp/e-mail, convites, confirmações, lembretes e notificações como escopo futuro. | **B:** intenção conversacional validada e referência documental externa, separadas da evidência Git; **C:** matriz atual para a role. | A role Comunicação possui leitura summary de Alpinista/Encontro e gestão de fotos/galeria conforme a matriz atual. | A relação exata entre a role/capacidades atuais e o produto futuro de comunicação permanece para comparação posterior. |
| 9 | Relatórios | Relatórios, exports e indicadores autorizados; referência documental externa trata Excel/PDF, autorização e minimização. | **B:** intenção conversacional validada e referência documental externa, separadas da evidência Git; **C:** capacidades atuais; **D:** correspondência exata dessas capacidades com a fase. | Existem dashboard com agregados reais, PDFs autorizados do Calendário e consulta protegida de logs. | As fronteiras exatas do produto de relatórios e sua relação com exports já especializados permanecem para comparação posterior. |
| 10 | Produção | Migração/cutover do legado, deduplicação/limpeza, revisão de segurança, deploy e operação produtiva. | **B:** validação humana externa ao Git; **C:** `ARCHITECTURE`, `PHASE_0_CLOSURE` e débitos operacionais atuais. | Há ambiente de desenvolvimento reproduzível, serviços systemd, checks/build e requisitos operacionais documentados. | A fronteira entre preparação atual, migração do legado e operação produtiva ainda precisa ser levantada nas etapas seguintes. |

Nenhuma linha da matriz classifica atendimento, maturidade ou estado formal de
uma fase histórica. As sobreposições apenas registram capacidades atuais.

### Fase 0 — evidência reconstruída

- **Objetivo explícito:** estabilizar a base antes da remodelagem.
- **Escopo explícito posterior:** 0A segurança/configuração; 0B ambiente e
  dependências; 0C regressão; 0D dados/atomicidade/dashboard; 0E autorização,
  privacidade, mídia e auditoria; 0F autenticação; 0G integração; 0H
  PostgreSQL/legado; 0I débitos; 0J gate final.
- **Dependência mencionada:** a liberação da Fase 1 dependia do gate 0J.
- **Evolução documental:** a primeira versão persistente do estado já
  apresentava 0A–0J; não foi encontrada uma versão anterior que permita
  separar o significado mais antigo de “Estabilização” dessa decomposição.

### Fase 1 — intenção e expansão factual

- **Intenção histórica explícita:** remodelar domínio e estabilizar mappings
  antes do loader/migração final do legado, preservando as invariantes da
  Fase 0.
- **Direções registradas no início:** Grupo e histórico territorial;
  Pessoa/Alpinista, inscrição e participação; regras por tipo de Encontro;
  sugestões advisory de equipe; Meu SIA; LGPD; loader posterior ao profiling.
- **Expansão documentada:** `Pessoa` e backfill inicial; Grupo/Frequência;
  lifecycle e calendários de Encontro; Inscrição/Convite/Participação;
  Equipes/Trabalho; Preparatórias/presença; autorização contextual;
  Formação; MME/Propostas; Calendário Institucional, Agenda e publicação.
- **Decisões posteriores relevantes:** separação entre Pessoa e perfil;
  lifecycle manual; históricos derivados de fatos efetivos; compatibilidade
  incremental sem backfill heurístico; calendário como projeção dos domínios;
  autorização contextual sem ampliar roles globais.
- **Dependência mencionada:** preservação integral das fronteiras de
  segurança, privacidade, contratos e compatibilidade estabilizadas na Fase 0.

Essa expansão se sobrepõe tematicamente aos nomes fornecidos para Fases 2–6,
mas nenhum documento localizado afirma que essas fases foram formalmente
substituídas, absorvidas ou satisfeitas.

### Fases 2–10 — limite da reconstrução

A validação humana externa ao Git recuperou nomes e intenções das Fases
2–10. O repositório fornece evidência atual de capacidades relacionadas, mas
não um plano-mestre versionado com decomposição, dependências, critérios de
saída ou limites detalhados. A matriz registra a intenção validada sem
transformar correspondência temática em avaliação de atendimento.

## Sobreposições observadas

- Pessoa/Alpinista, Grupo e vínculos aparecem hoje dentro da Fase 1 e se
  relacionam tematicamente ao nome “Pessoas”.
- O conjunto D.1–D.6 trata extensamente Encontros dentro da Fase 1.
- D.3 trata Equipes e Trabalho; D.5 trata propostas do MME. A intenção
  histórica de Sugestões foi validada, mas o grau de correspondência com D.5
  permanece para as etapas seguintes.
- Autorização transversal nasceu na Fase 0 e ganhou regras contextuais na
  Fase 1, sobrepondo-se tematicamente a “Permissões”.
- A base atual possui capacidades legadas de Eventos e da role Comunicação,
  mas isso não demonstra o objetivo histórico integral das Fases 7 e 8.
- Dashboard e logs existem; vinculá-los ao objetivo original de “Relatórios”
  seria inferência.
- Infraestrutura de desenvolvimento e requisitos operacionais existem;
  vinculá-los ao objetivo original de “Produção” também seria inferência.

## Divergências históricas

1. A validação conversacional confirma o roadmap 0–10, mas a documentação
   versionada localizada formaliza somente a Fase 0, a Fase 1 e suas
   subdivisões.
2. A direção inicial da Fase 1 no commit `271a01d` era aberta e mais curta;
   documentos posteriores incorporaram vários domínios de Encontro, MME e o
   Calendário Institucional. Não há ato documental dizendo que essa expansão
   alterou formalmente as Fases 2–6.
3. `AUTHORIZATION_MATRIX.md` documenta uma API legada de Eventos existente,
   enquanto ADR-001 e a D.6 tratam o novo domínio/integração de Eventos como
   futuro. As fontes podem estar descrevendo camadas distintas, mas não há
   documento histórico que fixe a relação com a Fase 7.
4. O rótulo histórico da Fase 6 é “Pastas / Permissões”. A documentação
   atual sustenta permissões e capacidades, mas não esclarece a relevância
   atual de “Pastas”.
5. Não foram encontradas versões concorrentes do objetivo das Fases 2–10; o
   problema é ausência de evidência versionada no Git, agora complementada
   por validação humana externa.

## Lacunas para validação humana

1. Qual era o significado operacional de “Pastas” na Fase 6 e essa parte do
   rótulo histórico ainda representa uma necessidade atual?
2. Quais são as fronteiras exatas entre funcionalidades entregues dentro da
   Fase 1 e o produto pretendido pelas Fases 2–10? Essa comparação não deve
   pressupor absorção ou atendimento.
3. Como separar, na comparação futura, o CRUD legado de Eventos do novo
   domínio de Eventos, seus participantes/equipes e sua integração
   institucional?

Essas questões permanecem registradas para as etapas futuras e não serão
resolvidas nesta R.1. Questões de correspondência, prioridade, maturidade e
nova arquitetura pertencem aos blocos posteriores.

## R.2 — Planejado × implementado × faltante

### Critério de classificação

- **IMPLEMENTADO:** a capacidade identificável existe hoje.
- **IMPLEMENTADO EM OUTRO BLOCO:** existe, mas foi entregue fora da fase
  histórica à qual estava associada.
- **PARCIAL:** uma parte concreta existe e outra parte prevista não foi
  localizada.
- **NÃO LOCALIZADO:** não foi encontrada evidência atual suficiente.
- **LEGADO / A REVALIDAR:** existe implementação antiga que não pode ser
  tratada automaticamente como o domínio futuro pretendido.

Os estados descrevem somente existência e cobertura estrutural. Não avaliam
qualidade, suficiência de produto, UX ou maturidade. Débitos técnicos não
mudam por si só o estado de uma capacidade existente.

### Fase 0 — Estabilização

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Segurança da aplicação | IMPLEMENTADO | 0A, 0E, 0F e 0J | `PHASE_0_CLOSURE`; `ARCHITECTURE` | Secrets, JWT/BFF, CSRF, mídia e gate estão documentados. |
| Configuração por ambiente | IMPLEMENTADO | 0A | `PHASE_0_CLOSURE`; settings | Debug, hosts, CORS, Origin e secrets usam ambiente. |
| Ambiente e dependências reproduzíveis | IMPLEMENTADO | 0B | `PHASE_0_CLOSURE`; `README.md` | Versões e dependências possuem fontes versionadas. |
| Baseline automatizado de testes | IMPLEMENTADO | 0C e 0J | `PHASE_0_CLOSURE` | Backend, frontend, checks e build compõem o gate registrado. |
| Consistência de dados e contratos | IMPLEMENTADO | 0D, 0G e 0I | `PROJECT_STATE`; `PHASE_0_CLOSURE` | CPF, status, paginação, payloads e atomicidade foram tratados. |
| Autorização e privacidade | IMPLEMENTADO | 0E e 0J | `AUTHORIZATION_MATRIX`; `ARCHITECTURE` | Default deny, summary/full e superuser separado estão documentados. |
| Infraestrutura de desenvolvimento | IMPLEMENTADO | 0B e infraestrutura atual | `PROJECT_STATE`; `ARCHITECTURE` | Notebook Ubuntu, PostgreSQL local, Remote SSH e systemd. |
| Observabilidade técnica | PARCIAL | Auditoria funcional e logs atuais | `PROJECT_STATE`; `LogSistema` | Auditoria existe; logging técnico estruturado permanece como débito. |

### Fase 1 — Remodelagem

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Pessoa e PerfilAlpinista | IMPLEMENTADO | 1B.3B | `PROJECT_STATE`; models/migration `0025` | Pessoa foi separada do perfil. |
| Grupo | IMPLEMENTADO | 1B.3C | `PROJECT_STATE`; models | Inclui Paróquia, configuração, vínculo e coordenação. |
| Frequência | IMPLEMENTADO | 1B.3C | `PROJECT_STATE`; `Frequencia` | Registro pertence ao perfil e pode referenciar Grupo. |
| Lifecycle de Encontro | IMPLEMENTADO | 1B.3D.1 | `PROJECT_STATE`; services de Encontro | Lifecycle administrativo é separado da projeção legada. |
| CalendarioEncontro e DiaEncontro | IMPLEMENTADO | 1B.3D.1 | `PROJECT_STATE`; migration `0028` | Agendas oficiais possuem versões e dias explícitos. |
| Inscrição | IMPLEMENTADO | 1B.3D.2 | `ENCOUNTER_PARTICIPATION`; D.2 | Fila de Escalada/ESPPA separada de convite e resultado. |
| ConviteEncontro | IMPLEMENTADO | 1B.3D.2 | `ENCOUNTER_PARTICIPATION`; D.2 | Participar e trabalhar são finalidades explícitas. |
| ParticipacaoEncontro | IMPLEMENTADO | 1B.3D.2 | `ENCOUNTER_PARTICIPATION`; D.2 | Resultado efetivo usa Pessoa e estados próprios. |
| Equipes | IMPLEMENTADO | 1B.3D.3 | `ENCOUNTER_WORK`; D.3 | Templates e snapshots por Encontro existem. |
| TrabalhoEncontro | IMPLEMENTADO | 1B.3D.3 | `ENCOUNTER_WORK`; D.3 | Alocação e trabalho efetivo permanecem separados do convite. |
| Preparatórias | IMPLEMENTADO | 1B.3D.3 | `ENCOUNTER_WORK`; D.3 | Reuniões ordenadas pertencem ao Encontro. |
| Presença preparatória | IMPLEMENTADO | 1B.3D.3 | `ENCOUNTER_WORK`; D.3 | Presença referencia o trabalho no mesmo Encontro. |
| Autorização contextual | IMPLEMENTADO | 1B.3D.3 | `AUTHORIZATION_MATRIX`; D.3 | Coordenação Geral recebe capacidade contextual limitada. |
| Formação em Encontros | IMPLEMENTADO | 1B.3D.4 | `ENCOUNTER_FORMATION`; D.4 | Sessões, palestrantes e histórico derivado existem. |
| MME e propostas de Violeiros | IMPLEMENTADO | 1B.3D.5 | `ENCOUNTER_MME`; D.5 | Propostas e disponibilidade derivada são separadas da escala oficial. |
| Calendário Institucional | IMPLEMENTADO | 1B.3D.6 | `INSTITUTIONAL_CALENDAR`; D.6 | É projeção canônica da fatia de Encontros. |
| Agenda do Encontro | IMPLEMENTADO | 1B.3D.6 | `INSTITUTIONAL_CALENDAR`; D.6 | Reúne Dias, Preparatórias e Avaliação. |
| Exportação PDF | IMPLEMENTADO | 1B.3D.6 | D.6; service de exportação | Há modalidades mensal e anual, pública e interna. |
| Publicação e histórico imutáveis | IMPLEMENTADO | 1B.3D.6 | D.6; `PublicacaoCalendarioInstitucional` | Snapshot, arquivo privado, hash e autoria são persistidos. |
| Mappings, backfills e preparação do legado | PARCIAL | 1B.3B–D.6 e `core/legacy` | `PROJECT_STATE`; `ARCHITECTURE` | Houve backfill inicial e cutovers lógicos; loader e migração final não foram localizados. |

### Fase 2 — Pessoas

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Pessoa | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / 1B.3B | `Pessoa`; `PROJECT_STATE` | Entidade canônica existe. |
| PerfilAlpinista | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / 1B.3B–D.2 | `PerfilAlpinista`; D.2 | Perfil é separado de Pessoa e pode nascer por conclusão elegível. |
| Status ativo/inativo da Pessoa/Perfil | LEGADO / A REVALIDAR | `Alpinista.status` legado | `models.py`; `PROJECT_STATE` | O novo `Pessoa`/`PerfilAlpinista` não possui esse status. |
| Histórico da Pessoa/Alpinista | PARCIAL | Históricos derivados em D.2–D.5 | `PROJECT_STATE`; workplans | Há históricos de Encontro, Grupo, equipe e formação; não foi localizado um histórico geral único. |
| Grupo | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / 1B.3C | `Grupo`; `ConfiguracaoGrupo` | Grupo e configuração temporal existem. |
| Vínculo com Grupo | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / 1B.3C | `VinculoGrupo` | Datas de início/fim preservam histórico. |
| Frequência | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / 1B.3C | `Frequencia` | Capacidade estrutural existe. |
| Vínculo conjugal | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / 1B.3B | `VinculoConjugal` | Relação canônica entre duas Pessoas existe. |
| Outros vínculos familiares entre Pessoas | NÃO LOCALIZADO | — | Busca dirigida em models/docs | Responsável é dado associado, não vínculo Pessoa–Pessoa geral. |
| Dados de responsável | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / 1B.3B | `ResponsavelPessoa` | Nome, parentesco, telefone e principal existem. |
| Sacramentos | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / 1B.3B | `Pessoa` | Batismo, primeira comunhão e crisma preservam estado tri-state. |
| CPF e deduplicação | PARCIAL | Fase 0 e Fase 1 | validators, constraints e backfill | CPF é normalizado/único; deduplicação final do legado não foi localizada. |

### Fase 3 — Encontros

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Encontro canônico | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.1 | `PROJECT_STATE`; models | O model legado foi expandido com lifecycle canônico. |
| Lifecycle administrativo | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.1 | D.1; services | Permanece manual e separado de `status_encontro`. |
| Calendário e versionamento | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.1 | `CalendarioEncontro` | Reprogramações oficiais preservam versões. |
| Dias do Encontro | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.1 | `DiaEncontro` | Dias explícitos podem ser não consecutivos. |
| Inscrição | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.2 | `Inscricao` | Inscrição ativa é separada da edição do Encontro. |
| Convite | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.2 | `ConviteEncontro` | Confirmação pertence ao convite. |
| Participação/resultado | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.2 | `ParticipacaoEncontro` | Conclusão, falta e desistência são resultados. |
| Preparatórias | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | `ReuniaoPreparatoriaEncontro` | Pertencem ao Encontro e ao fluxo de trabalho. |
| Agenda agregada | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.6 | D.6; query service | Dias, Preparatórias e Avaliação são ordenados. |
| Avaliação de agenda | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.6 | `AvaliacaoEncontro` | Existe um item simples por Encontro. |
| Conflitos temporais consultivos | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.6 | D.6 | Conflitos avisam e não bloqueiam. |
| Publicação do Calendário | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.6 | D.6 | Publicação cobre a projeção institucional de Encontros. |

O domínio de Encontro é a fonte canônica; o Calendário Institucional é
uma projeção e uma interface sobre parte desse domínio.

### Fase 4 — Equipes

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Templates de equipe | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | `TemplateEquipeEncontro` | Templates são separados do histórico. |
| Snapshots de equipe | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | `EquipeEncontro` | Mudança no template não altera snapshot. |
| Funções/roles | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | `TemplateRoleEquipe`; `RoleEquipeEncontro` | Roles também são copiadas para o Encontro. |
| Alocação/membro | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | `TrabalhoEncontro` | Pessoa é alocada no contexto do Encontro. |
| Trabalho efetivamente realizado | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | `TrabalhoEncontro` e services | Estado distingue planejamento de trabalho realizado. |
| Histórico de trabalho | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | `historico_equipes`; D.3 | Deriva somente de trabalho efetivo. |
| Elegibilidade | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | evaluator de elegibilidade; D.3 | Produz bloqueios/avisos explícitos. |
| Disponibilidade consultiva | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3–D.5 | D.3; D.5 | Há avaliação advisory e disponibilidade derivada nas propostas. |
| Preparatórias e presença do trabalho | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | models/services da D.3 | Presença referencia `TrabalhoEncontro`. |

### Fase 5 — Sugestões

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Propostas específicas de Violeiros | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.5 | `ENCOUNTER_MME`; D.5 | É uma aplicação específica de apoio à decisão. |
| Disponibilidade derivada | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.5 | services da D.5 | Deriva da escala oficial e não reserva Pessoa. |
| Regras advisory de elegibilidade | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | evaluator da D.3 | Avisos e bloqueios possuem razões explícitas. |
| Explicabilidade das propostas/avisos | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3–D.5 | workplans D.3 e D.5 | Resultados consultivos expõem motivos. |
| Motor genérico de sugestões | NÃO LOCALIZADO | — | Busca dirigida em docs/código | Não foi localizada infraestrutura genérica reutilizável de sugestão. |

A existência das propostas do MME não é tratada como equivalência com a
Fase 5 inteira.

### Fase 6 — Pastas / Permissões

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Roles de negócio | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 | `roles.py`; matriz | Papéis reconhecidos são centralizados. |
| Default deny | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 | `permissions.py`; matriz | Ausência de regra resulta em negação. |
| Mapa de permissões por recurso/ação | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 e Fase 1 | `AUTHORIZATION_MATRIX`; permissions | Método/action e recursos especializados são mapeados. |
| Capabilities de apresentação | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 e D.6 | serializers/frontend | UI recebe capabilities sem substituir o backend. |
| Autorização contextual | IMPLEMENTADO EM OUTRO BLOCO | Fase 1 / D.3 | D.3; matriz | Escopo da Coordenação Geral é limitado ao Encontro. |
| Enforcement no backend | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 e Fase 1 | permissions/views/tests documentados | Operações protegidas não dependem da UI. |
| Enforcement no BFF | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 | `ARCHITECTURE` | Proxy usa allowlist e preserva autenticação/CSRF. |
| Suporte e Diretoria | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 e Fase 1 | matriz | São roles de negócio com capacidades explícitas. |
| Demais papéis/áreas | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 e Fase 1 | matriz | Fichas, MME, Formação, Eventos, Comunicação e outros estão mapeados. |
| Superuser técnico separado | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 | `ARCHITECTURE`; matriz | Não equivale a Suporte. |
| Pastas | NÃO LOCALIZADO | — | Busca dirigida em docs/código | Não há conceito atual inequívoco equivalente. |

### Fase 7 — Eventos

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| CRUD de Evento existente | LEGADO / A REVALIDAR | API/model legado | `Evento`; `AUTHORIZATION_MATRIX` | Model possui nome, data e local. |
| Participação em Evento existente | LEGADO / A REVALIDAR | API/model legado | `ParticipacaoEvento` | Relação usa `Alpinista` legado. |
| Novo domínio de Eventos | NÃO LOCALIZADO | — | ADR-001; D.6 | Documentos reservam essa modelagem para o futuro. |
| Equipes de Eventos no novo domínio | NÃO LOCALIZADO | — | Busca dirigida em docs/código | Nenhuma estrutura canônica nova foi localizada. |
| Integração institucional/Calendário | NÃO LOCALIZADO | — | `INSTITUTIONAL_CALENDAR` | Filtros existem desabilitados, sem dados simulados. |

### Fase 8 — Comunicação

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Role Comunicação, fotos e galeria | IMPLEMENTADO | Fase 0 / superfícies atuais | `AUTHORIZATION_MATRIX` | Role possui summary e gestão de foto/galeria. |
| Convites e confirmações internas | PARCIAL | Fase 1 / D.2 | `ConviteEncontro` e services | Fluxo funcional existe dentro do SIA, sem representar envio externo. |
| Envio real de e-mail | NÃO LOCALIZADO | — | Busca dirigida em código/docs | Campo de e-mail não constitui canal de envio. |
| Envio real por WhatsApp | NÃO LOCALIZADO | — | Busca dirigida em código/docs | Telefone/flag WhatsApp não constitui integração externa. |
| Lembretes | NÃO LOCALIZADO | — | Busca dirigida em código/docs | Nenhum scheduler ou fluxo de lembrete foi localizado. |
| Notificações institucionais | NÃO LOCALIZADO | — | D.5 as mantém fora de escopo | Avisos consultivos atuais não enviam notificações. |

### Fase 9 — Relatórios

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Dashboard e indicadores | IMPLEMENTADO | Fase 0 / estado atual | `PROJECT_STATE` | Usa agregados do backend e não infere totais de paginação. |
| Logs consultáveis | IMPLEMENTADO | Fase 0 | `LogSistema`; matriz | Leitura é protegida para Suporte/Diretoria. |
| PDFs do Calendário | IMPLEMENTADO | Fase 1 / D.6 | D.6 | Export específico, autorizado e minimizado. |
| Histórico de publicações | IMPLEMENTADO | Fase 1 / D.6 | `PublicacaoCalendarioInstitucional` | Preserva snapshot, PDF e metadados. |
| Plataforma geral de relatórios | NÃO LOCALIZADO | — | Busca dirigida em docs/código | Export do Calendário não é plataforma geral. |
| Exportação Excel | NÃO LOCALIZADO | — | D.6 exclui Excel | Nenhum export Excel foi localizado. |
| Outros relatórios formais autorizados | NÃO LOCALIZADO | — | Busca dirigida em docs/código | Históricos de domínio não foram classificados como relatórios gerais. |

### Fase 10 — Produção

| Capacidade histórica | Estado atual | Onde existe hoje | Evidência | Observação factual |
|---|---|---|---|---|
| Servidor, PostgreSQL e systemd | PARCIAL | Infraestrutura de desenvolvimento | `ARCHITECTURE`; `PROJECT_STATE` | Ambiente atual é servidor dedicado de desenvolvimento, não produção comprovada. |
| Migrations expansivas e backfill inicial | PARCIAL | Fase 1 | migrations `0025`–`0038`; workplans | Estruturas e um backfill inicial existem; migração final não foi localizada. |
| Controles de segurança | IMPLEMENTADO EM OUTRO BLOCO | Fase 0 | `PHASE_0_CLOSURE`; `ARCHITECTURE` | Há baseline de segurança aplicado. |
| Revisão final de segurança para produção | NÃO LOCALIZADO | — | Busca dirigida em docs | Gate 0J não é apresentado como aceite produtivo final. |
| Migração/cutover definitivo do legado | NÃO LOCALIZADO | — | `ARCHITECTURE`; `PROJECT_STATE` | `core/legacy` ainda não possui loader produtivo. |
| Deduplicação/limpeza final | NÃO LOCALIZADO | — | `PROJECT_STATE` | CPF único não equivale ao saneamento final dos dados legados. |
| Deploy produtivo real | NÃO LOCALIZADO | — | Busca dirigida em docs/repositório | Não foi localizada evidência de ambiente produtivo ativo. |
| Operação produtiva | NÃO LOCALIZADO | — | Débitos operacionais documentados | Rotinas atuais pertencem ao desenvolvimento/operação local. |
| Observabilidade técnica | PARCIAL | Auditoria e logs atuais | `PROJECT_STATE`; `LogSistema` | Logging estruturado/centralizado permanece como débito. |
| Backup e retenção operacionais | NÃO LOCALIZADO | — | D.6 registra necessidade de backup | Nenhuma automação/política produtiva foi localizada. |

### Resumo por fase

Na coluna **Implementado**, a contagem inclui `IMPLEMENTADO` e
`IMPLEMENTADO EM OUTRO BLOCO`. Os números contam capacidades das tabelas
acima; não constituem nota ou percentual de conclusão da fase.

| Fase | Implementado | Parcial | Não localizado | Legado/a revalidar | Principal sobreposição |
|---|---:|---:|---:|---:|---|
| 0 — Estabilização | 7 | 1 | 0 | 0 | Baseline transversal usado pelas fases seguintes |
| 1 — Remodelagem | 19 | 1 | 0 | 0 | Expandiu-se por domínios de Pessoas, Encontros, Equipes e Sugestões |
| 2 — Pessoas | 8 | 2 | 1 | 1 | Capacidades entregues sobretudo em 1B.3B–1B.3C |
| 3 — Encontros | 12 | 0 | 0 | 0 | Capacidades entregues em D.1–D.6 |
| 4 — Equipes | 9 | 0 | 0 | 0 | Capacidades entregues em D.3 e apoio de D.5 |
| 5 — Sugestões | 4 | 0 | 1 | 0 | Aplicações específicas em D.3/D.5, sem motor genérico localizado |
| 6 — Pastas / Permissões | 10 | 0 | 1 | 0 | Permissões distribuídas entre Fase 0 e autorização contextual da Fase 1 |
| 7 — Eventos | 0 | 0 | 3 | 2 | CRUD/participação legados separados do futuro domínio |
| 8 — Comunicação | 1 | 1 | 4 | 0 | Role/galeria atuais e convite interno não equivalem a canais externos |
| 9 — Relatórios | 4 | 0 | 3 | 0 | Dashboard/logs e export especializado do Calendário |
| 10 — Produção | 1 | 3 | 6 | 0 | Segurança e preparação técnica fora de um deploy produtivo comprovado |

## Capacidades absorvidas pela Fase 1

O termo “absorvidas” neste mapa significa apenas que a implementação foi
registrada dentro da Remodelagem; não elimina nem redefine a fase histórica.

| Capacidade | Fase historicamente associada | Onde apareceu |
|---|---|---|
| Pessoa e PerfilAlpinista | Fase 2 — Pessoas | 1B.3B e D.2 |
| Grupo, vínculos e Frequência | Fase 2 — Pessoas | 1B.3C |
| Lifecycle, agenda temporal e dias | Fase 3 — Encontros | D.1 |
| Inscrição, Convite e Participação | Fase 3 — Encontros | D.2 |
| Agenda agregada, conflitos e publicação | Fase 3 — Encontros | D.6 |
| Templates, equipes, roles, trabalho e presença | Fase 4 — Equipes | D.3 |
| Elegibilidade e avisos advisory | Fase 5 — Sugestões | D.3 |
| Propostas específicas do MME | Fase 5 — Sugestões | D.5 |
| Autorização contextual | Fase 6 — Pastas / Permissões | D.3 |

## Capacidades atuais fora do encaixe histórico claro

- Formação em Encontros possui domínio próprio na D.4, mas não foi citada
  explicitamente nas intenções históricas 0–10 recuperadas.
- Materiais e entregas possuem models e autorização atuais, sem fase
  histórica inequívoca na R.1.
- Galeria/fotos se relaciona à role Comunicação, mas não equivale ao produto
  histórico de comunicação institucional externa.
- O Calendário Institucional e sua publicação PDF cruzam Encontros e exports,
  sem precisar ser forçados exclusivamente para a Fase 3 ou a Fase 9.
- Dados de saúde existem associados a Pessoa, mas saúde não aparece como
  objetivo histórico autônomo no roadmap recuperado.

## Itens prioritários para revisão de maturidade na R.3

Os itens abaixo possuem implementação suficiente para permitir futura
observação de fluxos e uso. Esta lista não avalia nem prescreve correções:

- Pessoas, PerfilAlpinista, Grupos, vínculos e históricos;
- Encontros, lifecycle, inscrição, convite, participação e Agenda;
- Equipes, TrabalhoEncontro, elegibilidade, Preparatórias e presença;
- propostas específicas do MME e sua disponibilidade derivada;
- permissões globais/contextuais e sua aplicação backend/BFF/frontend;
- Calendário Institucional, exportação, publicação e histórico.

## Lacunas para validação humana após a R.2

1. Qual capacidade concreta o rótulo histórico “Pastas” representava e ela
   ainda é necessária?
2. Qual fronteira deve ser usada futuramente entre CRUD/participação legados
   de Eventos e o novo domínio com equipes e integração institucional?
3. A futura plataforma de Relatórios deve agregar os exports especializados
   existentes ou permanecer um produto separado? A R.2 apenas constatou ambos.
4. Quais evidências operacionais definirão “produção” para o SIA? O servidor
   atual está documentado como ambiente de desenvolvimento.

## Próximo checkpoint

Após aprovação humana da R.2: **R.3 — Revisão de maturidade**. A R.2 não
inicia testes manuais de produto, não prioriza implementações e não propõe o
Roadmap v2.

## R.3A — Gap frontend do domínio de Encontros

### Escopo e método

Auditoria estática, sem alteração ou teste empírico de dados, comparando a
documentação canônica de D.1–D.6 com models, services, serializers, views,
rotas, autorização, páginas, capabilities, navegação, proxy BFF, contratos e
testes frontend diretamente relacionados. Os achados descrevem o produto
observável; não classificam a maturidade da R.3 nem desenham a solução.

O diagnóstico central é uma divisão de gerações: Agenda e Calendário já usam
os comandos e a projeção canônicos de D.6, enquanto as abas Encontristas e
Equipes de Trabalho da página do Encontro continuam integralmente apoiadas em
`Alpinista`, `FuncaoEncontro` e `VinculoEncontroLegado`. As APIs canônicas de
D.2–D.5 existem no Django, porém não possuem interface e seus recursos raiz
nem sequer constam da allowlist atual do proxy BFF.

### Matriz principal

| Capacidade | Backend canônico | API/command | Frontend atual | Contrato frontend | Estado | Gap observado |
|---|---|---|---|---|---|---|
| Lifecycle do Encontro | `Encontro.status` e services de transição | Calendário expõe oficializar, reprogramar, adiar, novo planejamento e cancelar; iniciar preparação, iniciar Encontro e finalizar não estão expostos | Lista mostra status; página não oferece o fluxo completo nem muda para modo histórico | `/encontros/` legado e comandos `/calendario-institucional/` | PARCIAL | Faltam comandos operacionais para três transições e adaptação integral da página por estado. |
| Agenda canônica | `CalendarioEncontro`, `DiaEncontro`, Preparatórias e Avaliação | `GET /calendario-institucional/encontros/{id}/agenda/` | Seção Agenda na página e drawer do Calendário | Contrato agregado D.6 | ATUAL | A projeção canônica é consumida; não equivale aos demais fluxos do Encontro. |
| Inscrição | `Inscricao` | `POST /inscricoes-encontros/` | “Fila de Espera” lista `Alpinista.status=pendente` | `/alpinistas/?status=pendente` | LEGADO | Não representa inscrição por Pessoa/tipo, seu estado nem seu vínculo com convite. |
| Convite e resposta | `ConviteEncontro` | criação e `POST /convites-encontros/{id}/responder/` | “Confirmar selecionados” cria vínculo legado diretamente | `/encontros/{id}/efetivar-encontristas/` | LEGADO | Confirmação de convite não está representada; a mesma palavra descreve outra operação. |
| Resultado de participação | `ParticipacaoEncontro` por Pessoa/Encontro | `POST /resultados-participacoes-encontros/` | Nenhum fluxo localizado | — | AUSENTE | Não há registro ou histórico visual de `CONCLUIU`, `FALTOU` ou `DESISTIU`. |
| Participação antiga | `VinculoEncontroLegado`, mantido apenas por compatibilidade | CRUD `/participacoes-encontros/` e ações legadas no Encontro | “Confirmados”, remoção, coordenação e cards de equipe | Contrato legado de Alpinista/função | LEGADO | A página trata vínculo anterior como inscrição, aceite, participação e trabalho. |
| Templates e snapshots de equipe | `TemplateEquipeEncontro`, `TemplateRoleEquipe`, `EquipeEncontro`, `RoleEquipeEncontro` | preparar equipes e consulta de `/equipes-encontros/?encontro=` | Nenhuma representação canônica | Tela consulta `/funcoes/` | LEGADO | A mensagem “nenhuma função” mede `FuncaoEncontro`, não templates/snapshots. |
| Trabalho e alocação | `TrabalhoEncontro` | `/trabalhos-encontros/` e actions de alocar, realocar, desalocar, retirar, substituir e resultado | Cards e busca criam/deletam `VinculoEncontroLegado` | `/participacoes-encontros/` + `/alpinistas/?status=ativo` | LEGADO | Os trabalhos reais, estados, disponibilidade e elegibilidade não aparecem. |
| Histórico de trabalho | `TrabalhoEncontro` com experiência somente em `TRABALHOU` | consulta canônica de trabalho | Nenhuma tela localizada no Encontro | — | AUSENTE | Não há visão histórica; `FALTOU` operacional também não é apresentado. |
| Preparatórias na Agenda | `ReuniaoPreparatoriaEncontro` | comandos e projeção D.6 | Exibição e edição no Calendário | `/calendario-institucional/...` | ATUAL | O compromisso temporal está coberto. |
| Presença preparatória | `PresencaPreparatoria` e autorização contextual | `/presencas-preparatorias/` e `corrigir` | Nenhuma operação localizada | — | AUSENTE | Exibir Preparatória na Agenda não cobre presença nem revisão de permanência. |
| Formação | `SessaoFormativa` e `PalestranteSessao` | catálogo, sessões e actions canônicas | Nenhuma rota ou componente localizado | — | AUSENTE | Backend D.4 existe, mas não aparece dentro ou fora do Encontro. |
| Proposta de Violeiros | `PropostaVioleiros` e `ItemPropostaVioleiros` | `/propostas-violeiros/`, actions e seleção oficial | Nenhuma rota ou componente localizado | — | AUSENTE | MME, Diretoria, Suporte e Fichas não têm interface para suas operações específicas. |
| Avaliação simples | `AvaliacaoEncontro` 1:1 | comandos D.6 de criar, editar e remover | Item na Agenda e edição no drawer para gestores do Calendário | `/calendario-institucional/.../avaliacao/` | PARCIAL | Existe operação, mas sem integração com a finalização; permanece editável em estados terminais. |
| Publicação/PDF do Calendário | versões imutáveis, snapshot e arquivo privado | preview, publicação, histórico e download | Fluxo de exportação/publicação implementado | Contrato D.6 | ATUAL | Sem gap funcional identificado nesta auditoria; há apenas refinamento terminológico. |
| Transporte browser das APIs D.2–D.5 | Django possui as rotas canônicas | Recursos raiz canônicos registrados no DRF | Não consumíveis pelo `siaFetch` atual | Allowlist BFF contém apenas recursos antigos e Calendário | ACESSO BLOQUEADO | `inscricoes-encontros`, `convites-encontros`, `resultados-participacoes-encontros`, `equipes-encontros`, `trabalhos-encontros`, `presencas-preparatorias`, `sessoes-formativas`, `catalogo-formacao` e `propostas-violeiros` não estão liberados no proxy. |

### Lifecycle observado na interface

A seção Agenda respeita a projeção canônica. A página operacional de
`/encontros/{id}` não condiciona as abas Encontristas ou Equipes ao status do
Encontro. No drawer do Calendário, os botões de lifecycle variam por estado,
mas dados básicos, Preparatórias e Avaliação continuam renderizados para todo
estado quando o usuário pode editar.

| Estado | Página do Encontro | Ações do Calendário | Aceitação observável no backend | Adaptação |
|---|---|---|---|---|
| `EM_AGENDAMENTO` | Agenda + abas legadas completas | editar planejamento, oficializar e cancelar | comandos canônicos válidos; mutações legadas também não verificam lifecycle | PARCIAL |
| `AGENDADO` | Mesmas abas e ações legadas | reprogramar, adiar e cancelar | comandos canônicos válidos; mutações legadas continuam aceitas | PARCIAL |
| `EM_PREPARACAO` | Mesmas abas e ações legadas | adiar e cancelar; sem comando para iniciar o Encontro | transição canônica existe apenas em service; mutações legadas continuam aceitas | PARCIAL |
| `EM_ANDAMENTO` | Mesmas abas e ações legadas | cancelar; sem comando para finalizar | finalização canônica existe apenas em service; mutações legadas continuam aceitas | PARCIAL |
| `FINALIZADO` | Continua com fila, confirmação, remoção e montagem de equipe | oculta botões de lifecycle, mas ainda oferece dados básicos, Preparatórias e Avaliação | ações legadas não possuem guarda por status; services de dados básicos, reunião e avaliação também não rejeitam estado terminal | LEGADO |
| `ADIADO` | Mesmas abas e ações legadas | editor envia reprogramação; não usa explicitamente o command de novo planejamento | reprogramação canônica aceita `ADIADO`; mutações legadas continuam aceitas | PARCIAL |
| `CANCELADO` | Mesmas abas e ações legadas | oculta botões de lifecycle, mas ainda oferece dados básicos, Preparatórias e Avaliação | ações legadas e esses comandos auxiliares não possuem guarda terminal | LEGADO |

`FINALIZADO` e `CANCELADO` são terminais apenas na máquina de transições. A
página não possui modo histórico/read-only. Há, portanto, dois gaps distintos:

- **visual:** abas, textos e controles antigos permanecem iguais aos de um
  Encontro em preparação;
- **operacional:** efetivar/remover encontristas, CRUD de vínculo legado e
  alterações de dados básicos, Preparatórias e Avaliação não são recusados
  por uma regra terminal específica. Uma exclusão genérica pode falhar por
  integridade referencial, mas isso não equivale a uma política de lifecycle.

Não foi localizada tela de histórico de `ParticipacaoEncontro` nem de
`TrabalhoEncontro`.

### Encontristas — chamadas atuais

| Ação visual | Chamada | Objeto realmente manipulado |
|---|---|---|
| Fila de Espera | `GET /alpinistas/?status=pendente` | estado global do `Alpinista` legado |
| Confirmados | `GET /participacoes-encontros/?encontro={id}` | `VinculoEncontroLegado` com função `encontrista` |
| Confirmar selecionados | `POST /encontros/{id}/efetivar-encontristas/` | cria função/vínculo legado; não responde `ConviteEncontro` |
| Remover selecionados | `POST /encontros/{id}/remover-encontristas/` | exclui vínculo legado |

“Fila de Espera”, “Confirmados” e “Inscrições Pendentes” não correspondem de
forma confiável aos três conceitos canônicos de D.2. A confirmação apresentada
é uma efetivação legada, não `ConviteEncontro.status=CONFIRMADO`; a participação
efetiva e sua conclusão não possuem frontend.

### Equipes, trabalho e dataset

A aba de equipes consulta `GET /funcoes/`, carrega
`GET /participacoes-encontros/?encontro={id}`, pesquisa
`GET /alpinistas/?status=ativo` e cria/remove vínculos pelo CRUD de
`/participacoes-encontros/`. Não consulta templates, snapshots,
`EquipeEncontro`, roles ou `TrabalhoEncontro`.

O DEV-SEED.1 criou os dados no domínio canônico: 9 `EquipeEncontro` e 13
`TrabalhoEncontro`, além de templates, roles, Pessoas/Perfis e proposta MME.
Não fez dual-write para `FuncaoEncontro` ou `VinculoEncontroLegado`, em linha
com os workplans. Por isso:

- “nenhuma função de trabalho cadastrada” resulta da consulta à coleção
  legada `/funcoes/`, não da ausência de templates no seed;
- os 9 times e 13 trabalhos são invisíveis porque a tela consulta outra
  estrutura;
- o modal de candidatos depende primeiro de um card de `FuncaoEncontro` e,
  quando aberto, pesquisa Alpinistas legados ativos, não a avaliação canônica
  de elegibilidade/disponibilidade.

O seed tornou o gap observável; não há evidência de que esses três sintomas
sejam defeito do dataset.

### Formação e MME

O backend de Formação possui catálogo, sessões, palestrantes, realização e
histórico autorizado. Nenhum consumo desses endpoints foi localizado no
frontend, dentro do Encontro ou em rota própria.

O backend de MME possui proposta, cinco posições, disponibilidade derivada,
encerramento e aproveitamento oficial. Não existe tela, navegação ou consumo
frontend. MME não recebe, por decisão documentada, leitura geral do Encontro;
isso não é erro de autorização. O gap é a ausência de uma entrada específica
para a capacidade que o backend lhe concede. Fichas, Diretoria e Suporte
também não possuem UI para suas ações sobre propostas.

### Preparatórias e Avaliação

- **Agenda:** Preparatórias reais e Avaliação são projetadas e exibidas; os
  gestores do Calendário podem criar/editar Preparatórias e
  criar/editar/remover Avaliação pelo drawer.
- **Operação:** não há frontend para registrar/corrigir
  `PresencaPreparatoria`, aplicar a autorização contextual ou acompanhar a
  flag de revisão. A Agenda não substitui esse produto de D.3.
- **Lifecycle:** não foi localizado vínculo automático entre Avaliação e a
  transição para `FINALIZADO`; sua edição continua disponível inclusive após
  finalização ou cancelamento.

### Permissões, capabilities e navegação

| Papel | Backend permite | Navegação oferece | Página permite | Gap |
|---|---|---|---|---|
| Suporte | Encontro completo; Calendário e D.2–D.5 conforme matriz | Dashboard, Alpinistas, Encontros, Calendário | Agenda e operações legadas de Encontristas/Equipe | APIs canônicas D.2–D.5 sem UI/BFF. |
| Diretoria | Mesmo escopo operacional relevante de Suporte | Dashboard, Alpinistas, Encontros, Calendário | Agenda e operações legadas de Encontristas/Equipe | APIs canônicas D.2–D.5 sem UI/BFF. |
| Fichas | Encontro completo; D.2/D.3; leitura de D.4/D.5 e seleção oficial MME; Calendário read-only | Dashboard, Alpinistas, Encontros, Calendário | Agenda e operações legadas de Encontristas/Equipe | Não há UI canônica nem seleção MME. |
| Comunicação | Encontro summary, Agenda, Calendário e galeria autorizada | Alpinistas, Encontros, Calendário | Resumo do Encontro e Agenda; sem abas de gestão | Coerente para a página auditada; galeria não foi objeto desta R.3A. |
| MME | Propostas MME e Calendário; sem leitura geral de Encontro/equipe/trabalho | Alpinistas e Calendário | Não acessa `/encontros`; não há página de proposta | Ausência de frontend específico, não erro da proteção backend. |
| Formação | Formação em Encontros e Calendário; sem leitura geral de Encontro | Alpinistas e Calendário | Não acessa `/encontros`; não há página de Formação | Ausência de frontend específico, não erro da proteção backend. |
| Secretaria | Calendário read-only; sem Encontro | Alpinistas e Calendário | Não acessa `/encontros` | Coerente com a matriz para Encontros. |
| Ação Social, Liturgia e Eventos | Calendário read-only; sem Encontro | Alpinistas e Calendário | Não acessam `/encontros` | Coerente com a matriz para Encontros. |
| Sem papel | Default deny | Nenhuma entrada funcional | URL direta negada | Sem gap; observação manual confirmada. |

As capabilities do frontend espelham o acesso geral: Encontros para Suporte,
Diretoria, Fichas e Comunicação; gestão para os três primeiros; Calendário
para todo papel reconhecido e gestão apenas para Suporte/Diretoria. Elas não
modelam capacidades específicas de D.2–D.5. Os testes frontend relacionados
cobrem contratos antigos de formulário, Calendário, capabilities e navegação;
não há testes de fluxos canônicos ausentes.

### Achados do teste manual e causa

| Observação | Categoria | Causa identificada | Evidência |
|---|---|---|---|
| Conflito avisou e não bloqueou oficialização | — | comportamento advisory aprovado | Drawer usa command canônico e preserva `avisos_conflito`. |
| MME vê apenas Alpinistas e Calendário | NAVEGAÇÃO/CAPABILITY | capability geral de Encontro exclui MME conforme matriz | `ENCOUNTER_READ_ROLES` versus autorização específica de propostas. |
| MME não opera proposta | FRONTEND AUSENTE | D.5 não possui rota/componente e o BFF bloqueia o recurso raiz | ausência de referência frontend a `/propostas-violeiros/`. |
| Pouca variedade em Encontristas | FRONTEND LEGADO; SEED | tela lê `Alpinista.status`, não `Inscricao`, `ConviteEncontro` e `ParticipacaoEncontro` do seed | chamadas da página e ausência deliberada de dual-write. |
| Fila move pessoa para “Confirmados” | FRONTEND LEGADO | action cria `VinculoEncontroLegado`, não confirma convite | implementação de `efetivar-encontristas`. |
| “Nenhuma função” | FRONTEND LEGADO | `/funcoes/` lê `FuncaoEncontro`; seed criou templates/roles canônicos | contrato da aba versus modelos populados. |
| 9 equipes/13 trabalhos não aparecem | FRONTEND LEGADO | tela não consulta `EquipeEncontro`/`TrabalhoEncontro` | seed e chamadas frontend usam universos distintos. |
| Candidatos não aparecem | FRONTEND LEGADO; FRONTEND PARCIAL | sem função legada não há card/modal; busca eventual usa Alpinistas ativos e não elegibilidade canônica | fluxo condicional da aba. |
| Confirmação existe, conclusão não | FRONTEND LEGADO; FRONTEND AUSENTE | confirmação visual é efetivação antiga; API de resultado não é consumida | endpoints D.2 versus chamadas atuais. |
| `demo.sem_papel` é negado | — | default deny funciona | capabilities e proteção backend, confirmadas manualmente. |
| `FINALIZADO` mantém fila e equipes | LIFECYCLE; FRONTEND LEGADO | componentes não condicionam abas pelo status; mutações legadas não guardam estado terminal | renderização e actions do backend. |
| Preferência por “Calendário” | UX/TERMINOLOGIA | navegação e título já usam forma curta; ainda há texto longo em negação e diálogo/identificação de exportação | página do Calendário, header e `CalendarExportDialog`. |

### Síntese por bloco D.1–D.6

| Bloco | Backend | Frontend | Principal gap |
|---|---|---|---|
| D.1 — lifecycle | SIM | PARCIAL | status é exibido, mas três transições não têm API/UI e a página não se adapta ao modo terminal. |
| D.2 — inscrição/convite/participação | SIM | NÃO | a interface continua integralmente no fluxo e nos objetos legados. |
| D.3 — equipes/trabalho/preparatórias | SIM | PARCIAL | Preparatórias aparecem na Agenda; equipes, trabalho, elegibilidade e presença não têm UI canônica. |
| D.4 — formação | SIM | NÃO | API/autorização existem, sem frontend correspondente. |
| D.5 — MME | SIM | NÃO | API/autorização existem, sem navegação/UI específica e bloqueadas pelo BFF atual. |
| D.6 — Agenda/Calendário | SIM | SIM | fluxo principal atual; restam gaps de lifecycle em edições auxiliares e refinamento terminológico. |

### Terminologia do Calendário

A preferência humana fica registrada, sem mudança de código:

- interface do SIA: **Calendário**;
- PDF, publicação e documentação formal: **CALENDÁRIO INSTITUCIONAL**.

A navegação já mostra “Calendário” e o cabeçalho usa “Calendário do Movimento”.
“Calendário Institucional” permanece na mensagem de acesso negado da página e
no diálogo/identificação da exportação; o segundo uso pertence ao contexto
formal permitido. A adequação exata da mensagem de interface requer decisão
posterior, sem afetar contratos.

### Decisões humanas necessárias

Antes de qualquer implementação, o checkpoint de produto precisa definir:

1. quais capacidades canônicas de D.1–D.5 entram no próximo recorte de
   frontend e em qual ordem;
2. qual deve ser a fronteira de operação e histórico em `FINALIZADO` e
   `CANCELADO`, inclusive para dados básicos, Preparatórias e Avaliação;
3. como aposentar semanticamente “fila”, “confirmados” e montagem por função
   legada sem confundi-los com Inscrição, Convite, Participação e Trabalho;
4. como disponibilizar as capacidades específicas de MME e Formação sem lhes
   conceder leitura geral do Encontro além da matriz vigente;
5. se e quando a allowlist BFF será ampliada para cada API canônica, junto do
   frontend correspondente;
6. qual escopo operacional de Preparatórias/presença e histórico de
   participação/trabalho será priorizado;
7. onde a forma curta “Calendário” deve substituir texto de interface,
   preservando o nome formal em PDFs/publicações.

Estas são decisões de produto; esta auditoria não escolhe abas, navegação,
layout, fluxos ou uma nova estrutura da página do Encontro.

### Próximo checkpoint

**Checkpoint humano de produto dos gaps da R.3A**, antes de qualquer
implementação ou avanço para R.3B. R.3 permanece em andamento.
