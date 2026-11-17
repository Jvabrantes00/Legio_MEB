# DEV-SEED — Dataset controlado de demonstração

## Objetivo

O management command `seed_demo` cria dados determinísticos para avaliação
manual do produto em desenvolvimento. Ele cobre Pessoas, Grupos, Encontros,
participação, equipes, trabalho, Preparatórias, MME, permissões e Calendário sem
adicionar capacidade de produção ou endpoint HTTP.

## Execução

Na pasta `backend/`, com o ambiente Django local carregado:

```bash
SIA_ENVIRONMENT=development \
SIA_DEMO_PASSWORD='<senha-local>' \
./.venv/bin/python manage.py seed_demo
```

A senha também pode ser fornecida por `--password`, mas a variável de ambiente
evita registrá-la no histórico do shell. A senha nunca é impressa pelo comando e
não deve ser versionada.

Para remover o dataset:

```bash
SIA_ENVIRONMENT=development \
./.venv/bin/python manage.py seed_demo --reset
```

## Segurança

O comando falha fechado: exige simultaneamente `settings.DEBUG=True` e
`SIA_ENVIRONMENT=development`. A senha é obrigatória somente para criação. Toda
a operação ocorre em uma transação e usa os services canônicos para transições
de domínio.

O reset usa allowlists exatas de usernames, pares nome/e-mail das Pessoas,
nomes dos Grupos e pares título/tipo dos Encontros. Templates criados pelo seed
só são removidos quando código e nome demo coincidem; um template canônico
preexistente de Violeiros é reutilizado e preservado. Referências externas
protegidas fazem a transação falhar em vez de ampliar a exclusão. A limpeza
inclui o código legado `demo-coordenacao-geral` somente quando o nome também é
`[DEMO] Coordenação Geral`. Na criação, um template `coordenacao-geral` com
nome diferente desse, em qualquer dos dois tipos, causa erro fechado e reverte
toda a transação, preservando o template real e seus papéis.

## Contas

São criadas as contas `demo.suporte`, `demo.diretoria`, `demo.fichas`,
`demo.mme`, `demo.formacao`, `demo.secretaria`, `demo.acao_social`,
`demo.liturgia`, `demo.eventos`, `demo.comunicacao`, `demo.sem_papel` e
`demo.superuser`. As dez primeiras recebem exatamente seu grupo de negócio;
`demo.sem_papel` não recebe papel e `demo.superuser` representa apenas o bypass
técnico. As contas não técnicas têm `VinculoUsuarioPessoa`. A Pessoa ligada a
`demo.sem_papel` não recebe trabalho ou função contextual privilegiada, para
preservar esse usuário como cenário de default deny.

Em Vale Verde, `demo.secretaria` atua como coordenador geral e
`demo.comunicacao` como apoio alocado na equipe de código exato
`coordenacao-geral`. Ambas têm acesso contextual a Equipes nesse Encontro;
`demo.sem_papel` permanece negado. A conta de Comunicação não recebe trabalho
nos outros três Encontros.

## Dataset

- 40 Pessoas fictícias, e-mails em `example.invalid`, telefones não roteáveis e
  CPF nulo; inclui menores com responsável e dois casais;
- 32 `PerfilAlpinista`, quatro Grupos e frequências com recência variada;
- exatamente duas Escaladas e dois ESPPAs demo nos estados
  `EM_AGENDAMENTO`, `EM_PREPARACAO`, `AGENDADO` e `FINALIZADO`;
- dias provisórios/oficiais e sobreposição consultiva entre Serra Azul e
  Horizonte;
- inscrições, convites e resultados de participação separados;
- snapshots de equipe, trabalhos atuais e experiência histórica formada
  exclusivamente por resultados `TRABALHOU`; existe também um `FALTOU` como
  resultado operacional, excluído do histórico pessoal de trabalho;
- três Preparatórias de Vale Verde, incluindo `Missa de Entrega`, com presenças
  variadas e uma Avaliação;
- uma proposta MME aberta em Vale Verde com cinco slots e candidatos cujos
  estados derivados cobrem disponibilidade, aproveitamento, outra equipe,
  indisponibilidade MME e histórico.

A reexecução tenta substituir apenas o dataset reconhecido e recriá-lo; consulte
a limitação conhecida de auditoria abaixo.

### Configuração demonstrativa de inscrições

Os quatro Encontros do dataset recebem uma
`ConfiguracaoEncontristasEncontro`: as Escaladas Serra Azul e Vale Verde e os
ESPPAs Horizonte e Caminho. Os valores definidos pelo seed são:

| Tipo | Capacidade | Idade mínima | Idade máxima |
|---|---:|---:|---:|
| Escalada | 40 | 15 | 18 |
| ESPPA | 50 | 18 | 80 |

A janela usa o primeiro `DiaEncontro` do calendário vigente, ordenado por
ordem e data. A abertura fica 210 dias antes, às 08:00, e o encerramento 14
dias antes, às 23:59, no timezone configurado pelo Django.

A criação usa o service canônico `criar_configuracao_encontristas`; quando a
rotina de configuração recebe um registro já existente, usa
`alterar_configuracao_encontristas`. Assim, validações, autorização, auditoria
e constraints do domínio não são contornadas. O `public_id` é um UUID gerado
automaticamente pelo model e não é definido pelo seed. A reconciliação de uma
configuração existente preserva seu registro e seu `public_id`.

A reexecução do comando completo tem uma semântica mais ampla: primeiro remove
o dataset reconhecido pelas allowlists e depois o recria. Quando a exclusão é permitida, ela recria os valores demonstrativos sem
preservar necessariamente PKs ou `public_id` entre recriações completas.

> **Limite dos valores demo.** Os valores descritos pertencem exclusivamente
> ao dataset de demonstração. Não constituem regras institucionais gerais nem
> valores obrigatórios para Encontros reais ou ambientes de produção.

Essa configuração é apenas suporte parcial ao novo fluxo. A R.3I.26 permanece
planejada e ainda prevê cenários de inscrição, cuidado, campanha, espera,
Pré-Encontro, pagamento, disputa e autorização que este dataset não demonstra
integralmente.

## Limitações

- O dataset tem exatamente quatro Encontros. Como o domínio permite um único
  `TrabalhoEncontro` por Pessoa/Encontro e somente Caminho está finalizado, ele
  demonstra experiência histórica distribuída, mas não múltiplos trabalhos
  concluídos da mesma Pessoa sem fabricar encontros adicionais.
- As datas são fixas para preservar determinismo; com a passagem do tempo, a
  leitura derivada de atividade pela janela de seis meses naturalmente muda.
- Nenhum AVC ou Acampamento é criado nesta versão.
- O dataset é apoio futuro à revisão manual de maturidade; este bloco não
  inicia a R.3.

### Limitação conhecida — auditoria PostgreSQL

No PostgreSQL, eventos de auditoria protegidos pelo trigger imutável da
migration 0052 fazem a recriação e o `--reset` falharem. A idempotência não
está atendida nesse cenário e permanece pendente para o pacote R26-B. O comando
é restrito a desenvolvimento (`DEBUG=True` e `SIA_ENVIRONMENT=development`) e
jamais deve ser usado no `sia_dev`. A adição de papéis `demo-*` a um template
real preexistente de Violeiros permanece como dívida técnica conhecida.
