# MME e Propostas de Violeiros

Este documento registra as regras estáveis do domínio de planejamento do MME
para possíveis equipes de Violeiros em Encontros. Decisões técnicas, progresso
e histórico da Fase 1B.3D.5 pertencem ao
[[../workplans/PHASE_1B_D5|workplan da fase]].

## Natureza das propostas

- O MME prepara propostas de possíveis equipes de Violeiros para um Encontro.
- Proposta é planejamento interno: não é escala oficial, não reserva Pessoa de
  forma bloqueante e não gera `ConviteEncontro` ou `TrabalhoEncontro`.
- Um Encontro pode possuir múltiplas propostas para oferecer combinações
  diferentes a Fichas e Diretoria.
- A seleção oficial pode misturar candidatos de várias propostas e incluir
  Pessoas que não apareciam em nenhuma delas. Propostas não são chapas
  indivisíveis.

## Composição e posições ativas

- Uma proposta completa possui cinco candidatos ativos e disponíveis: um
  coordenador sugerido e quatro integrantes sugeridos.
- A role sugerida é apenas recomendação. Ela não concede permissão, não cria
  coordenação oficial, não altera papel do usuário e não obriga a escala
  oficial a preservar a sugestão.
- A regra de cinco limita posições ativas, não a quantidade histórica de
  registros da proposta.
- Candidato aproveitado ou indisponível permanece preservado no planejamento,
  mas deixa de ocupar uma posição ativa. A proposta pode então ser completada
  com outro candidato e acumular mais de cinco registros históricos, sem
  ultrapassar cinco posições ativas vigentes.
- Não é necessário relacionar uma Pessoa indisponível a quem ocupou sua vaga.

## Participação em múltiplas propostas

- O mesmo Alpinista pode aparecer em várias propostas do mesmo Encontro.
- Dentro da mesma proposta, o mesmo Alpinista aparece no máximo uma vez.
- Não existe unicidade global Alpinista/Encontro para candidatos propostos.

## Disponibilidade e escala oficial

- A escala oficial, representada pelo domínio de `TrabalhoEncontro`, é a fonte
  operacional da verdade.
- Quando uma Pessoa proposta é oficialmente alocada em qualquer equipe do
  mesmo Encontro, ela deixa de estar disponível em todas as propostas daquele
  Encontro.
- A indisponibilidade vale tanto para aproveitamento como Violeiro quanto para
  escala em Apoio, Auxiliares, Cozinha, Coordenação ou qualquer outra equipe.
- Quem for aproveitado como Violeiro permanece identificável no histórico da
  proposta, mas deixa de ocupar posição ativa disponível.
- A disponibilidade deve derivar da escala oficial sempre que tecnicamente
  apropriado, sem depender de baixa manual do MME.
- A invariante canônica de uma única equipe/role oficial por Pessoa e Encontro
  continua pertencendo ao domínio de Trabalho.

## Proposta incompleta

- Perda de candidatos ativos por escala oficial ou outra causa operacional
  aprovada pode deixar a proposta incompleta.
- O sistema deve tornar consultável a quantidade disponível e indicar quando a
  proposta precisa ser completada, por exemplo `4/5 disponíveis`.
- Este domínio não define canal de notificação, push, e-mail ou infraestrutura
  geral de alertas.

## Edição e encerramento

- Enquanto o planejamento de Violeiros estiver aberto, MME e Diretoria podem
  editar e completar propostas.
- Candidatos aproveitados ou indisponíveis não são apagados retroativamente.
- Não é necessária timeline completa de cada edição além da preservação
  essencial e da auditoria geral aplicável.
- Quando o planejamento for encerrado, a proposta deixa de ser operacional e
  de ser alterada normalmente, mas permanece como histórico de planejamento.
- Depois do encerramento, mudanças operacionais ocorrem na escala oficial, sem
  reescrever propostas encerradas.

## Autorização e seleção oficial

- MME, Diretoria e Suporte podem criar e editar propostas. Superuser permanece
  bypass técnico separado.
- Fichas pode consultar propostas e aproveitar zero, alguns ou todos os nomes,
  inclusive combinando propostas, mas não edita a proposta MME diretamente.
- A reação da disponibilidade à escala oficial não transforma Fichas em MME.
- Somente a seleção oficial usa os fluxos canônicos de
  `ConviteEncontro(TRABALHAR)` → `TrabalhoEncontro` → alocação.

## Histórico do Alpinista

- Proposta MME não compõe histórico permanente do Alpinista e não representa
  trabalho realizado.
- Somente quem efetivamente `TRABALHOU` como Violeiro na escala oficial entra
  no histórico canônico.
- O fato de alguém ter sido sugerido pelo MME não deve aparecer como trabalho
  realizado.

## Perfil MME e elegibilidade

- Não existe catálogo de instrumentos neste domínio.
- As características relevantes são `violeiro`, `canta` e `disponivel_mme`,
  conforme a estrutura canônica existente ou aprovada de `PerfilAlpinista`.
- Propostas não duplicam o motor de elegibilidade da D.3. Disponibilidade e
  elegibilidade consultam as fontes canônicas existentes.
- Uma Pessoa sugerida pode deixar de ser elegível ou disponível depois, sem
  que seu registro histórico seja apagado.

## Separação de domínios

Uma proposta MME isolada não:

- cria `Frequencia`, `PerfilAlpinista`, `Pessoa` ou `User`;
- altera saúde ou Formação em Encontros;
- cria convite, trabalho, equipe oficial ou histórico de trabalho;
- concede permissão de coordenação por causa da role sugerida;
- impede a inclusão da mesma Pessoa em outra proposta.

## Compatibilidade

A evolução segue:

`EXPAND` → `POPULATE`, somente quando seguro → `COMPAT` → `CUTOVER` →
`DEPRECATE`.

A D.5A deve inspecionar estruturas de MME, perfil, pré-equipes, API, frontend,
histórico, autorização, testes e migrations antes do desenho técnico. Nenhum
backfill heurístico é permitido.
