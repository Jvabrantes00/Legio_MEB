# Inscrição, Convite e Participação em Encontros

Este documento registra as regras estáveis do domínio de inscrição, convite,
participação e conclusão de Encontros. Decisões de implementação, progresso e
histórico da Fase 1B.3D.2 pertencem ao
[[../workplans/PHASE_1B_D2|workplan da fase]].

## Separação conceitual

- Inscrição não é convite.
- Convite não é confirmação.
- Confirmação não é participação.
- Participação não é conclusão.
- A conclusão de Escalada ou ESPPA pode criar `PerfilAlpinista`.
- Nenhuma dessas etapas cria `Frequencia` automaticamente.

## Inscrição

- A inscrição existe inicialmente para Escalada e ESPPA.
- Os formulários são permanentes; a inscrição não pertence inicialmente a uma
  edição específica de `Encontro`.
- `PENDENTE` representa a fila geral de espera. Não existe uma entidade
  separada de lista de espera.
- A inscrição nasce como `PENDENTE` e permanece ou retorna a esse estado quando
  a Pessoa:
  - não é convidada para uma edição;
  - é convidada, mas não confirma;
  - confirma, mas falta, desiste ou não conclui.
- Uma conclusão válida de Escalada ou ESPPA cumpre e encerra a inscrição.
- A data da inscrição não gera prioridade automática. A escolha das Pessoas
  convidadas é humana.
- Não pode haver duas inscrições pendentes ativas da mesma `Pessoa` para o
  mesmo tipo. A implementação concreta dessa constraint será definida na
  D.2A.

## Convite

- O convite é específico de um `Encontro`.
- `ConviteEncontro` representa pelo menos a Pessoa, o Encontro, a finalidade,
  o status e, opcionalmente, a inscrição.
- As finalidades são `PARTICIPAR` e `TRABALHAR`.
- `TRABALHAR` existe estruturalmente para evitar redesenho futuro; o domínio
  completo de trabalho e equipes está fora da D.2.
- Os status conceituais iniciais são `CONVIDADO`, `CONFIRMADO`, `RECUSADO` e
  `SEM_RESPOSTA`.
- `CONFIRMADO` pertence ao convite. Confirmar um convite não cria
  `ParticipacaoEncontro`.
- Escalada e ESPPA podem relacionar o convite de participação à inscrição.
- AVC e Acampamento não possuem inscrição pública e usam convite direto.

## Participação

- `ParticipacaoEncontro` registra o resultado real da participação.
- A participação aponta para `Pessoa`, não para `PerfilAlpinista`, pois
  candidatos de Escalada e ESPPA ainda podem não ser Alpinistas.
- Os resultados são `CONCLUIU`, `FALTOU` e `DESISTIU`. Não existe resultado
  `CONFIRMADO`.
- Não há participação diária genérica nesta fase.
- Pode existir no máximo um resultado da mesma `Pessoa` no mesmo `Encontro`.

## Conclusão e PerfilAlpinista

- A Pessoa se torna oficialmente Alpinista somente quando conclui Escalada ou
  ESPPA.
- Inscrição, convite, confirmação, `FALTOU` e `DESISTIU` não criam
  `PerfilAlpinista`.
- `CONCLUIU` em Escalada ou ESPPA cria `PerfilAlpinista` se ele ainda não
  existir.
- Uma vez Alpinista, a Pessoa permanece Alpinista. O estado ativo ou inativo
  continua pertencendo ao domínio de frequência.
- A conclusão de um Encontro não gera `Frequencia` automaticamente.

## Conclusão única

- Uma Pessoa pode faltar, desistir e tentar novamente em uma edição futura.
- Cada tipo elegível pode ser concluído no máximo uma vez por Pessoa:
  Escalada, ESPPA, AVC e Acampamento.
- A implementação da regra no banco e no service layer será definida na D.2A.

## Elegibilidade essencial

### Escalada

- A faixa padrão de entrada é de 13 a 17 anos.
- Uma inscrição fora da faixa pode existir; a condição gera aviso e decisão
  humana, não bloqueio estrutural.
- Uma Pessoa com 17 anos na inscrição pode completar 18 antes do Encontro.
- Escalada só pode ser concluída uma vez.

### ESPPA

- A entrada ocorre normalmente a partir dos 18 anos.
- Quem concluiu Escalada pode participar posteriormente de ESPPA.
- ESPPA só pode ser concluído uma vez.

### AVC

- É elegível somente quem concluiu Escalada; concluir apenas ESPPA não torna a
  Pessoa elegível.
- O primeiro ano elegível é o ano da Escalada mais dois.
- Não possui inscrição pública e usa convite direto.
- AVC só pode ser concluído uma vez.

### Acampamento

- É destinado a quem concluiu Escalada.
- Não possui inscrição pública e usa convite direto.
- Acampamento só pode ser concluído uma vez.

## Compatibilidade

O legado deve ser migrado incrementalmente:

`EXPAND` → `POPULATE`, quando seguro → `COMPAT` → `CUTOVER` → `DEPRECATE`.

Existe comportamento legado conhecido que pode criar ou ativar Alpinista cedo
demais. Sua localização técnica será registrada no workplan durante a D.2A.

