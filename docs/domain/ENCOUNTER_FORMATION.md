# Formação em Encontros

Este documento registra as regras estáveis do domínio de palestras,
bate-papos, sessões formativas e palestrantes em Encontros. Decisões técnicas,
progresso e histórico da Fase 1B.3D.4 pertencem ao
[[../workplans/PHASE_1B_D4|workplan da fase]].

## Tipos de conteúdo por Encontro

| Tipo de Encontro | Conteúdo formativo |
|---|---|
| Escalada | `PALESTRA` |
| ESPPA | `PALESTRA` |
| AVC | `BATE_PAPO` |
| Acampamento | Não possui conteúdo formativo deste domínio |

## Catálogo fixo de temas

- Os temas são fixos e definidos em código.
- A interface não oferece criação ou edição livre de temas.
- O catálogo real está definido no registry
  `backend/core/formacao_catalogo.py`: Escalada e ESPPA compartilham nove
  palestras, enquanto AVC possui onze bate-papos próprios.
- Não haverá CRUD administrativo de temas.
- Código, título, tipo, ordem e bloco/momento são metadados imutáveis em código;
  alterar o registry não exige migration.

## Sessão formativa e preservação histórica

- Uma sessão formativa pertence a um Encontro e representa a realização de um
  conteúdo do catálogo aplicável ao tipo daquele Encontro.
- O conceito previsto é `SessaoFormativa`, com Encontro, conteúdo/tema e
  `title_snapshot` ou mecanismo histórico equivalente.
- O snapshot do título preserva a leitura histórica caso a representação do
  catálogo em código seja alterada no futuro.
- Dia e horário da palestra ou do bate-papo não são requisitos obrigatórios
  atuais deste domínio.

## Palestrantes

- Uma sessão pode possuir múltiplos palestrantes.
- O palestrante Alpinista deve usar o vínculo canônico com
  `Pessoa`/`PerfilAlpinista`, conforme o desenho técnico a ser fechado na
  D.4A.
- O palestrante externo não cria `Pessoa` permanente. É armazenado somente o
  nome necessário para exibição e preservação histórica.
- O palestrante externo continua aparecendo no quadrante e na sessão mesmo sem
  cadastro de Alpinista.
- Cada entrada de palestrante representa exatamente uma alternativa: Alpinista
  ou nome externo, nunca ambos e nunca nenhum.

## Histórico formativo do Alpinista

- Somente a atuação efetiva como palestrante ou responsável por bate-papo entra
  no histórico individual.
- A apresentação conceitual do registro é:
  `Palestrante — Tema — Encontro`.
- Esse histórico é consultivamente semelhante a um trabalho, mas não é
  `TrabalhoEncontro`, alocação em equipe ou histórico de equipe.
- Convite, indicação ou planejamento sem realização efetiva não incrementa o
  histórico formativo.

## Regras por tipo de Encontro

### Escalada e ESPPA

- Normalmente a sessão seleciona um Alpinista como palestrante.
- Quando nenhum Alpinista puder assumir, é permitido registrar palestrante
  externo.
- O palestrante externo não gera `Pessoa`.

### AVC

- O palestrante do bate-papo deve estar trabalhando naquele mesmo AVC.
- Essa condição é uma invariante bloqueante.
- Palestrante externo não é exceção para AVC.

### Acampamento

- Não recebe `SessaoFormativa` deste domínio.

## Autorização

- Formação, Diretoria e Suporte podem montar ou alterar sessões e
  palestrantes.
- Fichas não gerencia palestrantes.
- Os demais papéis não recebem permissão de gestão por causa deste domínio.
- A visualização continua seguindo a matriz geral de autorização.
- O superuser permanece como bypass técnico separado e não se torna papel de
  negócio.

## Separação de domínios

O domínio de Formação em Encontros não:

- cria `Frequencia`;
- altera `TrabalhoEncontro` ou equipes;
- cria `PerfilAlpinista`;
- cria `Pessoa` para palestrante externo;
- mistura histórico formativo com histórico de equipe.

## Compatibilidade

A evolução segue:

`EXPAND` → `POPULATE`, somente quando seguro → `COMPAT` → `CUTOVER` →
`DEPRECATE`.

A D.4A deve inspecionar o legado real relacionado a palestras, funções,
históricos e quadrantes antes do desenho técnico. Nenhum backfill heurístico é
permitido.
