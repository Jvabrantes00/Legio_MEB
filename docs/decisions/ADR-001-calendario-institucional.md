# ADR-001 — Calendário Institucional

- Status: aceita
- Data: 28 de setembro de 2026
- Etapa: 1B.3D.0

## Contexto

O SIA/MEB precisa oferecer uma visão institucional integrada de Encontros,
Eventos e compromissos gerais sem criar uma segunda fonte de verdade. A
modelagem também precisa acomodar planejamento provisório, agendas oficiais,
reprogramações e dias não consecutivos.

## Decisão

### Calendário como projeção

O Calendário Institucional será um HUB que projeta entidades dos respectivos
domínios. Não haverá um `ItemCalendario` que duplique nome, data ou tipo de um
Encontro, Evento ou compromisso já existente.

A estrutura conceitual para Encontros é:

```text
Encontro
  -> CalendarioEncontro
      -> DiaEncontro
```

Eventos manterão seus próprios dias. Um compromisso institucional genérico é
um conceito futuro e ainda não está definido.

### Duas portas para o mesmo objeto

Criar um Encontro pelo calendário criará o Encontro real, seu calendário e
seus dias. Criá-lo pelo módulo de Encontros fará o mesmo objeto aparecer no
calendário. Não existirão cadastros independentes.

O mesmo princípio valerá futuramente para Eventos.

### Lifecycle de Encontro

O fluxo principal aprovado é:

```text
EM_AGENDAMENTO
  -> AGENDADO
  -> EM_PREPARACAO
  -> EM_ANDAMENTO
  -> FINALIZADO
```

`ADIADO` e `CANCELADO` são estados laterais.

- `EM_AGENDAMENTO`: planejamento existente, com datas possivelmente
  provisórias, ainda sem confirmação oficial.
- `AGENDADO`: datas oficialmente confirmadas.
- `EM_PREPARACAO`: organização operacional iniciada.
- `EM_ANDAMENTO`: Encontro efetivamente iniciado.
- `FINALIZADO`: encerramento administrativo manual.

O tempo não muda status automaticamente.

### Planejamento e agenda oficial

Enquanto o Encontro estiver em `EM_AGENDAMENTO`, Diretoria e Suporte poderão
editar o calendário de planejamento vigente in-place. Esses ajustes não criam
versões históricas.

Ao passar para `AGENDADO`, a agenda torna-se oficial. Mudanças posteriores não
podem sobrescrevê-la: uma nova versão de calendário deve ser criada e a
anterior preservada. O Encontro conserva o mesmo ID.

### Adiamento

`ADIADO` não cria um novo Encontro. Sem novas datas, o fluxo esperado é:

```text
AGENDADO -> ADIADO -> EM_AGENDAMENTO -> AGENDADO
```

Se as novas datas já estiverem definidas durante o adiamento, uma operação
explícita de reprogramação pode retornar diretamente a `AGENDADO`. Em ambos os
casos, a agenda oficial anterior permanece histórica.

### Dias do Encontro

Um Encontro possui dias explícitos, que podem ser não consecutivos. Não serão
fixadas duração ou quantidade de dias por tipo de Encontro.

### Autorização

- Todas as roles funcionais reconhecidas poderão visualizar o calendário
  institucional completo.
- Somente Diretoria e Suporte poderão criar ou alterar objetos através do
  calendário.
- O superuser mantém seu bypass técnico separado das roles de negócio.
- Visualizar um item no calendário não concede permissão operacional sobre o
  objeto de origem.
- Equipes e demais operações continuam sujeitas à autorização de seus
  módulos de origem.

### Apresentação futura

As categorias iniciais serão `ENCONTRO`, `EVENTO` e `COMPROMISSO`. A interface
usará tokens semânticos equivalentes a `calendar.encounter`, `calendar.event`
e `calendar.commitment`, sem congelar cores nesta decisão.

Categoria será a camada visual principal e status poderá modificar a
apresentação secundária. Cor nunca será o único indicador: texto, ícone ou
rótulo acessível também deverá identificar o item e seu estado.

A direção conceitual da segunda camada é:

- `EM_AGENDAMENTO`: planejamento ou provisoriedade.
- `AGENDADO`: apresentação normal.
- `EM_PREPARACAO`: indicador de preparação.
- `EM_ANDAMENTO`: destaque.
- `ADIADO`: alerta.
- `CANCELADO`: apresentação atenuada.
- `FINALIZADO`: indicação de conclusão.

### Conflitos institucionais

O calendário deverá futuramente detectar sobreposições entre Encontros,
Eventos e compromissos. Inicialmente, conflitos gerarão aviso e não bloqueio,
pois sobreposições podem ser legítimas.

## Consequências

- Os módulos de origem continuam sendo a fonte de verdade.
- O núcleo de Encontros precisa modelar dias explícitos e versões de agenda.
- Transições de status e reprogramação devem ser operações explícitas.
- O calendário não pode ampliar implicitamente permissões de Encontros,
  Eventos ou equipes.
- A detecção inicial de conflitos será consultiva.

## Fora do escopo

Esta ADR não implementa models, migrations, services, API, frontend, Eventos,
compromissos genéricos, conflitos ou autorização contextual. Ela orienta a
1B.3D.1 — Núcleo de Encontros e as etapas futuras do Calendário Institucional.
