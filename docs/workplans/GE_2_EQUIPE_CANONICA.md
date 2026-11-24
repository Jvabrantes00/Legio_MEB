# GE-2 — equipe canônica

## Estado de implementação (verificado em 2026-11-24)

- GE-2A (`e4ac93c`): ativação, convites de trabalho e seletor mínimo da equipe canônica.
- GE-2B-1 (`db3bc5e`): Fichas registra resposta definitiva
  `confirmado`, `recusado` ou `sem_resposta` em
  `POST convites-encontros/{id}/responder-trabalho/` com `{status}`.
  `POST trabalhos-encontros/` com `{convite_id, confirmar_avisos?}` inicia
  trabalho confirmado: com função proposta nasce alocado; sem ela, aguardando
  alocação. Avisos exigem confirmação; bloqueios de elegibilidade ou função
  lotada não podem ser contornados.
- GE-2B-2 (`7547ad0`): alocação, realocação e desalocação manuais via
  `POST trabalhos-encontros/{id}/alocar|realocar|desalocar/`. As duas primeiras
  recebem `{role_equipe_id, confirmar_avisos?}`; desalocar recebe corpo vazio
  ou `{}`. A função pertence ao mesmo Encontro. Desalocar libera a vaga e
  retorna a aguardando alocação, preservando trabalho e convite; não é
  retirada definitiva. A interface oferece Alocar quando aguardando e
  Realocar/Desalocar quando alocado. Suporte, Diretoria e Fichas operam;
  Coordenação Geral contextual apenas consulta.

Pessoas montam as equipes manualmente; o SIA não escolhe, distribui, substitui
nem realoca sozinho. A atualização automática na tela apenas sincroniza dados.
A resposta é definitiva, `sem_resposta` não significa pendente, e contato é
externo ao SIA; não há envio automático de convites ativado.

**VERIFICADO pelo ARCH:** HTTP GE-2B-2, cliente → BFF → backend com SQLite
descartável, 153/154 verificações OK; divergência aceita de auditoria redundante
na desalocação idempotente. Coordenação Geral consultou apenas o próprio
Encontro e recebeu 403 em escritas e outros Encontros; payloads iguais aos de
Fichas. **REGISTRADO pelo ARCH:** GE-2B-1, 61/61. **RELATADO por pessoas:**
validação visual GE-2B-2 em nove cenários. **NÃO VERIFICADO:** idempotência de
`iniciar_trabalho_confirmado`, suspeita não reproduzida.

Pendências: catálogo real de equipes e funções não aprovado; retirar,
substituir e registrar resultado não expostos no BFF; auditoria redundante
aceita; entrega externa de convites (C5): fora do escopo do GE-2; ver o bloco abaixo.

## Entrega externa de convites e o worker existente (fora do escopo do GE-2)

O GE-2 não envia convites: o contato com as pessoas é externo ao SIA e os convites de trabalho (`finalidade=trabalhar`) não passam por nenhum worker de entrega.

**Fluxo existente (anterior ao GE-2).** A infraestrutura assíncrona das fases R.3I.14 e R.3I.15 entrega convites para **participar** de Encontros, por campanha e oportunidade, com adaptadores de e-mail (SMTP) e WhatsApp (mock). Seu worker é a tarefa `core.processar_outbox_convite`, que chama `processar_outbox_entrega_convite` (`backend/core/services/entregas_convites.py`), decorada com `@transaction.atomic`.

**Risco identificado por análise (não reproduzido).** Esse worker chama o provedor dentro da transação. Se houver falha depois de o provedor aceitar a mensagem e antes de o resultado ser gravado, uma nova tentativa poderia reenviá-la. A origem é o diagnóstico C5.1, feito por inspeção estática e reconfirmado por leitura do código em 2026-11-24. **Nenhuma falha de envio duplicado foi reproduzida nem há registro de ocorrência.**

**C5.** É o trabalho planejado para reconciliar esse fluxo. Está implementado **apenas o B1 (schema e integridade, migrations 0051 e 0052)**; B2, B3 e B4 não foram iniciados e o novo fluxo **não está ativado**. O B1 não alterou o worker existente.

Observação do ambiente: nenhum processo Celery estava em execução no ambiente de desenvolvimento quando conferido em 2026-11-24; produção não foi verificada.

## Registro de planejamento anterior ao GE-2B (histórico)

GE-2A cobre ativação com justificativa, preparação, consulta de funções e vagas,
seleção mínima de Alpinistas e registro e consulta de convites de trabalho.
Na listagem de convites, `encontro` ausente ou vazio retorna 405; filtro não
numérico retorna 400, e o filtro válido retorna somente convites de trabalho.
O contato ocorre fora do SIA. O catálogo real de equipes e funções permanece
aberto: a demonstração usa fixtures isoladas e a operação real depende de sua
aprovação e carga.

GE-2B tratará o registro por Fichas da resposta recebida em contato externo e
as operações posteriores de trabalho e alocação. Não há token público nem
autoatendimento, novos estados, reconvite ou cancelamento neste escopo. A
resposta do convite é definitiva e não há caminho suportado para corrigi-la;
`sem_resposta` não significa pendente.

O serviço `criar_convite_trabalho` reutiliza convite existente. Na API HTTP,
o validador de unicidade preserva a resposta 400 para POST duplicado, sem
alterar o convite existente; essa semântica também preserva o fluxo de participação.
