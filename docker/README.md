# SIA em Docker Compose para desenvolvimento

Execute os comandos a partir da raiz do projeto. Este ambiente é independente
do modo tradicional descrito no [README principal](../README.md); não se destina
à produção nem usa o banco tradicional ou legado. O PostgreSQL fica acessível
somente na rede Compose, sem porta publicada. Não há worker, agendador ou envio
externo de e-mail nesta configuração.

## Primeira execução

1. Copie o modelo e preencha `docker/.env` localmente, sem versioná-lo:

   ```bash
   cp docker/.env.example docker/.env
   ```

2. Gere duas chaves diferentes usando somente Docker e coloque cada resultado
   no campo correspondente (`SIA_COMPOSE_DJANGO_SECRET_KEY` e
   `SIA_COMPOSE_JWT_SIGNING_KEY`). Defina também uma senha local forte para
   `SIA_COMPOSE_POSTGRES_PASSWORD` e, se desejar o seed, outra para
   `SIA_COMPOSE_DEMO_PASSWORD`. Não compartilhe essas saídas ou o arquivo.

   ```bash
   docker run --rm python:3.12-slim-trixie python -c 'import secrets; print(secrets.token_urlsafe(48))'
   ```

   Execute a geração duas vezes. A imagem pode precisar ser obtida pelo Docker.
   As variáveis do shell têm precedência sobre `--env-file`; este arquivo
   explícito substitui o `.env` padrão do Compose, seguido pelos padrões do
   próprio Compose. Verifique variáveis `SIA_COMPOSE_*` e
   `COMPOSE_PROJECT_NAME` presentes no shell antes de iniciar. Variáveis
   tradicionais `POSTGRES_*` do host não redirecionam o banco.

3. Valide sem revelar segredos e construa as imagens:

   ```bash
   docker compose --env-file docker/.env -f docker/compose.yaml config --quiet
   docker compose --env-file docker/.env -f docker/compose.yaml config --services
   docker compose --env-file docker/.env -f docker/compose.yaml build backend frontend
   docker compose --env-file docker/.env -f docker/compose.yaml up -d
   ```

   Não cole a saída completa de `config`: ela contém segredos. O `up` inicia o
   banco, executa migrations e só então inicia os serviços da aplicação. Acesse
   `http://localhost:3100`; o backend fica em `127.0.0.1:8100`. Os valores e
   portas podem ser configurados no arquivo local. Use no browser exatamente o
   host configurado em `SIA_COMPOSE_APP_HOST`: a comparação de Origin é exata.

O ambiente tradicional pode continuar nas portas 8000 e 3000. Cookies não são
isolados por porta: use hosts distintos, por exemplo `localhost` para Compose e
`127.0.0.1` para o ambiente tradicional, configurando a Origin correspondente em
cada ambiente. As portas publicadas pelo Compose ficam restritas a loopback.

## Desenvolvimento

O código montado permite acompanhar alterações. Arquivos montados individualmente
podem exigir recriação do serviço quando o editor salva por renomeação. Mudanças
em `frontend/tsconfig.json` exigem reiniciar o frontend, pois ele copia o arquivo
na inicialização:

```bash
docker compose --env-file docker/.env -f docker/compose.yaml restart frontend
```

Para criar uma migration sem Python no host, mantenha o banco Compose ativo e
construa a imagem backend. A checagem do histórico de migrations consulta o
banco. Primeiro confira o que seria criado, sem escrever arquivos:

```bash
docker compose --env-file docker/.env -f docker/compose.yaml build backend
docker compose --env-file docker/.env -f docker/compose.yaml up -d --wait db
docker compose --env-file docker/.env -f docker/compose.yaml run --rm --no-deps backend python manage.py makemigrations core --dry-run --verbosity 2
```

Revise a proposta e escolha um nome descritivo para a migration. O comando
abaixo adiciona somente a pasta de migrations como montagem gravável aninhada;
o restante do código permanece somente leitura. Execute como usuário não-root
no host e substitua `nome_descritivo`:

```bash
docker compose --env-file docker/.env -f docker/compose.yaml run --rm --no-deps --user "$(id -u):$(id -g)" -e XDG_CACHE_HOME=/tmp -v "$PWD/backend/core/migrations:/app/core/migrations:rw" backend python manage.py makemigrations core --name nome_descritivo
git status --short backend/core/migrations
git diff -- backend/core/migrations
```

Confira também o conteúdo de cada arquivo novo não rastreado, pois `git diff`
não o exibe. A execução usa o UID/GID do usuário do host; no macOS, o Docker
Desktop intermedeia as permissões e a propriedade observada pode diferir.
O cache aponta para `/tmp`, gravável pelo usuário arbitrário. Na homologação R1,
foi comprovada a criação de uma migration vazia por este procedimento; consulte
[Homologação e limites](#homologação-e-limites) para o que não tem confirmação
específica.

Após criar ou receber migrations, revise os arquivos e aplique-as explicitamente. Construa primeiro a
imagem backend: `migrate` usa essa imagem e não possui `build` próprio. O `up`
também executa o serviço de migration; use o comando explícito abaixo para
garantir sua execução após mudanças:

```bash
docker compose --env-file docker/.env -f docker/compose.yaml build backend
docker compose --env-file docker/.env -f docker/compose.yaml run --rm migrate
```

Migrations montadas de `backend/core` não exigem rebuild por si só; mudanças em
dependências ou no Dockerfile exigem reconstrução. Confirme a necessidade de
rebuild conforme os arquivos alterados. Para atualizar dependências Python, edite
`backend/requirements.txt` no host e reconstrua:

```bash
docker compose --env-file docker/.env -f docker/compose.yaml build backend
docker compose --env-file docker/.env -f docker/compose.yaml up -d backend
```

Para alterar dependências Node, prepare cópias em um diretório temporário
privado fora do repositório. O diretório inteiro é montado para permitir que o
npm substitua arquivos por renomeação. O procedimento usa o UID/GID do host, um
HOME gravável e desativa telemetria e scripts de instalação. Ele atualiza as
cópias de `package.json` e `package-lock.json`, conforme a operação, sem criar
`node_modules` no host; os passos seguintes levam as alterações aceitas para
`frontend/`. A cobertura da homologação está em
[Homologação e limites](#homologação-e-limites). Não monte `frontend/` nem
arquivos `.env`:

```bash
SIA_NODE_PREP=$(mktemp -d "$HOME/sia-node-prep.XXXXXX")
cp frontend/package.json frontend/package-lock.json "$SIA_NODE_PREP/"
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/work -e NEXT_TELEMETRY_DISABLED=1 -v "$SIA_NODE_PREP:/work" -w /work node:24-trixie-slim npm install --package-lock-only --ignore-scripts
diff -u frontend/package.json "$SIA_NODE_PREP/package.json"
diff -u frontend/package-lock.json "$SIA_NODE_PREP/package-lock.json"
```

Para adicionar um pacote, substitua `npm install` no comando acima por
`npm install pacote@versao`; para atualizar, use `npm install pacote@versao`
com a versão desejada; para remover, use `npm uninstall pacote`. Preserve
`--package-lock-only --ignore-scripts` em cada caso e acrescente `--save-dev`
quando apropriado. Execute a operação desejada antes dos comandos `diff`.
Uma saída de `diff` com código 1 indica diferenças para revisão. Examine ambas
as cópias e aceite apenas as alterações pretendidas. Guarde os originais no
diretório temporário antes de copiar o conteúdo sobre os arquivos existentes;
então reconstrua e recrie o frontend:

```bash
mkdir "$SIA_NODE_PREP/originais"
cp frontend/package.json frontend/package-lock.json "$SIA_NODE_PREP/originais/"
cat "$SIA_NODE_PREP/package.json" > frontend/package.json
cat "$SIA_NODE_PREP/package-lock.json" > frontend/package-lock.json
docker compose --env-file docker/.env -f docker/compose.yaml build frontend
docker compose --env-file docker/.env -f docker/compose.yaml up -d --force-recreate frontend
```

Para desfazer após copiar, restaure o conteúdo dos originais e reconstrua e
recrie o frontend novamente. `git checkout` também descartaria alterações
locais não commitadas nesses arquivos:

```bash
cat "$SIA_NODE_PREP/originais/package.json" > frontend/package.json
cat "$SIA_NODE_PREP/originais/package-lock.json" > frontend/package-lock.json
docker compose --env-file docker/.env -f docker/compose.yaml build frontend
docker compose --env-file docker/.env -f docker/compose.yaml up -d --force-recreate frontend
```

Somente depois de validar o resultado, limpe o diretório criado nesta sessão:

```bash
rm -r -- "$SIA_NODE_PREP"
```

Dependências Node ficam na imagem; este procedimento não remove `pgdata`.

## Dados de demonstração

O seed é opcional e nunca automático. Configure `SIA_COMPOSE_DEMO_PASSWORD` no
arquivo local. Construa antes a imagem backend, pois o seed, como `migrate`, não
tem `build`; a dependência exige migration concluída:

```bash
docker compose --env-file docker/.env -f docker/compose.yaml build backend
docker compose --env-file docker/.env -f docker/compose.yaml --profile seed run --rm seed
```

O seed exige `SIA_COMPOSE_DEMO_PASSWORD`. Com dataset ausente, cria o dataset e as contas; com
dataset completo, não altera nada; recusa estado parcial ou divergente. Em
PostgreSQL, `--reset` é sempre recusado; não o use neste ambiente.

## Persistência e cópias locais

Os volumes `pgdata`, `media` e `frontend_next` são separados. O primeiro guarda o
banco, o segundo os arquivos de mídia e o terceiro o cache do Next; dependências
ficam nas imagens. Parar e remover containers preserva os volumes:

```bash
docker compose --env-file docker/.env -f docker/compose.yaml down
```

Para cópias locais, escolha um diretório fora do repositório, restrito ao seu
usuário. Os comandos abaixo usam `"$HOME/sia-backups"`; crie-o previamente e
nunca versione seus arquivos. Com os serviços disponíveis, copie banco e mídia:

```bash
mkdir -p "$HOME/sia-backups"
chmod 700 "$HOME/sia-backups"
docker compose --env-file docker/.env -f docker/compose.yaml exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$HOME/sia-backups/sia.dump"
docker compose --env-file docker/.env -f docker/compose.yaml run -T --rm --no-deps --entrypoint tar backend -C /app/media -cf - . > "$HOME/sia-backups/media.tar"
```

A cópia e a restauração de banco e mídia foram exercitadas na homologação R1, em
ambiente descartável separado. Planeje uma janela sem escrita para obter versões
coerentes entre banco e mídia. Proteja os arquivos, que podem conter dados
pessoais. A restauração está descrita abaixo como destrutiva.

## Operações destrutivas

Restauração sobrescreve o estado atual: pare os serviços que escrevem e confirme
o destino e as cópias antes de prosseguir. O exemplo substitui objetos do banco
presentes no dump e remove todos os arquivos existentes no volume de mídia.

Antes de executar os comandos destrutivos, confira no host que as duas cópias
existem e não estão vazias e que o arquivo de mídia é legível. Se qualquer
verificação falhar, não prossiga:

```bash
test -s "$HOME/sia-backups/sia.dump" && test -s "$HOME/sia-backups/media.tar" && tar -tf "$HOME/sia-backups/media.tar" || { printf '%s\n' 'Verificação falhou; não prossiga.' >&2; false; }
```

```bash
docker compose --env-file docker/.env -f docker/compose.yaml stop backend frontend
docker compose --env-file docker/.env -f docker/compose.yaml exec -T db sh -c 'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --exit-on-error' < "$HOME/sia-backups/sia.dump"
docker compose --env-file docker/.env -f docker/compose.yaml run -T --rm --no-deps --entrypoint sh backend -c 'find /app/media -mindepth 1 -delete && tar -C /app/media -xf -' < "$HOME/sia-backups/media.tar"
docker compose --env-file docker/.env -f docker/compose.yaml up -d
```

`down -v` remove os volumes declarados, incluindo banco e mídia, e seus dados:

```bash
docker compose --env-file docker/.env -f docker/compose.yaml down -v
```

Remover volumes individualmente também apaga seus dados; identifique o projeto e
o volume antes de qualquer remoção. Não use essas operações para atualizar
dependências ou reiniciar serviços.

## Homologação e limites

Todos os resultados abaixo são de homologação humana em Mac ARM64 (aarch64),
sobre o baseline `4ab3ed9`. Os logs originais não estão arquivados no
repositório. Eles valem para o ambiente e os dados testados.

### Homologação inicial, anterior à R1

Realizada com Docker Engine 29.9.3 e Compose v5.7.0, sobre o candidato anterior
às correções da R1 (cache do Fontconfig, telemetria do Next.js e procedimentos
deste guia).

Foram confirmados: configuração do Compose, builds, inicialização e saúde dos
serviços, migrations, isolamento da porta PostgreSQL, seed e sua idempotência,
login e uso, persistência após down/up, hot reload, arquitetura e versões dos
runtimes, geração de PDF, isolamento básico, execução sem root, permissões e
rejeição de login por origem divergente. O seed criou 40 pessoas, 32 alpinistas,
4 encontros e 12 contas; a primeira tentativa falhou sem a senha demonstrativa e
a seguinte funcionou com a senha configurada. Somente build, migrations e seed
tiveram saídas de terminal apresentadas; os demais resultados foram confirmados
sem transcrição integral.

### Candidato corrigido R1

**Saídas de terminal recebidas e revisadas na conversa de homologação:**

- build, inicialização e saúde dos serviços;
- System Check sem problemas;
- banco e mídia: backup, restauração em ambiente descartável, correspondência do
  banco restaurado, banco original íntegro e ida e volta de mídia;
- PDF gerado diretamente no backend, cache do Fontconfig `sia:sia` com modo 700 e
  nenhum erro do Fontconfig nos logs do backend e do seed, nas conferências
  realizadas;
- telemetria do Next.js: variável `1` e status `Disabled`;
- processos de workers pesquisados ausentes, configurações de envio externo e
  amostragem das conexões HTTPS externas;
- dependências Node: diff de `package.json` e `package-lock.json` e ausência de
  `node_modules` no diretório temporário;
- migration vazia `0054`: criação, conteúdo, arquivo com o UID do usuário do host
  e escrita bloqueada no container normal (filesystem somente leitura);
- regressão do backend: 1116 testes, 75 ignorados e nenhuma falha;
- ESLint: nenhum erro e 2 avisos;
- falha controlada de migration (`division by zero`, saída 1, somente o banco em
  execução) e recuperação após remover a migration defeituosa;
- seed completo e segunda execução idempotente;
- integridade dos 18 hashes dos dois ambientes de teste e `git status` final de
  ambos contendo somente os nove arquivos esperados do candidato.

**Confirmações verbais, sem saída registrada:** instalação de `ms@2.1.3`; volume
do PostgreSQL inalterado, container do banco não recriado e dados iguais após a
atualização; reversão das dependências e frontend saudável em seguida; testes
automatizados do frontend (quantidade não registrada) e TypeScript concluídos com
sucesso.

**Verificações manuais aprovadas:** acesso pelo endereço correto, login com
`demo.suporte`, geração de PDF real pela interface, abertura do PDF, logout e
rejeição de login pela origem incorreta.

### Resultados não repetidos na R1

Não há registro de repetição, no candidato R1, de hot reload, persistência após
down/up, conferência de arquitetura e versões dos runtimes, execução sem root e
isolamento da porta PostgreSQL. Esses resultados pertencem à homologação inicial.

### Conexões externas do frontend

Foram observadas conexões HTTPS externas no frontend. As origens prováveis são o
Google Fonts e consultas de versão do Next.js/npm, segundo análise do código, sem
comprovação individual por captura de tráfego. Na amostragem, não se observou
conexão externa do backend ou do PostgreSQL, o que não prova sua ausência. Este
ambiente não é offline: o objetivo é não enviar mensagens, convites ou e-mails nem
executar tarefas externas.

### Limitações e itens não comprovados

- Sem confirmação específica: aplicação e reversão da migration vazia `0054`.
- Sem registro de resultado: `makemigrations --check`, tentativa de sobrescrever a
  variável de telemetria e contagem de erros do Fontconfig após o PDF gerado pela
  interface.
- Não comprovados: detecção de mudanças de modelo ao criar migrations, remoção de
  dependências Node, Windows, AMD64, build de produção e regressão completa sobre
  PostgreSQL.
- A migration artificial comprova o bloqueio da inicialização, não a recuperação
  de uma migration real parcialmente aplicada.
- Esta configuração não substitui auditoria de segurança nem validação para
  operação em produção.
