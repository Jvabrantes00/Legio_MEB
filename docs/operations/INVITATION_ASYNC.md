# Convites assíncronos — operação

## Garantias e fronteiras

- PostgreSQL é a autoridade para campanha, rodada, oportunidade, entrega,
  retry, prazo, outbox e sinal de reposição.
- Redis é somente broker. Tasks carregam apenas IDs técnicos; token,
  ciphertext, link, e-mail, telefone e outros dados pessoais não entram nos
  argumentos Celery.
- O token fica temporariamente cifrado e autenticado na outbox. A chave Fernet
  existe apenas no ambiente e o ciphertext é apagado depois que todos os
  canais terminam.
- A publicação inicial usa `transaction.on_commit`. Falha do broker não
  desfaz o estado válido do banco; o Beat republica trabalho pendente.
- O estado local é idempotente. SMTP, porém, tem semântica at-least-once em
  falhas ambíguas: uma queda depois da aceitação externa e antes da gravação
  local pode provocar mensagem duplicada no retry.
- **Comportamento vigente.** As garantias acima descrevem o código atual, no
  qual a chamada externa ocorre dentro da transação do worker. O tratamento
  planejado de resultado incerto, reconciliação e ativação segura está
  especificado em
  [[../workplans/R3I16_C5_ENTREGA_RECONCILIACAO|R.3I.16-C5]] e **não está
  implementado**. Somente o schema e a integridade do B1 (migrations `0051` e
  `0052`) estão commitados localmente (C1, `1c42f63`), sem ativação e sem
  aplicação em banco persistente; não alteram o worker nem este comportamento.

## Transição planejada da entrega externa (R.3I.16-C5, não implementada)

Resumo operacional. A especificação, os estados e a distinção entre decisão
aprovada e proposta estão no workplan citado e não são repetidos aqui.

- **Ativação controlada, rollback fail-closed.** A entrega nova será ligada por
  feature flag, desligada por padrão. Com a flag desligada nenhuma chamada
  externa ocorre e não há retorno automático ao worker antigo.
- **Sem workers antigos e novos na mesma fila.** Antes de ativar: parar worker
  e Beat, confirmar que nenhum processo antigo consome, implantar, inventariar,
  transitar o legado e só então ligar a flag. Worker antigo ativo bloqueia a
  ativação.
- **Inventário prévio obrigatório (ainda não realizado).** Contagem de
  entregas por status e por número de tentativas, existência de entregas
  `enviando`, outboxes pendentes com segredo e oportunidades expiradas com
  entrega pendente. Exige acesso ao PostgreSQL com aprovação pontual.
- **Legado.** Toda entrega `pendente` sem prova confiável de não envio, com
  qualquer número de tentativas (inclusive zero), é identificada logicamente
  como `LEGADO_SEM_PROVA`, com reenvio automático bloqueado no próprio serviço
  (não apenas na fila ou na task) e liberação somente por evidência segura ou
  reconciliação autorizada por Fichas, que é sempre exigida, mesmo com prova
  conclusiva; prova exige evidência verificável de não início ou confirmação
  inequívoca de não aceitação pelo provedor, e contador zero ou ausência de
  registro não bastam; `entregue` e `falhou` são preservadas. Ausência de
  registro de sucesso não prova que a mensagem não foi enviada.
- **Segredo.** O ciphertext deixará de ser apagado apenas porque os canais
  terminaram: será retido enquanto houver necessidade legítima e oportunidade
  válida.
- **Sem alertas externos.** Pendências e alertas de entrega incerta ou falha
  são internos, na Central de Pendências.

## Variáveis

Configure no arquivo local não versionado do backend:

```dotenv
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
SIA_CELERY_OUTBOX_INTERVAL=300
SIA_CELERY_CAMPAIGN_INTERVAL=300
SIA_INVITATION_OUTBOX_KEY=<chave-fernet-exclusiva-do-ambiente>
SIA_PUBLIC_INVITATION_BASE_URL=http://localhost:3000/convites
```

Gere a chave uma vez por ambiente, armazene-a como segredo operacional e não a
imprima em logs de inicialização:

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Perder ou rotacionar essa chave sem um procedimento explícito torna outboxes
pendentes indecifráveis. Não há fallback para `SECRET_KEY` nem chave efêmera.

## Desenvolvimento local

Inicie Redis e Mailpit conforme os pacotes locais do servidor. Em terminais
separados, depois de carregar o ambiente do backend:

```bash
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/python manage.py runserver
./.venv/bin/celery -A setup worker --loglevel=INFO
./.venv/bin/celery -A setup beat --loglevel=INFO
```

Mailpit atende o adapter SMTP local; WhatsApp continua no mock configurável da
R.3I.14. Não há provider real de WhatsApp nesta etapa.

## Saúde e diagnóstico

```bash
redis-cli ping
cd /home/vinicius/projects/Legio_MEB/backend
./.venv/bin/celery -A setup inspect ping
systemctl status redis-server
systemctl status sia-celery-worker.service
systemctl status sia-celery-beat.service
journalctl -u sia-celery-worker.service -n 100 --no-pager
journalctl -u sia-celery-beat.service -n 100 --no-pager
```

Uma inspeção Celery indisponível não autoriza recriar estado de negócio no
Redis. Restaure broker/worker/Beat; os reconciliadores retomam IDs pendentes a
partir do PostgreSQL.

## Exemplos de systemd

Os trechos abaixo são referência e não instalam nem modificam units do host.
Use o mesmo usuário, `EnvironmentFile` e diretório já adotados pelos serviços
SIA locais.

```ini
# /etc/systemd/system/sia-celery-worker.service
[Unit]
Description=SIA Celery worker
After=network.target postgresql.service redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=vinicius
WorkingDirectory=/home/vinicius/projects/Legio_MEB/backend
EnvironmentFile=/home/vinicius/projects/Legio_MEB/backend/.env
ExecStart=/home/vinicius/projects/Legio_MEB/backend/.venv/bin/celery -A setup worker --loglevel=INFO
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/sia-celery-beat.service
[Unit]
Description=SIA Celery beat
After=network.target postgresql.service redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=vinicius
WorkingDirectory=/home/vinicius/projects/Legio_MEB/backend
EnvironmentFile=/home/vinicius/projects/Legio_MEB/backend/.env
ExecStart=/home/vinicius/projects/Legio_MEB/backend/.venv/bin/celery -A setup beat --loglevel=INFO --schedule=/var/tmp/sia-celerybeat-schedule
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Em produção, use usuário de serviço dedicado, permissões mínimas, secrets fora
do repositório, Redis não exposto publicamente, SMTP institucional e diretório
persistente/gravável apropriado para o schedule do Beat. Worker e Beat devem
ser processos separados. Redis não deve ser configurado como result backend:
as tasks ignoram resultados e persistem o resultado operacional no banco.
