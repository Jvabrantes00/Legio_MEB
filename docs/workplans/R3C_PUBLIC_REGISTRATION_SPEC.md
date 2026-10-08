# R.3C — Ficha pública de Escalada e ESPPA

## Status e objetivo

Esta é a especificação funcional oficial da ficha pública de inscrição de
Escalada e ESPPA. Ela complementa a
[[R3C_ENCONTROS_ARCHITECTURE|arquitetura do Workspace/Encontristas]] sem
definir schema, contratos técnicos ou layout visual final. AVC e Acampamento
não usam esta ficha.

## Princípios

- A ficha representa somente os dados declarados para um Encontro específico.
- A inscrição não cria Alpinista, `PerfilAlpinista`, Grupo, vínculos
  institucionais, vínculos familiares canônicos ou histórico de participação.
- A submissão não associa ou sobrescreve `Pessoa` automaticamente.
- A superfície pertence ao mesmo frontend Next.js, mas fica isolada da
  aplicação privada, não exige login e é acessada normalmente por link no site
  do Movimento.
- Nenhum registro definitivo é criado antes da confirmação final.

## Fluxo

1. Abrir o formulário.
2. Preencher e validar os dados.
3. Avançar para revisão.
4. Revisar todas as seções.
5. Voltar e editar, se necessário.
6. Finalizar a inscrição.
7. Criar `InscricaoEncontro` somente nesse momento.
8. Mostrar mensagem de sucesso.

Não existe rascunho persistido na v1. Abandonar o fluxo antes da finalização
não cria inscrição definitiva.

## Campos compartilhados

Escalada e ESPPA compartilham identificação, contato, endereço, responsável
de menor, sacramentos, cuidado e acolhimento, origem do contato e revisão.

### Identificação do participante

| Campo | Obrigatoriedade |
|---|---|
| Nome completo | Obrigatório |
| Apelido | Opcional |
| Data de nascimento | Obrigatória |
| CPF do participante | Opcional |

O CPF do participante é semanticamente diferente do CPF do responsável. O
CPF do responsável não pode ser usado para deduplicar o participante.

### Contato do participante

Pelo menos um dos campos abaixo precisa ser informado:

- e-mail;
- WhatsApp/telefone.

Qualquer um sozinho ou ambos são válidos. Não se exige e-mail de quem possui
somente telefone/WhatsApp. Quando ambos existirem, a futura campanha poderá
entregar a mesma oportunidade pelos dois canais.

### Endereço

| Campo | Obrigatoriedade |
|---|---|
| CEP | Obrigatório |
| Logradouro | Obrigatório |
| Número | Obrigatório |
| Complemento | Opcional |
| Bairro | Obrigatório |
| Cidade | Obrigatória |
| UF | Obrigatória |

Integração automática de CEP não foi decidida.

### Como conheceu o Movimento Escalada

A pergunta comum às duas modalidades é:

> Como conheceu o Movimento Escalada?

Opções:

- Indicação de amigo/familiar;
- Paróquia;
- Redes sociais;
- Já conhecia o Movimento Escalada;
- Outro.

Ao selecionar **Outro**, a especificação textual é obrigatória.

## Menores e responsável

A data de nascimento determina a exibição da seção de responsável legal. Para
participante menor de 18 anos, a seção é obrigatória. O menor pode se inscrever
sem CPF próprio; o CPF do responsável não ocupa o campo do participante.

| Campo do responsável | Obrigatoriedade |
|---|---|
| Nome completo | Obrigatório |
| CPF | Obrigatório na v1 |
| Parentesco | Obrigatório |
| WhatsApp/telefone | Obrigatório |
| E-mail | Opcional |

O responsável não precisa existir como `Pessoa`. O mesmo CPF pode constar em
inscrições de irmãos. A ficha não cria vínculo familiar canônico.

## Sacramentos

A ficha mantém Batismo, Primeira Comunhão e Crisma. Cada resposta é
trivalente: **Sim**, **Não** ou **Não informado / Não sei**. Essa semântica
preserva compatibilidade conceitual com `Pessoa`. As respostas não devem ser
devolvidas desnecessariamente em contratos públicos.

## Cuidado e acolhimento

A seção se chama **Informações importantes para cuidado e acolhimento**. Sua
finalidade é preparar a equipe, nunca excluir automaticamente alguém.

### Alergias

- possui alergia: Sim/Não;
- quais, quando a resposta for Sim.

### Intolerâncias e restrições

- possui intolerância ou restrição alimentar: Sim/Não;
- quais, quando a resposta for Sim.

### Medicamentos

- usa medicamento durante o Pré-Encontro ou Encontro: Sim/Não;
- medicamento, horário(s) e observações necessárias quando a resposta for
  Sim.

### Neurodivergência e necessidade de apoio

A pergunta identifica se existe neurodivergência, condição ou necessidade de
apoio que a equipe deva conhecer. As respostas conceituais são **Não**,
**Sim** e **Prefiro não informar**. Quando aplicável, a pessoa pode declarar:

- condição ou neurodivergência, se desejar;
- sensibilidades ou situações de desconforto;
- o que costuma ajudar nesses momentos;
- outras informações relevantes ao cuidado.

Diagnóstico não é requisito de participação. A formulação final dos campos e
avisos permanece pendente na especificação de UX.

## Campos específicos do ESPPA

Esses campos não aparecem na Escalada somente para uniformizar formulários.

### Estado civil

ESPPA solicita estado civil. A lista final pode refletir o domínio existente,
desde que comporte a lógica de cônjuge e pessoa de referência.

### Cônjuge

Quando a pessoa se declarar casada, solicitar nome e telefone do cônjuge. Não
solicitar CPF ou e-mail. Os dados são declarativos e não criam
`VinculoConjugal` automaticamente.

### Pessoa de referência

Quando não houver cônjuge conforme a situação declarada, solicitar nome,
relação com o participante e telefone. As relações conceituais podem incluir
Pai/Mãe, Irmão/Irmã, Outro familiar, Amigo(a) e Outro. Não solicitar CPF ou
e-mail nem criar vínculo familiar.

## Revisão e finalização

A revisão apresenta os dados nas mesmas seções do formulário e oferece
**Voltar e editar** e **Finalizar inscrição**. O layout visual final não é
definido aqui.

Após a finalização, a interface confirma o recebimento, por exemplo:

> Inscrição enviada com sucesso.

A mensagem informa que a inscrição foi recebida e que a pessoa deve aguardar
o contato ou convite da equipe. Não expõe identificadores internos.

## Edição e cancelamento

Enquanto a janela estiver aberta, a pessoa poderá futuramente editar a
inscrição, cancelar sem apagar o registro e reativar a inscrição cancelada sem
criar uma segunda inscrição lógica. Depois do encerramento, alterações passam
por Fichas.

O mecanismo público seguro de acesso permanece pendente; esta especificação
não define token.

## Snapshot

A submissão final segue a direção híbrida aprovada:

- campos estruturados necessários à operação e resolução;
- snapshot versionado que preserva o declarado.

O schema final não é definido aqui. Alterações posteriores em `Pessoa` ou nos
dados operacionais não reescrevem o snapshot original.

## Resolução cadastral

`InscricaoEncontro` pode existir sem `Pessoa`. O backend poderá sugerir
possíveis correspondências, mas Fichas decide entre vincular uma Pessoa,
rejeitar a correspondência, criar nova Pessoa ou aplicar seletivamente
atualizações cadastrais.

Não há associação ou merge automático. O CPF do participante é sinal forte,
mas não decisão automática.

## Pré-Encontro

No Pré-Encontro, Fichas poderá confirmar presença, conferir dados de cuidado,
atualizar informações operacionais, tirar/adicionar foto e regularizar a ficha.
Essas ações não alteram retroativamente o snapshot declarado.

Foto não é solicitada na ficha pública: será tirada no Pré-Encontro e
adicionada posteriormente por Fichas.

## Privacidade e autorização

Dados de cuidado são restritos a Fichas, Diretoria, Suporte e coordenadores
contextualmente autorizados naquele Encontro. O acesso do coordenador é
temporário e restrito ao Encontro, termina em `FINALIZADO` ou `CANCELADO` e
não termina apenas por `ADIADO`. Isso não concede capability global.

Esses dados não aparecem em Calendário, Agenda, MME, busca genérica, seleção
de equipe, relatórios gerais ou superfícies sem necessidade operacional.

A resposta pública retorna somente o necessário. Ela não expõe dados completos
de Pessoa, correspondências internas, outros inscritos, sacramentos, saúde,
IDs internos desnecessários ou informações de autorização.

## Validações

A ficha deve validar:

- nome completo e data de nascimento obrigatórios;
- pelo menos e-mail ou WhatsApp/telefone;
- CEP, logradouro, número, bairro, cidade e UF obrigatórios;
- responsável obrigatório para menor;
- CPF do responsável obrigatório na v1;
- cônjuge ou pessoa de referência conforme a situação do ESPPA;
- detalhes condicionais de alergia, restrição, medicamento e cuidado;
- texto obrigatório quando **Outro** exigir especificação.

Esta especificação não escolhe biblioteca, máscara ou implementação frontend.

## Fora de escopo

Não pertencem à ficha pública:

- Status de Alpinista e outros status administrativos internos;
- Grupo e `PerfilAlpinista`;
- Violeiro, canto, MME ou disponibilidade para MME;
- Equipe de Trabalho;
- histórico institucional ou de participação;
- permissões e papéis internos;
- foto;
- informações técnicas do SIA;
- AVC e Acampamento.

## Pendências

Permanecem **PENDENTES**:

- schema definitivo de `InscricaoEncontro` e do snapshot;
- token ou outro mecanismo para edição/cancelamento;
- captcha, antiabuso e throttling;
- máscaras e integração de CEP;
- layout visual final;
- texto final de consentimentos e avisos;
- mecanismo técnico de comparação cadastral;
- model final de presença no Pré-Encontro;
- model final dos dados operacionais de cuidado.

Nenhuma dessas pendências é resolvida implicitamente por esta especificação.
