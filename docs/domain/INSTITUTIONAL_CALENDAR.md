# Calendário Institucional — fatia de Encontros

Este documento registra as regras estáveis da fatia de Encontros do
Calendário Institucional. A decisão arquitetural principal permanece no
[[../decisions/ADR-001-calendario-institucional|ADR-001]]; desenho técnico,
execução e histórico da Fase 1B.3D.6 pertencem ao
[[../workplans/PHASE_1B_D6|workplan da fase]].

## Escopo desta fatia

A D.6 cobre somente Encontros:

- projeção institucional e consultas;
- criação e edição pelo Calendário;
- autorização;
- frontend personalizado;
- PDFs mensal e anual;
- preservação das versões efetivamente divulgadas;
- integração e regressão.

Eventos e compromissos institucionais genéricos não serão modelados nesta
fase, embora a solução não deva impedir sua inclusão futura no mesmo HUB.

## HUB e fonte da verdade

- O Calendário projeta o `Encontro` canônico; não possui uma cópia do objeto
  para exibição.
- Criar pelo Calendário cria o Encontro real, sua agenda e seus dias. Criar
  pelo módulo de Encontros faz o mesmo objeto aparecer no Calendário.
- Calendário e módulo de Encontros são duas interfaces para o mesmo domínio.
- Toda alteração ocorre no SIA e passa pelos comandos e services canônicos.
  Planilhas ou artefatos exportados nunca retornam como fonte de edição.

O fluxo conceitual de divulgação é:

```text
alteração no SIA
  -> domínio canônico
  -> histórico e auditoria
  -> projeção institucional
  -> PDF de divulgação
```

## Agenda, versões e dias

- A estrutura temporal é `Encontro -> CalendarioEncontro -> DiaEncontro`.
- `CalendarioEncontro.vigente` identifica a versão atualmente selecionada;
  não significa, isoladamente, que a agenda já seja oficial.
- Em `EM_AGENDAMENTO`, datas podem ser provisórias e a versão vigente pode
  ser editada sem criar histórico para cada ajuste.
- Ao passar para `AGENDADO`, a agenda vigente torna-se oficial.
- Uma alteração posterior de data oficial preserva a agenda anterior e cria
  nova versão.
- Dias podem ser não consecutivos. Cada `DiaEncontro` é projetado no
  Calendário sem transformar um Encontro em vários objetos.
- Cada dia próprio do Encontro pode possuir um rótulo público curto e
  editável. Sugestões por tipo podem ser oferecidas, mas não são obrigatórias
  nem inferidas automaticamente pela posição da data.

## Agenda agregada do Encontro

A Agenda apresentada ao usuário é uma composição cronológica de fontes
canônicas, sem tabela visual duplicada:

- dias próprios, vindos de `DiaEncontro`;
- Preparatórias, vindas de `ReuniaoPreparatoriaEncontro`;
- avaliação pós-Encontro, como item simples de agenda vinculado ao Encontro.

Criar ou editar uma Preparatória pela Agenda atua sobre a reunião real e
preserva as regras de presença do domínio de trabalho. Um rótulo complementar
pode qualificar a reunião sem transformar esse complemento em novo tipo de
compromisso.

A avaliação não é reunião, dia do Encontro, presença, participação, trabalho
ou equipe. Ela existe apenas para compor a cronologia do Encontro e deve ter
modelagem mínima própria e expansiva. Não serão generalizados outros tipos de
compromisso nesta fase.

O Calendário Institucional e a seção Agenda da página canônica do Encontro
leem esses mesmos objetos. Não há sincronização, cópia ou dual-write entre as
duas interfaces.

## Lifecycle, adiamento e reprogramação

O lifecycle canônico continua manual:

```text
EM_AGENDAMENTO
  -> AGENDADO
  -> EM_PREPARACAO
  -> EM_ANDAMENTO
  -> FINALIZADO
```

`ADIADO` e `CANCELADO` permanecem estados laterais. Datas nunca iniciam ou
finalizam um Encontro automaticamente. A nova interface deve usar `status`, e
não a projeção temporal legada `status_encontro`.

Adiamento não cria novo Encontro. Replanejamento, reoficialização e
reprogramação preservam o mesmo Encontro e o histórico das agendas oficiais,
conforme os services canônicos.

## Consulta e gestão

- Todos os papéis funcionais reconhecidos podem visualizar o Calendário
  Institucional completo.
- Diretoria e Suporte podem criar ou alterar Encontros pela interface do
  Calendário. O superuser mantém bypass técnico separado.
- Outros papéis permanecem somente leitura no Calendário.
- Visualização não concede edição do Encontro, gestão de participantes ou
  equipes, acesso a saúde ou permissão sobre o módulo de origem.
- Comandos expostos pelo Calendário devem reutilizar os services de Encontro;
  lifecycle e regras temporais não serão duplicados na API de projeção.

Os comandos expostos se limitam a criação, dados básicos, planejamento,
oficialização, reprogramação, adiamento, novo planejamento e cancelamento.
Preparação, início, finalização e operações internas permanecem no módulo de
Encontros.

## Categoria, status, visibilidade e conflitos

- Categoria e status são dimensões diferentes. Nesta fase a única categoria
  é `ENCONTRO`; a arquitetura deve admitir categorias futuras.
- Nenhuma dessas dimensões pode ser comunicada somente por cor. Texto, badge,
  ícone, forma ou outro marcador acessível deve acompanhar a cor.
- Itens apropriados distinguem visibilidade `PUBLICÁVEL` e `INTERNO` de forma
  coerente com o domínio. O renderer não decide visibilidade por uma lista
  fixa de classes.
- Sobreposições de agenda produzem avisos consultivos e não bloqueiam
  automaticamente criação ou edição.

## PDFs de divulgação

Existem três combinações de período/layout nos escopos Público e Interno:

- mês selecionado + layout mensal: uma página;
- ano completo + layout mensal: um único PDF de 12 páginas;
- ano completo + anual resumido Modelo B: uma página A4 paisagem.

Mês + anual resumido não é uma combinação válida. Período e layout são
dimensões independentes do contrato.

O PDF é artefato de divulgação, não fonte de verdade ou edição. Não haverá
exportação Excel, importação de planilha nem sincronização externa nesta
fase.

Datas provisórias podem ser divulgadas, mas devem receber `*` e a legenda
discreta `* Data ainda sujeita a confirmação.`

O PDF público contém somente itens publicáveis externamente, inicialmente os
dias publicáveis dos Encontros. Por padrão, não inclui Preparatórias,
Avaliação, dados pessoais, equipes, presença ou informações
operacionais.

O PDF interno pode reunir Dias, Preparatórias e Avaliação e recebe
identificação discreta `USO INTERNO`. Interno significa agenda operacional
mais completa, não autorização irrestrita para dados pessoais ou sensíveis.

As modalidades preservam linguagem de calendário em A4 paisagem. O anual
resumido definitivo é o Modelo B, em composição 3 × 4; o Modelo A permanece
somente como alternativa avaliada no spike. Os PDFs usam apenas o símbolo
oficial do pé no canto superior direito.

Somente Diretoria, Suporte e o bypass técnico do superuser podem gerar ou
publicar PDFs. Todas as roles funcionais reconhecidas podem consultar e baixar
publicações públicas; publicações internas permanecem restritas aos gestores.

## Histórico de divulgação

- Toda versão efetivamente divulgada deve ser preservada e recuperável.
- Nova publicação não sobrescreve material divulgado anteriormente.
- O registro deve preservar o conteúdo exato publicado naquele momento;
  consultar apenas o estado canônico atual não é suficiente.
- Cada publicação preserva PDF imutável, snapshot estruturado allowlist,
  metadados e hash de integridade. Preview não integra o histórico.

## Diretrizes de produto aprovadas

- O sistema oferece visões Mês e Ano; mês atual é a entrada padrão.
- A visão anual é síntese e navegação, não lista completa de nomes.
- No mobile, selecionar um dia revela abaixo uma lista legível dos seus itens.
- A data provisória usa `*` e legenda; não exibe texto de confirmação dentro
  da célula.
- O detalhe do calendário é enxuto e direciona operações completas para a
  página canônica do Encontro.
- Somente gestores visualizam ações de criação, edição e exportação.
- Filtros de Eventos e Outros permanecem desabilitados até seus domínios
  existirem; status e confirmação não viram filtros nesta fase.
- Categoria nunca é comunicada apenas por cor e a identidade principal usa
  ícones locais próprios conforme cada módulo for implementado.

## Fora de escopo

- Eventos e compromissos institucionais genéricos.
- Saúde e fonte canônica de atividade.
- Frontend canônico das D.2–D.5.
- Excel, importação ou sincronização de calendário externo.
- Tipos genéricos adicionais de compromisso além da avaliação aprovada.
