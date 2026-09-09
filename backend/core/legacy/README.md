# Compatibilidade com o SIA legado

Esta pasta é uma **anti-corruption layer**: ela impede que nomes, valores e
decisões do MySQL antigo contaminem diretamente o domínio Django atual. Nada
aqui conecta ao MySQL, usa ORM, grava registros ou escolhe PKs novas.

## Fluxo futuro de ETL

```text
extração MySQL -> staging/raw -> normalização -> validação
    -> DTO canônico ou quarentena -> loader Django -> crosswalk
```

- **Extract**: copiar as linhas do banco legado sem modificá-las para uma
  área raw controlada.
- **Transform**: normalizar formatos e construir os DTOs desta pasta.
- **Load**: no futuro, um componente separado usará apenas DTOs válidos para
  criar objetos Django.
- **Staging/raw**: cópia fiel e temporária da fonte. Ela permite reprocessar e
  comprovar o que veio do legado sem colocar dados brutos no domínio novo.
- **Quarentena**: linhas com issues `ERROR` ou `FATAL`. Elas não devem chegar
  ao loader até uma decisão humana ou um mapping versionado resolver o caso.

## Módulos

- `contracts.py`: DTOs canônicos e `TransformationResult`.
- `normalizers.py`: funções puras para formatos legados.
- `mappings.py`: mapas explícitos; permanecem vazios até o profiling real.
- `issues.py`: códigos, severidades e descrições seguras.
- `transformers/`: transforma uma linha raw por domínio.
- `FIELD_MAPPING.md`: inventário campo a campo.

Os DTOs são o **modelo canônico intermediário**. Eles descrevem o significado
que conseguimos provar, sem fingir que todos os campos já existem no Django.
Cada resultado separa:

- atributos canônicos: significado comprovado;
- `deferred`: significado conhecido, mas domínio/destino ainda pendente;
- `legacy_metadata`: campo preservado sem semântica canônica suficiente;
- `issues`: problemas que impedem ou alertam sobre a migração.

## Falha explícita e mappings

Os mapas de `usu_tipo`, tipo de encontro, função e status estão
intencionalmente vazios. Um valor não mapeado produz `UNKNOWN_*`; ele jamais
vira um default. Um fallback silencioso perderia a diferença entre, por
exemplo, "N", vazio, erro de digitação e um terceiro estado real.

As flags aceitam somente `S`, `N` ou ausência. Novas grafias só devem ser
incluídas depois de contadas e documentadas no profiling.

## Crosswalk de IDs

`CrosswalkEntry` representa:

```text
source_table | source_id | target_model | target_id
```

Exemplos futuros:

- `alpinista / CD_REGISTRO 42 -> core.Alpinista / 918`;
- `encontro / CD_ENCONTRO 7 -> core.Encontro / 35`;
- `grupos / CD_GRUPO 3 -> futuro GrupoPosEncontro / 12`.

O ID antigo identifica a origem, mas nunca é reutilizado automaticamente como
PK nova. Participações serão resolvidas consultando o crosswalk. Isso permite
repetir a migração de maneira **idempotente**: a mesma origem produz a mesma
associação e não cria duplicatas em uma segunda execução.

O armazenamento persistente do crosswalk pertence ao loader futuro; não foi
criado model nesta fase.

## Participações

- `encontros_alpinista` produz candidato do tipo `ENCONTRISTA`.
- `encontro_equipe` produz candidato do tipo `EQUIPE`.
- `NM_FUNCAO` exige mapping explícito; nunca se usa `get_or_create` com texto
  legado.
- a validação em memória detecta Alpinista/Encontro órfão, duplicidade e
  classificações incompatíveis.
- `NR_ORDEM` é preservado, não aplicado ao model atual.

`evento_equipe` gera um DTO de equipe de evento, não uma
`ParticipacaoEvento`. Presença e trabalho em equipe continuam conceitos
distintos.

## Pessoas e grupos

O Grupo Pós-Encontro tem contrato independente do campo textual `grupo` do
Alpinista atual. Nomes de padrinhos, madrinhas e coordenadores são preservados
em `unresolved_people`; não há resolução automática por nome. Quando houver
dados reais, zero, um ou vários candidatos poderão gerar respectivamente
orphan, match ou `AMBIGUOUS_PERSON_MATCH`.

`grupo_avc` permanece um conceito separado.

## Segurança

- `adm_usu.usu_senha` nunca entra em DTO, metadata, teste ou documentação.
- a issue correspondente apenas informa que a credencial foi ignorada e deve
  ser rotacionada.
- descrições de issues não incluem CPF, telefone, e-mail, valores financeiros
  nem o valor bruto que falhou.
- dados raw e relatórios completos deverão usar acesso restrito, retenção
  definida e criptografia apropriada.
- referências de mídia são strings; nenhum arquivo ou URL é aberto nesta fase.

## Tabelas sem domínio atual

`ajuda`, `coordenacao`, `ele_recebe_inscricao`, `financeiro`, `frequencia`,
`justificativas` e `logs` permanecem `DEFERRED` ou `RAW_ONLY`. Elas não devem
ser forçadas em models existentes. Dados financeiros e pessoais são
sensíveis.

As views `alpinistasausentes`, `estatisticafrequencia`, `ultimafrequencia` e
`ultimostrabalhos` são consultas derivadas. Elas serão recalculadas no domínio
novo, nunca importadas como entidades.

## Dependências do profiling real

Antes do loader, ainda será necessário:

1. contar valores distintos, nulos, encoding e tamanhos por coluna;
2. preencher mappings de papéis, status, tipos de encontro e funções;
3. decidir conflitos de telefone, CPF e e-mail duplicados;
4. definir equivalências de pessoas referenciadas por nome;
5. verificar se IDs decimais são de fato inteiros sem perda;
6. perfilar formatos monetários, datas, flags e URLs;
7. definir regras de deduplicação e precedência;
8. verificar existência e integridade dos arquivos de mídia;
9. modelar Grupo Pós-Encontro, frequência, financeiro e inscrições;
10. rotacionar todas as credenciais históricas antes de qualquer acesso.

Os testes usam somente linhas sintéticas e não afirmam representar a
distribuição ou o vocabulário dos dados reais.
