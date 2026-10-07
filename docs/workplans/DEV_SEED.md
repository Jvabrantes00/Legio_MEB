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
protegidas fazem a transação falhar em vez de ampliar a exclusão.

## Contas

São criadas as contas `demo.suporte`, `demo.diretoria`, `demo.fichas`,
`demo.mme`, `demo.formacao`, `demo.secretaria`, `demo.acao_social`,
`demo.liturgia`, `demo.eventos`, `demo.comunicacao`, `demo.sem_papel` e
`demo.superuser`. As dez primeiras recebem exatamente seu grupo de negócio;
`demo.sem_papel` não recebe papel e `demo.superuser` representa apenas o bypass
técnico. As contas não técnicas têm `VinculoUsuarioPessoa`. A Pessoa ligada a
`demo.sem_papel` não recebe trabalho ou função contextual privilegiada, para
preservar esse usuário como cenário de default deny.

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

Executar novamente substitui apenas o dataset reconhecido e o recria, evitando
duplicatas e mantendo o resultado determinístico.

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
