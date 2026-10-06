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

A D.6A definirá quais comandos canônicos serão expostos diretamente sem
replicar todo o módulo de Encontros.

## Categoria, status e conflitos

- Categoria e status são dimensões diferentes. Nesta fase a única categoria
  é `ENCONTRO`; a arquitetura deve admitir categorias futuras.
- Nenhuma dessas dimensões pode ser comunicada somente por cor. Texto, badge,
  ícone, forma ou outro marcador acessível deve acompanhar a cor.
- Cores exatas não estão definidas nesta etapa.
- Sobreposições de agenda produzem avisos consultivos e não bloqueiam
  automaticamente criação ou edição.
- A D.6A definirá o mecanismo técnico mínimo de detecção de conflitos.

## PDFs de divulgação

Existem duas modalidades aprovadas:

- PDF mensal, com o mês completo em grade e o nome do Encontro dentro da
  célula correspondente;
- PDF anual, preservando a linguagem visual de calendário e de meses.

O PDF é artefato de divulgação, não fonte de verdade ou edição. Não haverá
exportação Excel, importação de planilha nem sincronização externa nesta
fase.

Datas provisórias podem ser divulgadas, mas devem receber `*` e uma legenda
discreta equivalente a "* Data ainda sujeita a confirmação." A redação e a
apresentação finais pertencem ao checkpoint de UX/UI.

O conteúdo publicável fica limitado ao necessário para divulgação
institucional, inicialmente data e nome do Encontro. PDFs não incluem
participantes, equipes, dados pessoais, saúde, preparação interna, permissões
ou observações administrativas privadas.

Somente Diretoria, Suporte e o bypass técnico do superuser podem gerar ou
publicar PDFs. A política de consulta e download do histórico será refinada na
fase, se necessário.

## Histórico de divulgação

- Toda versão efetivamente divulgada deve ser preservada e recuperável.
- Nova publicação não sobrescreve material divulgado anteriormente.
- O registro deve preservar o conteúdo exato publicado naquele momento;
  consultar apenas o estado canônico atual não é suficiente.
- A D.6A escolherá a estratégia mínima segura entre artefato imutável,
  snapshot estruturado, combinação de ambos, metadados e integridade/hash.

## Checkpoint obrigatório de UX/UI

A D.6D é uma pausa humana obrigatória. Antes da aprovação nela:

- não será implementado o frontend personalizado;
- não serão definidos o design final ou a composição final dos PDFs;
- não serão fixados cores, papel, orientação, fontes, dimensões, densidade,
  tratamento de nomes longos ou de muitas atividades no mesmo dia.

Navegação, visualizações, desktop/mobile, interações, criação/edição,
múltiplos dias, provisoriedade, filtros, acessibilidade e identidade visual
serão discutidos com o usuário. A paleta candidata registrada para essa
conversa não deve ser aplicada automaticamente.

## Fora de escopo

- Eventos e compromissos institucionais genéricos.
- Saúde e fonte canônica de atividade.
- Frontend canônico das D.2–D.5.
- Excel, importação ou sincronização de calendário externo.
- Decisões visuais finais antes da D.6D.
