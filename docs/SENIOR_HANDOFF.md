# Handoff para desenvolvimento sênior

Conferência: 2026-11-24. HEAD `7547ad0807a6cb4518805eb9d26302c5ed685ddf`.

## O que é

SIA 2.0 é o sistema de gestão interna do MEB, com Alpinistas, Encontros,
histórico, papéis e dados sensíveis. O browser usa o BFF Next.js para acessar
Django. Autorização é default deny; JWT permanece em cookies HttpOnly,
CSRF exige double-submit e Origin exata, e summary/full delimita privacidade.
Suporte é papel de negócio; superuser é bypass técnico separado. Mídia
protegida não é publicada por `/media`.

## Onde está o código

`backend/` contém API, domínio e legado; `frontend/`, interface, BFF e sessão.
A branch `sia/roadmap-rebaseline` está publicada no HEAD acima, 57 commits à
frente e zero atrás da main `93818ed323c62968f71084c4a4e2eadd697414b5`
(2026-10-08); `origin/HEAD` aponta à main. Não houve merge na main nem
implantação em produção, conforme evidência fornecida. Registros de
coordenação, pacotes, ledger e evidências ficam fora do repositório.

## Funcionalidades implementadas

GE-2A ativa e consulta a equipe canônica, registra convites e oferece seleção
mínima. GE-2B-1 registra resposta definitiva e inicia trabalho confirmado;
GE-2B-2 permite alocar, realocar e desalocar manualmente e atualiza a
composição. Suporte, Diretoria e Fichas operam essas alocações; Coordenação
Geral contextual apenas consulta. O seed de demonstração é idempotente.
Detalhes e contratos em [GE-2](workplans/GE_2_EQUIPE_CANONICA.md).

## Regras de negócio que não devem ser "melhoradas"

Pessoas montam equipes; o sistema não escolhe, distribui, substitui ou realoca
sozinho. Atualização automática na tela apenas sincroniza dados. Resposta de
convite é definitiva e `sem_resposta` não significa pendente. Função lotada é
bloqueio intencional, sem contorno. Contato é externo ao SIA no GE-2; envio
automático de convites não está ativado.

## Validações

- **VERIFICADO pelo ARCH:** GE-2B-2 por HTTP, cliente → BFF → backend e SQLite
  descartável: 153/154 OK; a exceção aceita é um registro de auditoria
  redundante ao desalocar trabalho já aguardando alocação, com 200 e sem
  mudança de dados. Coordenação Geral leu apenas o próprio Encontro (200),
  recebeu 403 em escritas e outros Encontros, com payloads iguais aos de
  Fichas. Integridade SHA-256 e auditorias Git conferidas.
- **REGISTRADO como executado pelo ARCH:** GE-2B-1 por HTTP, 61/61.
- **RELATADO por DEV/QA, não reexecutado pelo ARCH:** frontend 35 arquivos,
  471 testes aprovados, lint sem erros e dois avisos antigos de imagem,
  TypeScript sem erros; backend check e migration check limpos, suíte SQLite
  em memória com 1116 testes OK e 75 pulados.
- **RELATADO por pessoas:** nove cenários visuais GE-2B-2; C5 B1 em
  PostgreSQL com 67 aprovados e um pulado, conforme operador.
- **NÃO VERIFICADO:** Estratégia de migração dos dados históricos: não homologada; ver seção Banco legado.

## Banco legado

Meta aprovada: substituir o SIA legado preservando os dados históricos. A estratégia de migração ainda não foi homologada: não foram executados nem aprovados inventário, mapeamento, deduplicação, migração experimental, reconciliação, rollback e cutover. Verificado no código: backend/core/legacy é só uma camada anticorrupção (contratos, mapeamentos, normalizadores), sem loader nem ETL. Relato não verificado: um registro de bloco anterior diz que o responsável informou não haver dados legados a inventariar; isso não foi verificado por consulta e não deve ser tomado como fato, nem contradiz a meta de preservar o histórico. Em aberto: a decisão sobre os dados do primeiro piloto, migrados ou novos. O banco legado e o sia_dev não foram acessados nesta revisão.

## Pendências conhecidas

- Suíte PostgreSQL completa no HEAD não verificada. No baseline `8f98fdd6`
  houve 27 falhas registradas: 26 envolvendo `FOR UPDATE` em
  `backend/core/services/inscricoes_encontro.py:650-653` e um deadlock em
  `PropostaVioleirosConcurrencyTests`; não se sabe se persistem. Junção externa
  em `select_related` com `FOR UPDATE`, pois `InscricaoEncontro.pessoa` é
  anulável, é apenas hipótese por leitura de código, sem reprodução.
- Build no HEAD, configuração de produção, implantação, backup e homologação
  com usuários reais não verificados. Idempotência de
  `iniciar_trabalho_confirmado` é suspeita não reproduzida; auditoria
  redundante em operações idempotentes é pendência aceita.
- Exposição de campos de encontristas à Coordenação Geral com registros
  preenchidos não verificada; seletor de status e rótulos de estados terminais
  têm prioridade menor. Telas de Formação, MME e preparatórias incompletas.
- Retirar, substituir e registrar resultado de trabalho não estão expostos no
  BFF. Catálogo real de equipes e funções não aprovado; demonstração usa
  fixtures.
- Entrega externa de convites (C5): só o B1 (schema) está implementado e não está ativado. Risco identificado por análise estática, não reproduzido: o worker já existente de entrega de convites para participar (`core.processar_outbox_convite`) chama o provedor dentro de uma transação; uma falha entre a aceitação externa e a gravação poderia duplicar o envio. Não afeta o GE-2, cujo contato é externo ao SIA.

## Como rodar e validar

O caminho padrão com PostgreSQL não foi executado nesta revisão. Consulte o
[README](../README.md) para preparo, configuração local e
comandos exatos. Por política, suítes completas e testes PostgreSQL são
executados manualmente em checkpoints; não confunda SQLite com PostgreSQL.

## Onde ler

[Roteador](00_HOME.md) · [Estado](PROJECT_STATE.md) ·
[Arquitetura](ARCHITECTURE.md) · [Autorização](AUTHORIZATION_MATRIX.md) ·
[GE-2](workplans/GE_2_EQUIPE_CANONICA.md) ·
[Seed](workplans/DEV_SEED.md) · [Instruções gerais](../AGENTS.md) ·
[Backend](../backend/AGENTS.md) · [Frontend](../frontend/AGENTS.md).
