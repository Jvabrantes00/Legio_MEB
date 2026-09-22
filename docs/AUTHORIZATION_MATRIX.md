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

## Matriz

| Papel | API root | Admin | Alpinista | Escrita Alpinista | Foto perfil | Música | Palestras | Encontros | Galeria | Funções / participações | Eventos / participações | Materiais / entregas | Dashboard | Logs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Superuser técnico | R | RW | Full | RW | RW | RW | R | Full/RW | RW | RW | RW | RW | R | R |
| Suporte | — | — | Full | RW | RW | RW | R | Full/RW | RW | RW | RW | RW | R | R |
| Diretoria | — | — | Full | RW | RW | RW | R | Full/RW | RW | RW | RW | RW | R | R |
| Fichas | — | — | Full | RW | RW | RW | R | Full/RW | — | RW | — | — | R | — |
| MME | — | — | Summary | — | R | RW | — | — | — | — | — | — | — | — |
| Formação | — | — | Summary | — | R | — | R | — | — | — | — | — | — | — |
| Secretaria | — | — | Summary | — | R | — | — | — | — | — | — | RW | — | — |
| Ação Social | — | — | Summary | — | R | — | — | — | — | — | — | — | — | — |
| Liturgia | — | — | Summary | — | R | — | — | — | — | — | — | — | — | — |
| Eventos | — | — | Summary | — | R | — | — | — | — | — | RW | — | — | — |
| Comunicação | — | — | Summary | — | RW | — | — | Summary/R | RW | — | — | — | — | — |
| Usuário sem role | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

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

### Domínios especializados

- Eventos: Suporte, Diretoria e Eventos têm CRUD de Evento e Participação de
  Evento.
- Materiais: Suporte, Diretoria e Secretaria gerem materiais e registram
  entregas; Entrega oferece criar, listar e recuperar, não update/delete.
- Logs: Suporte e Diretoria têm leitura; o ViewSet é read-only.

## Semântica de negação

- `401 Unauthorized`: credencial ausente, inválida ou expirada.
- `403 Forbidden`: identidade válida, mas papel/capacidade insuficiente.
- `404 Not Found`: recurso ausente ou nested mismatch; não revelar associação
  pertencente a outro pai.
- A ausência de uma permissão explícita resulta em negação: **default deny**.

Mudanças nesta matriz exigem evidência de regra de negócio, alteração
correspondente no backend e testes de autorização. Não derive novas
permissões apenas a partir da navegação do frontend.
