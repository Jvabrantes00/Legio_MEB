# R.3C — Arquitetura do Workspace/Encontristas

## Status e escopo

R.3C.1 auditou a modelagem atual de convites e R.3C.2 auditou a ficha de
inscrição e os dados cadastrais sem alterar arquivos. R.3C.3 consolida as
decisões humanas tomadas depois dessas auditorias.

Este documento descreve arquitetura funcional, fronteiras e responsabilidades.
Ele não define schema final, contratos definitivos, migrations ou decomposição
de implementação. R.3 permanece aberta.

A especificação funcional dos campos, condicionais, validações e revisão da
ficha está em
[[R3C_PUBLIC_REGISTRATION_SPEC|R.3C — Ficha pública de Escalada e ESPPA]].
Este documento arquitetural continua responsável pelas fronteiras, fluxos e
entidades conceituais; a especificação da ficha não congela schema técnico.

A modelagem aprovada de entidades, relações, constraints, locks, APIs e cutover
está em
[[R3C_ENCONTRISTAS_TECHNICAL_MODEL|R.3C.5 — Modelagem técnica de Encontristas]].
Ela foi revisada humanamente na R.3C.6 e não representa schema implementado.

## Decisões aprovadas

### Configuração de encontristas

Cada Encontro abrangido pelo fluxo terá conceitualmente uma
`ConfiguracaoEncontristasEncontro`, separada de `Encontro`, contendo ao menos:

- capacidade;
- idade mínima e máxima;
- abertura e encerramento das inscrições.

O prazo da campanha de convites pertence ao fluxo da campanha, não
necessariamente a essa configuração. Na v1, Fichas o define manualmente.

### Elegibilidade por idade e conclusão anterior

A faixa etária é configurada por Encontro e calculada com as datas oficiais:

- a idade mínima deve ser atingida até o último dia oficial, inclusive;
- a pessoa precisa estar dentro da idade máxima no primeiro dia oficial;
- ultrapassar o máximo durante o Encontro não retira a elegibilidade;
- quem ainda não atingiu a idade mínima hoje, mas a atingirá até o último dia,
  permanece elegível e gera aviso informativo para Fichas.

Quem já concluiu Escalada não pode participar novamente de outra Escalada.
Quem já concluiu ESPPA não pode participar novamente de outro ESPPA. Essas
regras não impedem trabalho em Encontros futuros.

### Inscrição por Encontro

A futura inscrição representa **Pessoa × Encontro**, e não Pessoa × tipo. A
mesma pessoa pode manter inscrições históricas em edições diferentes.

Será criada futuramente uma nova `InscricaoEncontro`, de forma expansiva, sem
remodelar destrutivamente a `Inscricao` atual. A nova inscrição:

- pertence a um Encontro;
- pode nascer sem vínculo com uma `Pessoa` canônica;
- admite origem pública e regularização administrativa por Fichas;
- preserva a submissão original;
- coexistirá com a inscrição legada durante o cutover.

A constraint final de identidade lógica permanece pendente porque a inscrição
pode existir antes da resolução da Pessoa.

### Superfície pública

Escalada e ESPPA terão formulário público. AVC e Acampamento ficam fora desse
fluxo. A superfície será construída no mesmo projeto Next.js, porém isolada
visual e arquiteturalmente da aplicação autenticada. O usuário público não
faz login no SIA e não acessa menus, Pessoas, Encontros internos, Calendário ou
outros módulos privados.

Os contratos e endpoints serão próprios e mínimos. Não será reutilizado
diretamente `POST /alpinistas/`, nem serão tornadas públicas APIs privadas.
Permanecem obrigatórios:

- default deny nas superfícies internas;
- BFF adequado, sem JWT exposto ao browser;
- proteção CSRF e validação exata de Origin;
- respostas minimizadas, sem PII desnecessária;
- operações públicas específicas para submissão e, quando permitido, edição
  e cancelamento.

Throttling, captcha e demais controles contra abuso ainda não estão definidos.

### Envio, edição e cancelamento da inscrição

Não haverá rascunho persistido na v1. O fluxo público será:

```text
preencher -> revisar -> voltar e editar -> finalizar -> criar InscricaoEncontro
```

Somente a finalização cria o registro definitivo. Depois dela, a interface
mostra confirmação simples de recebimento.

Enquanto a janela estiver aberta, a pessoa poderá editar ou cancelar a própria
inscrição. Cancelamento não apaga o registro. Uma inscrição cancelada pode ser
reativada na mesma janela sem criar uma segunda inscrição lógica. Depois do
encerramento, mudanças dependem de Fichas. O mecanismo público seguro para
recuperar a inscrição permanece pendente.

### Snapshot e resolução cadastral

A direção preferida é híbrida:

- campos estruturados necessários a consulta e resolução;
- snapshot versionado da submissão.

O snapshot preserva o que foi declarado e nunca é reescrito para aparentar
uma submissão diferente. A inscrição não sobrescreve `Pessoa`, não associa
automaticamente uma Pessoa, não cria `PerfilAlpinista` e não cria vínculos
institucionais.

O backend pode localizar possíveis Pessoas, mas a correspondência é apenas um
sinal para Fichas. Fichas decide entre:

- vincular uma Pessoa existente;
- rejeitar uma correspondência;
- criar uma Pessoa;
- aplicar seletivamente atualizações cadastrais.

Dados divergentes devem ser apresentados comparativamente. Nenhuma
correspondência, inclusive por CPF, autoriza associação ou merge automático.

### CPF e responsável de menor

CPF do participante e CPF do responsável são conceitos distintos:

- o CPF do participante é opcional e constitui sinal forte, mas insuficiente
  para auto-merge;
- o CPF do responsável não participa da deduplicação do participante e pode
  aparecer em inscrições de irmãos;
- menor sem CPF próprio pode se inscrever.

Para menor, responsável é obrigatório. A ficha deverá poder coletar nome,
CPF, parentesco, telefone/WhatsApp, e-mail e os demais campos que vierem a ser
aprovados. O responsável não precisa existir como `Pessoa`, e a submissão não
cria automaticamente vínculo familiar canônico.

### Dados de cuidado

A ficha pública deverá reunir informações úteis ao cuidado e acolhimento:

- alergias;
- intolerâncias e restrições;
- medicamentos e horários;
- neurodivergência;
- necessidades de apoio;
- sensibilidades ou situações de desconforto;
- informações sobre o que costuma ajudar a pessoa.

A finalidade é preparar a equipe. Esses dados não podem alimentar exclusão
automática. Os campos exatos e sua UX permanecem pendentes.

### Pré-Encontro

O Pré-Encontro é condição obrigatória para participar do Encontro principal:

```text
CONFIRMADO + ausência no Pré-Encontro -> não participa do fim de semana
```

Sua presença é fato distinto de `ParticipacaoEncontro`, que continua
representando o resultado do Encontro principal. A estrutura futura deve
registrar comparecimento, ator, momento, Encontro e relação com inscrição ou
Pessoa quando disponível.

Na v1 existe no máximo um Pré-Encontro por Encontro. Havendo mais presentes
elegíveis que vagas, o sistema preserva as presenças e aguarda decisão da
Diretoria, sem prioridade por check-in e sem overbooking.

Fichas pode regularizar situações excepcionais:

- inscrito sem confirmação que compareça ao Pré-Encontro pode ter presença
  registrada e situação regularizada, se cumprir as regras e houver vaga;
- pessoa sem ficha prévia não é excluída automaticamente: Fichas registra a
  situação e completa ou cria a ficha depois, preservando a regularização no
  histórico.

Não será exigido o preenchimento integral da ficha na porta. Capacidade e
demais regras continuam obrigatórias. O model final da presença permanece
pendente.

### Capacidade

A capacidade é limite real e não admite overbooking automático. Durante a
campanha, confirmações ocupam vagas de planejamento. No Pré-Encontro, a
presença obrigatória determina quem está apto ao Encontro principal, sempre
dentro do limite vigente.

Somente Diretoria e Suporte podem alterar capacidade. Fichas não a altera
diretamente. Toda alteração deverá guardar valor anterior, valor novo, ator e
data/hora. Aumento pode reabrir vagas e o fluxo da lista de espera. Redução não
pode produzir capacidade inferior à ocupação ou aptidão já existente.

### Reprogramação

Reprogramar as datas oficiais recalcula a elegibilidade e registra que a
mudança decorreu da reprogramação:

- ainda sem convite: elegibilidade é atualizada automaticamente;
- já convidada e agora inelegível: confirmação fica suspensa e Fichas recebe
  revisão obrigatória para manter ou cancelar conscientemente;
- já confirmada: não há cancelamento automático; o caso é marcado para revisão
  por Fichas.

O comportamento quando não houver calendário oficial suficiente para calcular
idade permanece pendente.

## Entidades conceituais

Os nomes abaixo orientam responsabilidades; não congelam models ou campos:

- `ConfiguracaoEncontristasEncontro`: capacidade, faixa etária e janela;
- `InscricaoEncontro`: inscrição específica da edição, inclusive antes da
  resolução cadastral;
- `CampanhaConvitesEncontro`: operação de convite iniciada por Fichas;
- `RodadaConvitesEncontro`: ciclo de oportunidades, inclusive reposição;
- `OportunidadeConviteEncontro`: link e resposta daquela pessoa naquela
  rodada; nome provisório;
- `EntregaConviteEncontro`: tentativa e resultado por canal;
- estrutura própria de presença no Pré-Encontro;
- estrutura de auditoria histórica sensível.

`ConviteEncontro` permanece o vínculo lógico Pessoa × Encontro × finalidade.
Ele não vira uma linha por rodada. Convite representa estado lógico de
negócio; oportunidade representa aquele link/rodada; entrega representa o
estado daquele canal. `ParticipacaoEncontro` continua reservado ao resultado
real do Encontro principal.

## Fluxos

### Campanha de convites

Fichas inicia manualmente a campanha por ação equivalente a **Iniciar envio de
convites**. O sistema registra ator e momento. Antes disso não há disparo
automático. Depois do início, a campanha processa pessoas elegíveis enquanto
houver vagas.

Convite enviado não reserva vaga e não é necessário aguardar recusa:

```text
confirmados < capacidade -> campanha pode continuar enviando
confirmados == capacidade -> novos envios normais param
```

Na v1, Fichas define data/hora final para confirmação. Configurações
incoerentes devem ser rejeitadas. No prazo, a campanha para e oportunidades
pendentes deixam de aceitar confirmação. Fichas decide entre prorrogar ou
encerrar com os confirmados existentes.

### Prorrogação, rodadas e lista de espera

Prorrogação não revalida links antigos. Uma nova oportunidade ou rodada é
criada quando necessário. Podem voltar automaticamente ao fluxo:

- quem não respondeu;
- quem teve falha de entrega e voltou a ter canal utilizável;
- quem ainda não havia sido convidado.

Recusa explícita não é reaberta automaticamente; somente Fichas pode fazê-lo
manualmente.

Quando a capacidade é atingida, as pessoas elegíveis restantes compõem a
lista de espera. Se uma vaga reabrir, uma nova rodada oferece oportunidade a
todas as pessoas elegíveis da lista: a primeira confirmação válida ocupa a
vaga e as demais permanecem esperando. Não há promoção sem confirmação.

### Links e respostas

Cada rodada produz novas oportunidades; links anteriores não voltam a valer.
Quando uma vaga é preenchida, oportunidades concorrentes restantes não podem
ocupar outra vaga. A validade pode ser configurável e não terá prazo universal
fixado nesta etapa.

O link sozinho não autoriza resposta. O fluxo aprovado é:

```text
link individual -> confirmação da data de nascimento -> confirmar ou recusar
```

A solução futura deve usar token imprevisível, limitar tentativas, minimizar
informação, tornar o link somente leitura após resposta e invalidá-lo por
rodada, suspensão ou expiração. Data de nascimento não é senha permanente.
MeuSIA fica fora desta etapa.

### Canais, falhas e reenvios

Com e-mail e WhatsApp disponíveis, a mesma oportunidade é entregue pelos dois.
Com apenas um canal, usa-se o disponível. Sem canal, a inscrição continua
válida, Fichas recebe pendência e a campanha prossegue.

Falha de entrega não equivale a recusa nem bloqueia a campanha. O desenho
futuro prevê retries automáticos limitados, reenvio manual, idempotência e
histórico de tentativas. Reenvio na mesma oportunidade não cria novo convite
lógico. Quantidade e intervalo dos retries estão pendentes.

E-mail terá envio automático e adaptador desacoplado do provedor. Desenvolvimento
usará SMTP local de teste/Mailpit; homologação poderá usar SMTP temporário
controlado; produção usará SMTP institucional quando disponível. Credenciais e
remetente são configuração de ambiente e nunca entram no repositório.

WhatsApp usará adaptador mock na v1 de desenvolvimento, capaz de simular
sucesso e falha. Nenhum provedor real foi escolhido.

## Autorização

- Fichas administra inscrições, resolução cadastral, campanha, oportunidades,
  regularizações e presença no Pré-Encontro, dentro dos comandos aprovados.
- Diretoria e Suporte podem alterar capacidade; Fichas não pode.
- Dados de cuidado são acessíveis a Fichas, Diretoria, Suporte e coordenadores
  contextualmente autorizados no Encontro correspondente.
- O coordenador contextual é membro da EquipeEncontro **Coordenação Geral** e
  seu acesso deriva da cadeia canônica de identidade e `TrabalhoEncontro`, sem
  cadastro paralelo. A capability não é global, termina em `FINALIZADO` ou
  `CANCELADO` e não termina apenas por `ADIADO`.
- Ausência de permissão explícita continua negada por default.

Essa especificação registra autorização futura e não declara essas
capabilities como já implementadas na matriz atual.

## Privacidade

Snapshots, dados cadastrais, responsáveis e dados de cuidado não podem vazar
para Calendário, Agenda, MME, busca genérica, montagem de equipe, relatórios
gerais ou qualquer superfície sem necessidade. A resposta pública deve ser
mínima e nunca devolver PII desnecessária.

O snapshot declarado e os dados canônicos comparados permanecem distintos.
Aplicação seletiva de mudanças exige ação de Fichas; correção cadastral não
apaga a evidência histórica da submissão.

## Concorrência

A última vaga deve ser ocupada atomicamente. A implementação futura deverá
usar transações, locks e constraints compatíveis com PostgreSQL para impedir
qualquer estado acima da capacidade, inclusive concorrência entre resposta
pública, confirmação manual e redução de capacidade.

O processamento de campanhas, oportunidades, entregas e retries deve ser
idempotente. Esta etapa não escolhe o desenho de locks nem as constraints
finais.

## Processamento assíncrono

A direção arquitetural aprovada é:

```text
PostgreSQL = fonte de verdade
Redis      = fila/broker
Celery     = processamento assíncrono
Beat       = prazos, retries, reconciliação e verificações temporais
```

Ações imediatas devem enfileirar tarefas imediatas; Beat não será usado para
polling agressivo. Jobs precisam ser idempotentes. Redis e Celery não são
instalados nem configurados nesta etapa, e os detalhes de deploy permanecem
pendentes.

## Auditoria

Correções históricas sensíveis posteriores a `FINALIZADO`, como participação
e trabalho/equipe, deverão registrar:

- ator e timestamp;
- entidade ou fato alterado;
- valor anterior e novo;
- justificativa obrigatória;
- Encontro.

Alterações de capacidade também exigem trilha com valores anterior e novo.
Ações posteriores normais, como adicionar fotos, não exigem justificativa.
A preferência é não depender exclusivamente de `LogSistema`, mas o model final
de auditoria ainda não foi decidido.

## Compatibilidade e limites

- `Inscricao` atual permanece durante o cutover; não há alteração destrutiva.
- `ConviteEncontro` mantém sua identidade lógica e sua finalidade.
- `ParticipacaoEncontro` não é presença de Pré-Encontro.
- Confirmação continua diferente de participação real.
- Nenhum envio público cria `PerfilAlpinista` ou vínculo institucional.
- A arquitetura não define nesta etapa models, status, endpoints, migrations,
  dependências ou componentes de interface definitivos.

## Pendências explícitas

Permanecem **PENDENTES**:

- formulação final de UX, consentimentos e avisos da seção de cuidado;
- schema final do snapshot e de `InscricaoEncontro`;
- models e status finais de campanha, rodada, oportunidade e entrega;
- mecanismo público seguro para editar/cancelar inscrição enviada;
- formato, armazenamento e expiração exatos dos tokens;
- captcha, throttling e controles contra abuso;
- provedor real de WhatsApp;
- SMTP institucional definitivo;
- model final de presença no Pré-Encontro;
- model final de auditoria;
- detalhes operacionais do deploy Redis/Celery;
- URL pública definitiva;
- comportamento sem calendário oficial suficiente para calcular idade;
- desenho final de locks, constraints e resolução de corridas;
- decomposição de implementação, contratos e cutover.

Essas pendências precisam ser fechadas na medida necessária antes da
decomposição de implementação. Nenhuma deve ser resolvida implicitamente.
