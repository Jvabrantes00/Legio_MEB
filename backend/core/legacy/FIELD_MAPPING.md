# Matriz de compatibilidade do schema legado

Estados: `DIRECT` preserva o conceito; `TRANSFORM` normaliza/valida;
`DEFERRED` aguarda domínio ou decisão; `RAW_ONLY` preserva somente na staging;
`DERIVED` será recalculado; `UNKNOWN` exige profiling.

Nenhum “destino futuro” listado cria compromisso de modelagem nesta fase.

## `adm_usu`

| Campo | Significado conhecido | Destino canônico/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `usu_nome` | nome do usuário | texto normalizado | `User`/perfil a definir | TRANSFORM |
| `usu_login` | login legado | texto/legacy_id | `User.username` sob política futura | TRANSFORM |
| `usu_senha` | credencial histórica | descartada; issue segura e rotação | nenhum | RAW_ONLY |
| `usu_tipo` | tipo/papel legado | mapping vazio `usu_tipo -> SiaRole` | `Group` | DEFERRED |
| `grupo` | grupo textual legado | preservado sem associar pessoa | domínio de grupo futuro | DEFERRED |

## `ajuda`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_AJUDA` | ID da mensagem | legacy_id | suporte/comunicação a definir | DEFERRED |
| `NO_AJUDA_REMETENTE` | remetente textual | preservar na staging | a definir | RAW_ONLY |
| `NO_AJUDA_DESTINATARIO` | destinatário textual | preservar na staging | a definir | RAW_ONLY |
| `TX_AJUDA_ASSUNTO` | assunto | texto normalizado futuro | a definir | DEFERRED |
| `TX_AJUDA_TEXTO` | mensagem | dado pessoal potencial | a definir | DEFERRED |
| `DT_AJUDA` | data/hora | datetime legado | a definir | TRANSFORM |
| `TX_AJUDA_LIDA` | estado de leitura | vocabulário desconhecido | a definir | UNKNOWN |
| `TX_AJUDA_PRIORIDADE` | prioridade | vocabulário desconhecido | a definir | UNKNOWN |

## `alpinista`

| Campo | Significado conhecido | Destino canônico/transformação | Destino Django futuro | Estado |
|---|---|---|---|---|
| `CD_REGISTRO` | ID legado | `legacy_id`, inteiro positivo | crosswalk para `Alpinista.id` | TRANSFORM |
| `DC_REGISTRO` | código textual | metadata | a definir | UNKNOWN |
| `DT_ENTRADA` | entrada/cadastro | datetime preservado | campo futuro se aprovado | DEFERRED |
| `NO_ALPINISTA` | nome | trim + Unicode NFC | `Alpinista.nome` | TRANSFORM |
| `DT_NASCIMENTO` | nascimento | data ISO validada | `Alpinista.dataNascimento` | TRANSFORM |
| `TX_APELIDO` | apelido | texto canônico | campo futuro | DIRECT |
| `TX_ENDERECO` | logradouro/endereço | `CanonicalAddress.street` | endereço remodelado | TRANSFORM |
| `CD_CEP` | CEP | oito dígitos | endereço remodelado | TRANSFORM |
| `CD_DDD` | DDD principal | combinado apenas com telefone local | contato remodelado | TRANSFORM |
| `NR_TELEFONE` | telefone principal legado | dígitos, sem escolher precedência | contato remodelado | TRANSFORM |
| `NR_TELEFONE1` | telefone alternativo | dígitos; conflito explícito | contato remodelado | TRANSFORM |
| `NO_PAI` | nome do pai | responsável `PAI` | responsáveis futuros | TRANSFORM |
| `NR_PAITELEFONE` | telefone do pai | telefone normalizado | responsáveis futuros | TRANSFORM |
| `NO_MAE` | nome da mãe | responsável `MAE` | responsáveis futuros | TRANSFORM |
| `NR_MAETELEFONE` | telefone da mãe | telefone normalizado | responsáveis futuros | TRANSFORM |
| `NO_CIDADE` | cidade | `CanonicalAddress.city` | endereço remodelado | TRANSFORM |
| `SG_UF` | UF | sigla brasileira validada | endereço remodelado | TRANSFORM |
| `IN_SEXO` | marcador legado | vocabulário/semântica pendente | a definir | UNKNOWN |
| `IN_BAIRRO` | bairro | `CanonicalAddress.district` | endereço remodelado | TRANSFORM |
| `NO_ESCALADA` | evidência histórica | `deferred` | Participações/Encontros | DEFERRED |
| `NO_ESPPA` | evidência histórica | `deferred` | Participações/Encontros | DEFERRED |
| `NO_AVC` | evidência histórica | `deferred` | Participações/Encontros | DEFERRED |
| `NO_ACAMPAMENTO` | evidência histórica | `deferred` | Participações/Encontros | DEFERRED |
| `NO_MONTE` | semântica não comprovada | metadata | a definir | UNKNOWN |
| `IN_COR_GRUPO` | cor/grupo histórico | `deferred` | participação/grupo futuro | DEFERRED |
| `IN_JOVEM` | flag legado | significado/vocabulário pendente | a definir | UNKNOWN |
| `IN_VIOLEIRO` | indicação musical | booleano estrito S/N | `Alpinista.eh_violeiro` | TRANSFORM |
| `IN_ATUANTE` | situação de atuação | mapping ainda vazio | estado futuro | DEFERRED |
| `CD_EMAIL` | e-mail | trim, lowercase, validação | `Alpinista.email`/contato | TRANSFORM |
| `situacao` | status textual legado | mapping ainda vazio | estado futuro | DEFERRED |
| `situacao_obs` | observação da situação | preservada | estado futuro | DEFERRED |
| `FICHA_ESPPA` | indicador/código legado | metadata | a definir | UNKNOWN |
| `CD_GRUPO` | referência de grupo | legacy ID/texto preservado | crosswalk de Grupo | DEFERRED |
| `NR_GRUPO_FASE` | fase do grupo | preservar | Grupo futuro | DEFERRED |
| `NO_GRUPO` | grupo textual | preservar, sem criar relação | Grupo futuro | DEFERRED |
| `NO_GRUPO_AVC` | grupo AVC textual | preservar separadamente | Grupo AVC futuro | DEFERRED |
| `revisado` | flag de revisão | sem regra comprovada | processo de migração | UNKNOWN |
| `IN_AMIGO` | indicador financeiro/social | preservar | financeiro futuro | DEFERRED |
| `NR_CPF` | CPF | vazio = ausência; 11 dígitos validados | `Alpinista.cpf` | TRANSFORM |
| `AMIGO_CATEGORIA` | classificação financeira | preservar como sensível | financeiro futuro | DEFERRED |
| `AMIGO_CODIGO` | código financeiro | preservar como sensível | financeiro futuro | DEFERRED |
| `AMIGO_BANCO` | banco | preservar como sensível | financeiro futuro | DEFERRED |
| `AMIGO_TIPO_CONTRIBUICAO` | tipo de contribuição | preservar como sensível | financeiro futuro | DEFERRED |
| `AMIGO_AGENCIA` | agência | preservar como sensível | financeiro futuro | DEFERRED |
| `AMIGO_CONTA` | conta | preservar como sensível | financeiro futuro | DEFERRED |
| `IN_FREQUENTE` | flag de frequência | semântica/vocabulário pendente | Frequência futura | UNKNOWN |
| `URL_FOTO` | referência de foto | URL/path seguro, sem download | migração de mídia futura | TRANSFORM |
| `IN_INDICADO` | flag de indicação | vocabulário pendente | a definir | UNKNOWN |
| `TX_INDICADO` | detalhe da indicação | metadata | a definir | UNKNOWN |
| `OBS_FICHAS` | observação privada | `private_notes`, acesso restrito | campo/domínio futuro | DEFERRED |
| `IN_MARCADO` | flag legado | significado pendente | a definir | UNKNOWN |

## `coordenacao`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_COORDENACAO` | ID legado | legacy_id | crosswalk futuro | TRANSFORM |
| `CD_ALPINISTA` | pessoa referenciada | resolver via crosswalk | Alpinista/coordenação | DEFERRED |
| `TX_FUNCAO` | função textual | mapping/profiling | papel/função futura | DEFERRED |
| `TX_COORDENACAO` | coordenação textual | vocabulário pendente | domínio futuro | UNKNOWN |
| `NR_ORDEM` | ordem | decimal preservado | domínio futuro | DEFERRED |

## `ele_recebe_inscricao`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `id_ele_inscricao` | ID da inscrição | legacy_id | inscrições futuras | DEFERRED |
| `ele_nome_alpinista` | nome informado | texto; não casar automaticamente | inscrição/pessoa | DEFERRED |
| `ele_email` | e-mail informado | normalização futura | inscrição | TRANSFORM |
| `ele_telefone` | telefone informado | normalização futura | inscrição | TRANSFORM |
| `ele_celular` | celular informado | normalização/conflito | inscrição | TRANSFORM |
| `ele_modulos` | módulos textuais | vocabulário pendente | inscrição | UNKNOWN |
| `ele_perguntas` | respostas/perguntas | dado pessoal raw | inscrição | DEFERRED |
| `ele_validacao` | estado de validação | vocabulário pendente | inscrição | UNKNOWN |
| `ele_data_inscricao` | data/hora | datetime validado futuramente | inscrição | TRANSFORM |

## `encontro`

| Campo | Significado conhecido | Destino/transformação | Destino Django futuro | Estado |
|---|---|---|---|---|
| `CD_ENCONTRO` | ID legado | legacy_id | crosswalk para `Encontro.id` | TRANSFORM |
| `DT_ENCONTRO` | data de referência | data ISO validada | `Encontro.data_referencia` | TRANSFORM |
| `NO_ENCONTRO` | nome | texto normalizado | `Encontro.encontro` | TRANSFORM |
| `IN_TIPO_ENCONTRO` | tipo codificado | mapping vazio | `Encontro.tipo` | DEFERRED |
| `DS_ENCONTRO` | descrição | texto canônico | campo futuro | DIRECT |
| `DS_MENSAGEM` | mensagem | texto canônico | campo futuro | DIRECT |
| `DT_ENCONTRO_COMPLETA` | datas em texto | preservar sem interpretar | `Encontro.data_exato` possível | DEFERRED |
| `URL_ENCONTRO` | referência de mídia | URL/path, sem download | galeria/storage futuro | TRANSFORM |

Status de encontro histórico não é inferido.

## `encontros_alpinista`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_REGISTRO` | pessoa legada | crosswalk de Alpinista | `ParticipacaoEncontro.alpinista` | DEFERRED |
| `NO_ALPINISTA` | campo textual/código inconsistente | metadata, não usado para match | a definir após profiling | UNKNOWN |
| `CD_ENCONTRO` | encontro legado | crosswalk de Encontro | `ParticipacaoEncontro.encontro` | DEFERRED |

A tabela produz apenas participação candidata como encontrista.

## `encontro_equipe`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_EQUIPE` | ID da linha | source_id | crosswalk opcional | TRANSFORM |
| `CD_ENCONTRO` | encontro legado | inteiro + crosswalk | Participação | DEFERRED |
| `CD_REGISTRO` | pessoa legada | inteiro + crosswalk | Participação | DEFERRED |
| `NR_ORDEM` | ordem histórica | decimal preservado | metadata/ordem futura | DEFERRED |
| `NM_FUNCAO` | função textual | mapping vazio obrigatório | `FuncaoEncontro` | DEFERRED |

## `evento`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_EVENTO` | ID legado | legacy_id | crosswalk para Evento | TRANSFORM |
| `DT_EVENTO` | data | data ISO validada | `Evento.data_evento` | TRANSFORM |
| `NO_EVENTO` | nome | texto normalizado | `Evento.nome` | TRANSFORM |
| `IN_TIPO_EVENTO` | tipo codificado | preservar para profiling | tipo futuro | DEFERRED |
| `NO_TIPO_EVENTO` | nome do tipo | preservar para profiling | tipo futuro | DEFERRED |
| `DS_EVENTO` | descrição | texto canônico | campo futuro | DIRECT |
| `OBS_EVENTO` | observação | texto canônico | campo futuro | DEFERRED |
| `URL_EVENTO` | referência de mídia | URL/path, sem download | storage futuro | TRANSFORM |

## `evento_equipe`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_EVENTO_EQUIPE` | ID da linha | source_id | crosswalk opcional | TRANSFORM |
| `CD_EVENTO` | evento legado | inteiro + crosswalk | equipe de Evento futura | DEFERRED |
| `CD_REGISTRO` | pessoa legada | inteiro + crosswalk | equipe de Evento futura | DEFERRED |
| `NR_ORDEM` | ordem | decimal preservado | metadata futura | DEFERRED |
| `NM_FUNCAO` | função textual | mapping vazio | função futura de Evento | DEFERRED |

Não é convertido automaticamente em `ParticipacaoEvento`.

## `financeiro`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `NATUREZA` | natureza do lançamento | vocabulário pendente | financeiro futuro | UNKNOWN |
| `CD_FINANCEIRO` | ID | legacy_id | crosswalk futuro | TRANSFORM |
| `CD_CONTRIBUICAO` | código de contribuição | preservar | financeiro futuro | DEFERRED |
| `CD_ENCONTRO` | encontro referenciado | crosswalk | financeiro futuro | DEFERRED |
| `CD_ALPINISTA` | pessoa referenciada | crosswalk | financeiro futuro | DEFERRED |
| `VALOR` | valor em texto | parser monetário + profiling | `Decimal` futuro | TRANSFORM |
| `FORMA` | forma/modalidade | vocabulário pendente | financeiro futuro | UNKNOWN |
| `DATA` | data do lançamento | data validada | financeiro futuro | TRANSFORM |
| `LOG_DATA` | data/hora de auditoria | datetime validado | auditoria futura | TRANSFORM |
| `LOG_USUARIO` | usuário textual | preservar sem match automático | auditoria futura | DEFERRED |
| `NOTA` | nota | dado financeiro sensível | financeiro futuro | DEFERRED |
| `NO_RESPONSAVEL` | responsável textual | dado pessoal; match futuro | financeiro futuro | DEFERRED |
| `NO_PRESTADOR` | prestador textual | dado pessoal; match futuro | financeiro futuro | DEFERRED |
| `NO_DESCRICAO` | descrição | dado financeiro sensível | financeiro futuro | DEFERRED |

## `frequencia`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_FREQUENCIA` | ID | legacy_id | frequência futura | TRANSFORM |
| `CD_GRUPO` | grupo legado | crosswalk | frequência futura | DEFERRED |
| `CD_ALPINISTA` | pessoa legada | crosswalk | frequência futura | DEFERRED |
| `CD_PADRINHO` | padrinho textual/código | semântica e tipo inconsistentes | a definir | UNKNOWN |
| `MES_REFERENCIA` | mês/data de referência | data validada + regra futura | frequência futura | DEFERRED |
| `DT_ALTERACAO` | alteração | datetime validado | auditoria futura | TRANSFORM |

## `grupos`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_GRUPO` | ID legado | legacy_id | crosswalk de Grupo | TRANSFORM |
| `DT_CRIACAO` | criação | data validada | Grupo futuro | TRANSFORM |
| `NO_GRUPO` | nome | texto normalizado | Grupo futuro | TRANSFORM |
| `TX_GRUPO` | descrição | texto canônico | Grupo futuro | DIRECT |
| `TX_DATA` | data/periodicidade textual | preservar sem interpretar | Grupo futuro | DEFERRED |
| `TX_ENDERECO` | endereço | texto canônico | Grupo futuro | TRANSFORM |
| `IN_BAIRRO` | bairro | texto canônico | Grupo futuro | TRANSFORM |
| `NO_PADRINHO` | padrinho, tipo legado inconsistente | preservar sem resolver | relação futura | DEFERRED |
| `NO_MADRINHA` | madrinha por nome | preservar sem resolver | relação futura | DEFERRED |
| `NO_COORDENADOR1` | coordenador por nome | preservar sem resolver | relação futura | DEFERRED |
| `NO_COORDENADOR2` | coordenador por nome | preservar sem resolver | relação futura | DEFERRED |
| `NO_COORDENADOR3` | coordenador por nome | preservar sem resolver | relação futura | DEFERRED |
| `IN_ATIVO` | flag de atividade | booleano S/N estrito por enquanto | Grupo futuro | TRANSFORM |
| `URL_LOGO` | referência de logo | URL/path, sem download | storage futuro | TRANSFORM |

## `grupo_avc`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `CD_GRUPO_AVC` | ID legado | legacy_id | crosswalk separado | TRANSFORM |
| `NO_GRUPO_AVC` | nome | texto canônico | Grupo AVC futuro | TRANSFORM |
| `DS_GRUPO_AVC` | descrição | texto canônico | Grupo AVC futuro | DIRECT |

## `justificativas`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `ID` | ID legado | legacy_id | justificativa futura | TRANSFORM |
| `CD_ALPINISTA` | pessoa | crosswalk | justificativa/frequência | DEFERRED |
| `CD_ENCONTRO` | encontro | crosswalk | justificativa/frequência | DEFERRED |
| `DATA` | data/hora | datetime validado | justificativa futura | TRANSFORM |
| `MOTIVO` | motivo | dado pessoal potencialmente sensível | justificativa futura | DEFERRED |

## `logs`

| Campo | Significado conhecido | Destino/transformação | Destino futuro | Estado |
|---|---|---|---|---|
| `id` | ID | legacy_id | arquivo de auditoria, se aprovado | DEFERRED |
| `hora` | data/hora | datetime validado | arquivo de auditoria | TRANSFORM |
| `ip` | IP legado | dado pessoal técnico | arquivo restrito | DEFERRED |
| `mensagem` | mensagem livre | pode conter dados/secrets | arquivo restrito | RAW_ONLY |
| `usuario` | usuário textual | não casar automaticamente | arquivo restrito | DEFERRED |

Logs antigos não serão inseridos automaticamente em `LogSistema`.

## Views MySQL derivadas

| View/campo observado | Tratamento | Estado |
|---|---|---|
| `alpinistasausentes.CD_EMAIL` | recalcular ausências no novo domínio | DERIVED |
| `estatisticafrequencia.1fase` | recalcular estatística | DERIVED |
| `ultimafrequencia.CD_ALPINISTA` | recalcular última frequência | DERIVED |
| `ultimostrabalhos.CD_REGISTRO` | recalcular trabalhos recentes | DERIVED |

Views não geram DTOs de entidades nem linhas a importar.
