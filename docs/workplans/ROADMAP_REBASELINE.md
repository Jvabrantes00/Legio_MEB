# Roadmap Re-baseline

## Status

R.1 concluída documentalmente em 2026-10-07 e aguardando validação humana.
Este documento não altera, substitui ou renumera o roadmap.

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
