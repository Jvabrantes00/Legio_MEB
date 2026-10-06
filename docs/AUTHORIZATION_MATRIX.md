# SIA/MEB — Matriz de Autorização

## Convenções

- **Full**: contrato completo autorizado para o domínio atual.
- **Summary**: contrato mínimo, sem campos sensíveis do perfil completo.
- **R**: leitura.
- **RW**: leitura e escrita permitidas pelos métodos/actions do recurso.
- **—**: acesso negado.
- Superuser é bypass técnico; **Suporte** é um papel de negócio distinto.

Esta matriz descreve somente o que está implementado. Capabilities do
frontend orientam a interface, mas o backend é a autoridade final.

A seção de Calendário Institucional ao final registra uma decisão futura,
ainda não implementada, sem alterar as permissões da matriz corrente.

## Matriz

| Papel | API root | Admin | Alpinista | Escrita Alpinista | Foto perfil | Música | Propostas MME | Formação em Encontros | Encontros | Galeria | Funções / participações | Eventos / participações | Materiais / entregas | Dashboard | Logs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Superuser técnico | R | RW | Full | RW | RW | RW | RW | RW | Full/RW | RW | RW | RW | RW | R | R |
| Suporte | — | — | Full | RW | RW | RW | RW | RW | Full/RW | RW | RW | RW | RW | R | R |
| Diretoria | — | — | Full | RW | RW | RW | RW | RW | Full/RW | RW | RW | RW | RW | R | R |
| Fichas | — | — | Full | RW | RW | RW | R | R | Full/RW | — | RW | — | — | R | — |
| MME | — | — | Summary | — | R | RW | RW | — | — | — | — | — | — | — | — |
| Formação | — | — | Summary | — | R | — | — | RW | — | — | — | — | — | — | — |
| Secretaria | — | — | Summary | — | R | — | — | — | — | — | — | — | RW | — | — |
| Ação Social | — | — | Summary | — | R | — | — | — | — | — | — | — | — | — | — |
| Liturgia | — | — | Summary | — | R | — | — | — | — | — | — | — | — | — | — |
| Eventos | — | — | Summary | — | R | — | — | — | — | — | — | RW | — | — | — |
| Comunicação | — | — | Summary | — | RW | — | — | — | Summary/R | RW | — | — | — | — | — |
| Usuário sem role | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

## Detalhes importantes

### Fronteiras técnicas

- `/api/` é reservado a superuser autenticado.
- `/admin/` exige superuser Django ativo; `is_staff` isoladamente não basta.
- O endpoint de identidade `/api/auth/me/` exige autenticação, mas pode
  representar usuário sem role para que o BFF preserve a distinção entre
  sessão válida e autorização de negócio.

### Alpinistas

- Todos os papéis reconhecidos podem ler o summary.
- Suporte, Diretoria e Fichas recebem full e CRUD.
- O arquivo da foto de perfil pode ser lido por todos os papéis reconhecidos.
- Gestão da foto cabe a Suporte, Diretoria, Fichas e Comunicação.
- Música e histórico de Violeiro cabem a Suporte, Diretoria, Fichas e MME.
- Histórico de palestras cabe a Suporte, Diretoria, Fichas e Formação.
- Filtros, busca e ordenação também são limitados por papel.

### Encontros e galeria

- Suporte, Diretoria e Fichas recebem full, CRUD, funções, participações e
  actions de efetivar/remover encontristas.
- Comunicação recebe somente identificação summary do Encontro.
- A galeria é um subrecurso separado: Suporte, Diretoria e Comunicação podem
  listar, adicionar, substituir, remover e ler arquivos.
- Fichas não recebe acesso à galeria no contrato atual.
- Foto associada a outro Encontro retorna `404`, não acesso cruzado.

### Presença preparatória contextual

- Suporte, Diretoria e Fichas podem registrar e corrigir presença preparatória
  como parte da administração de Encontros. O superuser permanece como bypass
  técnico separado.
- Um usuário ativo sem papel administrativo pode registrar ou corrigir
  presença somente quando possui vínculo explícito com a `Pessoa` alocada em
  role snapshot habilitada para presença naquele mesmo Encontro.
- Essa capability contextual termina quando o trabalho deixa de estar
  `ALOCADO` ou quando o Encontro fica `FINALIZADO`/`CANCELADO`.
- A capability não concede leitura global de Encontros ou Alpinistas, gestão
  de equipes/participantes, acesso a saúde nem qualquer papel global.
- A API contextual oferece apenas criação e correção; ausência de regra
  explícita permanece negada.

### Equipes e trabalho em Encontro

- Suporte, Diretoria e Fichas podem consultar snapshots por Encontro e
  executar os comandos canônicos de convite, início, alocação, realocação,
  retirada, substituição e resultado de trabalho. O superuser permanece como
  bypass técnico separado.
- As consultas exigem escopo explícito de Encontro e os comandos não expõem
  update ou delete genéricos de `TrabalhoEncontro`.
- Avisos de elegibilidade exigem confirmação explícita; bloqueios estruturais
  permanecem impeditivos. Essa gestão não concede acesso a dados de saúde.
- Usuários sem uma das roles administrativas não recebem gestão de equipes. A
  capability contextual da Coordenação Geral continua limitada ao registro de
  presença preparatória e não amplia esses comandos.

### Formação em Encontros

- Suporte, Diretoria e Formação podem criar e configurar sessões, gerir
  palestrantes, cancelar e registrar realização. O superuser permanece como
  bypass técnico separado.
- Fichas pode consultar catálogo, sessões, palestrantes e históricos, mas não
  recebe gestão. Os demais papéis permanecem negados por default.
- A gestão de Formação não concede escrita de Alpinista, TrabalhoEncontro,
  equipes, Frequência ou saúde. Regras por tipo e a invariante do AVC são
  aplicadas pelos services canônicos.
- O histórico formativo canônico é separado do histórico de equipes. A leitura
  do endpoint legado de palestras permanece disponível durante a
  compatibilidade, sem dual-write ou backfill automático.

### MME e Propostas de Violeiros

- Suporte, Diretoria e MME podem criar, editar, preencher, substituir, retirar
  e encerrar propostas. O superuser permanece bypass técnico separado.
- Fichas pode listar, consultar resumo e disponibilidade e aproveitar um
  candidato pelo fluxo oficial de convite de trabalho, mas não altera a
  proposta diretamente.
- A seleção pela proposta cria somente `ConviteEncontro(TRABALHAR)` e pode
  indicar uma role oficial diferente da sugestão. Confirmação, trabalho e
  alocação continuam nos comandos canônicos da D.3.
- MME não recebe CRUD geral de Encontro, equipe ou trabalho. A sugestão de
  coordenação não concede autorização contextual.
- Os demais papéis permanecem negados por default. Situação e completude são
  derivadas, sem dual-write na proposta.

### Domínios especializados

- Eventos: Suporte, Diretoria e Eventos têm CRUD de Evento e Participação de
  Evento.
- Materiais: Suporte, Diretoria e Secretaria gerem materiais e registram
  entregas; Entrega oferece criar, listar e recuperar, não update/delete.
- Logs: Suporte e Diretoria têm leitura; o ViewSet é read-only.

### Calendário Institucional — decisão futura

- Todas as roles funcionais reconhecidas poderão visualizar o calendário
  institucional completo.
- Somente Suporte e Diretoria poderão criar ou alterar objetos através do
  calendário.
- O superuser permanece como bypass técnico separado.
- Visualizar um item no calendário não concede permissão de gestão sobre o
  objeto de origem.
- Encontros, Eventos, equipes e demais recursos continuarão sujeitos às
  permissões de seus próprios módulos.
- Esta política somente entrará na matriz implementada junto com backend,
  frontend e testes de autorização correspondentes.

## Semântica de negação

- `401 Unauthorized`: credencial ausente, inválida ou expirada.
- `403 Forbidden`: identidade válida, mas papel/capacidade insuficiente.
- `404 Not Found`: recurso ausente ou nested mismatch; não revelar associação
  pertencente a outro pai.
- A ausência de uma permissão explícita resulta em negação: **default deny**.

Mudanças nesta matriz exigem evidência de regra de negócio, alteração
correspondente no backend e testes de autorização. Não derive novas
permissões apenas a partir da navegação do frontend.
