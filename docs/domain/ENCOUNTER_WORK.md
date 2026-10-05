# Equipes e Trabalho em Encontro

Este documento registra as regras estáveis do domínio de equipes, alocação e
trabalho em Encontros. Decisões técnicas, progresso e histórico da Fase
1B.3D.3 pertencem ao
[[../workplans/PHASE_1B_D3|workplan da fase]].

## Separação conceitual

- Template de equipe não é equipe de uma edição específica.
- Convite para trabalhar não é alocação em equipe.
- Confirmação não é trabalho realizado.
- Escala provisória, falta e recusa não compõem o histórico permanente de
  trabalho.
- `ConviteEncontro` e `TrabalhoEncontro` permanecem conceitos separados.
- `CONFIRMADO` pertence ao convite.

## Templates, equipes e roles

- Templates de equipes são administrados pelo sistema ou por Suporte. Fichas
  e Diretoria não os alteram livremente durante a operação normal.
- Ao criar ou preparar um Encontro, as equipes aplicáveis e suas roles são
  copiadas como snapshot para aquela edição.
- Mudanças futuras no template não alteram Encontros históricos.
- Roles/funções pertencem à estrutura do template. Quando houver role
  definida, ela não deve ser substituída por texto livre.
- A operação preserva o conceito de uma posição definida pela estrutura e uma
  Pessoa escolhida para ocupá-la.
- Equipe e role são conceitos distintos: a equipe agrupa o trabalho, enquanto
  a role descreve a posição ocupada dentro dela.

## Equipes por tipo de Encontro

| Tipo | Equipes |
|---|---|
| Escalada e ESPPA | Coordenação Geral, Dirigentes, Apoio, Auxiliares, Violeiros, Cozinha e Vigília |
| AVC | Coordenação Geral, Apoio, Auxiliares, Violeiros, Cozinha e Vigília |
| Acampamento | Coordenação, Guias, Suportes, Intercessão, Limpeza e Cozinha |

AVC não possui equipe de Dirigentes.

## Capacidades consultivas

As capacidades são referências operacionais e devem produzir avisos quando
apropriado. Não são constraints rígidas, salvo composições estruturais
explicitamente definidas.

### Escalada, ESPPA e AVC

| Equipe | Referência |
|---|---|
| Dirigentes, quando aplicável | 6 |
| Auxiliares | 6 |
| Apoio | 5 |
| Violeiros | 5 |
| Cozinha | Sem máximo rígido inicial |
| Vigília | 10 a 14 |
| Coordenação Geral | 6 posições estruturais |

Equipes comuns têm recomendação mínima de três integrantes mais coordenação,
quando aplicável.

### Acampamento

| Equipe | Referência |
|---|---|
| Guias | 10 a 12 |
| Suportes | 6 |
| Intercessão | 4 a 5 |
| Limpeza | 6 |
| Coordenação | 4 posições estruturais |
| Cozinha | 6 a 8 |

Limites operacionais consultivos não devem ser convertidos em constraints SQL
frágeis.

## Composição de coordenação

### Coordenação Geral de Escalada, ESPPA e AVC

São seis posições:

- duas de Adulto Geral;
- duas de Adulto Auxiliar;
- duas de Jovem.

Referências antigas a “casal” representam uma dupla operacional e não exigem
vínculo conjugal. Casamento não é requisito de domínio.

### Vigília

- dois coordenadores adultos;
- dois coordenadores jovens;
- integrantes.

### Outras equipes

Normalmente possuem um coordenador jovem e integrantes.

### Coordenação de Acampamento

São quatro posições: duas de adulto e duas de jovem.

Todas essas posições devem ser representáveis pelas roles do template.

## Convite para trabalhar e alocação

- `ConviteEncontro` com finalidade `TRABALHAR` é a origem do convite.
- Normalmente a Pessoa é convidada sem conhecer inicialmente equipe ou role.
- Após a confirmação, pode existir `TrabalhoEncontro` ainda sem alocação até a
  definição operacional.
- A equipe costuma ser apresentada na primeira reunião preparatória.
- Quem for chamado depois dessa reunião pode receber o convite já conhecendo
  equipe e role.
- Uma Pessoa pode ocupar somente uma equipe/role no mesmo Encontro. Essa é uma
  invariante forte.
- Antes do Encontro, a Pessoa pode ser realocada. O estado operacional atual ou
  final, junto da auditoria geral, é suficiente; não é necessária uma timeline
  completa de todas as alocações.
- Somente Fichas, Diretoria e o acesso técnico apropriado de Suporte podem
  alterar a composição das equipes.

## TrabalhoEncontro e histórico

`TrabalhoEncontro` representa a participação operacional de uma Pessoa como
trabalhadora de um Encontro. O domínio distingue:

- convidado;
- confirmado;
- alocado ou escalado;
- trabalhou;
- faltou;
- retirado ou substituído operacionalmente, quando necessário.

Somente quem efetivamente `TRABALHOU` entra no histórico permanente do
Alpinista e nos contadores históricos. Convite, confirmação, escala provisória,
recusa e falta podem permanecer para operação ou auditoria, mas não contam
como trabalho realizado.

## Substituições

- Uma Pessoa alocada pode ser trocada por outra sem relacionamento explícito
  entre substituída e substituta.
- Não haverá campo `substituido_por` nem entidade específica de substituição.
- A auditoria geral pode registrar a alteração.
- O histórico principal reflete quem efetivamente trabalhou.

## Reuniões preparatórias e presença

- Um Encontro pode possuir múltiplas reuniões preparatórias ordenadas.
- `ReuniaoPreparatoriaEncontro` deve representar Encontro, ordem, data,
  horário, local e observações quando necessárias.
- A presença preparatória é vinculada ao trabalhador do Encontro.
- `PresencaPreparatoria` possui os estados `PRESENTE`,
  `AUSENTE_JUSTIFICADO` e `AUSENTE_SEM_JUSTIFICATIVA`.
- A justificativa é opcional quando aplicável.
- Ausência sem justificativa sinaliza revisão da permanência na equipe, mas
  nunca remove automaticamente a Pessoa. A decisão é humana e cabe a Fichas
  ou Diretoria.

## Autorização contextual da Coordenação Geral

- Somente integrantes apropriados da Coordenação Geral recebem acesso
  contextual para registrar presença em reuniões preparatórias.
- Coordenar outra equipe não concede esse acesso.
- A permissão depende do vínculo real com a Coordenação Geral, do Encontro e
  do estado/contexto correspondente.
- O acesso termina quando o contexto deixa de permiti-lo, especialmente após
  `FINALIZADO` ou `CANCELADO`.
- O sistema não cria nem destrói contas automaticamente. Fichas e Suporte
  continuam responsáveis pela gestão das contas.
- Negar ou remover acesso contextual não apaga o `User` técnico nem seu
  histórico de auditoria.

## Elegibilidade essencial para trabalhar

- Normalmente o trabalhador deve ser Alpinista ativo.
- Alpinista inativo gera aviso e pode trabalhar por decisão humana.
- No caminho da Escalada, é necessário ter concluído AVC antes de trabalhar
  em Escalada.
- Quem veio pelo caminho ESPPA pode trabalhar em Escalada ou ESPPA conforme as
  regras aplicáveis.
- Quem concluiu Escalada e AVC pode trabalhar em ESPPA.
- AVC e Acampamento possuem restrições próprias, a serem fechadas tecnicamente
  na D.3A sem transformar recomendações em bloqueios indevidos.
- A avaliação deve distinguir resultado elegível, aviso e bloqueio somente
  quando a regra for estrutural.

## Fronteiras do domínio

- Trabalho em Encontro não cria `Frequencia` automaticamente.
- Saúde contextual não faz parte da D.3. Equipe ou role não concede nesta fase
  acesso a alergias, medicamentos, neurodivergência ou condição médica.
- O motor de elegibilidade não pertence à preparação do Vault; seu desenho
  técnico será fechado na D.3A e sua implementação ocorrerá em bloco próprio.

## Compatibilidade

A evolução segue:

`EXPAND` → `POPULATE`, somente quando seguro → `COMPAT` → `CUTOVER` →
`DEPRECATE`.

O legado mistura função e equipe. A D.3A deve localizar exatamente os models
e vínculos legados, `FuncaoEncontro`, choices, serializers, views, APIs,
contratos frontend, históricos, testes e migrations dependentes antes de
propor adaptação. Nenhum backfill heurístico é permitido.
