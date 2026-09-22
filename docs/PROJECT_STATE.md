# SIA/MEB — Estado do Projeto

## Estado atual

- Data: 22 de setembro de 2026.
- Branch: `sia/fase-0-estabilizacao`.
- **FASE 0 — ESTABILIZAÇÃO: CONCLUÍDA**
- **FASE 1 — REMODELAGEM DE DOMÍNIO: LIBERADA**

## Roadmap

| Etapa | Estado |
|---|---|
| 0A Segurança e configuração | ✅ Concluída |
| 0B Ambiente, dependências e lint | ✅ Concluída |
| 0C Base de regressão | ✅ Concluída |
| 0D Dados, CPF, atomicidade e dashboard | ✅ Concluída |
| 0E Autorização, privacidade, mídia e auditoria | ✅ Concluída |
| 0F Autenticação, JWT e BFF | ✅ Concluída |
| 0G Integração frontend/API | ✅ Concluída |
| 0H PostgreSQL e legado | ✅ Concluída |
| 0I Débitos técnicos restantes | ✅ Concluída |
| 0J Gate e auditoria final | ✅ Concluída |
| Fase 1 Remodelagem de domínio | Liberada; não iniciada |

## Histórico — Fase 0

| Etapa | Objetivo | Principais entregas | Status |
|---|---|---|---|
| 0A | Segurança e configuração | Secrets removidos do código; DEBUG, hosts, CORS e CSRF configuráveis; ambientes locais ignorados. | Concluída |
| 0B | Ambiente e dependências | Requirements reproduzíveis; versões Python/Node estabilizadas; ESLint, Tailwind e build corrigidos. | Concluída |
| 0C | Base de regressão | Suíte inicial, settings isolados de teste e piso para prevenir regressões. | Concluída |
| 0D | Dados | Status canônicos; CPF nullable, único e normalizado; atomicidade e dashboard estabilizados. | Concluída |
| 0E | Autorização e privacidade | Roles oficiais, default deny, summary/full, domínios especializados, mídia protegida, auditoria e admin técnico separado. | Concluída |
| 0F | Autenticação | JWT via BFF, cookies HttpOnly, CSRF double-submit, Origin exata, rotação, blacklist, logout e guards. | Concluída |
| 0G | Integração frontend/API | Paginação, formulários, payloads, capabilities, summary/full, dashboard, tipos e erros alinhados. | Concluída |
| 0H | PostgreSQL e legado | Schema legado auditado, `core/legacy` criado e PostgreSQL descartável validado sem antecipar migração real. | Concluída |
| 0I | Débitos técnicos | Allowlists, remoção de PII em stdout, atomicidade, limpeza de permissão morta e casos-limite estabilizados. | Concluída |
| 0J | Gate final | Segurança, sessão, autorização, privacidade, dados, mídia, legado, infraestrutura, documentação e regressão aprovados. | Concluída |

O fechamento histórico consolidado está em `docs/PHASE_0_CLOSURE.md`.

## Decisões fechadas

### Alpinista

- Um novo Alpinista nasce com status `pendente`.
- Edição no frontend usa `PATCH`.
- E-mail e telefone são obrigatórios no contrato atual.
- CPF é opcional, normalizado e único quando informado.
- CPF inválido ou duplicado é rejeitado.
- Campos opcionais podem ser limpos com `null` onde o contrato permite.
- Neurodivergência `false` limpa o tipo associado.
- Sacramentos preservam estado tri-state: `true`, `false` ou `null`.
- Papéis de gestão recebem perfil full; demais papéis reconhecidos recebem
  summary.
- A foto é protegida e não é publicada diretamente por `/media`.

### Encontro

- Tipos atuais: `Escalada`, `AVC`, `Esppa` e `Acampamento`.
- Status atuais: `em_agendamento` e `agendado`.
- `cancelado` não faz parte do contrato atual.
- Suporte, Diretoria e Fichas recebem full e podem gerir Encontros.
- Comunicação recebe summary e usa a galeria dedicada.
- Participações e funções permanecem recursos próprios e protegidos.

### Dashboard

- Usa agregados calculados pelo backend.
- Nunca infere totais a partir da primeira página de um recurso paginado.
- Não exibe métricas falsas nem “últimas inscrições” inventadas.
- Está disponível para Suporte, Diretoria, Fichas e superuser técnico.

### Autenticação e sessão

- O browser conversa com o BFF do Next.js, não diretamente com Django.
- JWT access e refresh ficam em cookies HttpOnly.
- Refresh usa rotação e blacklist do token anterior.
- `/api/auth/me` fornece a identidade mínima e os papéis reconhecidos.
- O guard diferencia ausência de sessão de identidade autenticada sem role.
- CSRF usa double-submit e validação exata de `Origin`.
- `SIA_APP_ORIGIN` é a origem canônica; aliases de tunnel não são
  intercambiáveis.

## Baseline de testes

Baseline integral final validado na 0J:

| Verificação | Resultado |
|---|---|
| Backend | 192/192 testes passando |
| Frontend | 104/104 testes passando em 9 arquivos |
| Lint | 0 erros; 2 warnings justificados |
| TypeScript | PASS |
| Build Next.js | PASS |
| Django check | PASS |
| Migrations | Nenhuma pendente |

Os dois warnings são de `no-img-element` nas imagens protegidas de
Alpinistas. A decisão atual evita encaminhar cookies de autenticação a um
otimizador de imagens sem um contrato explícito para isso.

## Infraestrutura de desenvolvimento

- Notebook Ubuntu dedicado.
- Acesso de desenvolvimento por VS Code Remote SSH.
- PostgreSQL local no servidor.
- Serviços systemd: `sia-backend.service`, `sia-frontend.service` e
  `sia-tunnel.service`.
- DevTunnel persistente para acesso ao frontend.
- A URL corrente é configuração local e não deve ser documentada ou
  hardcoded.
- `.env`, `.env.local` e arquivos locais do tunnel permanecem fora do Git.

## Resultado da 0I

- Serializers remanescentes usam allowlists explícitas sem mudar contratos.
- O signal de participação não imprime mais o nome do Alpinista em stdout.
- `HasRecognizedSiaRole`, sem uso, foi removido.
- Remoção em lote de encontristas é atômica e possui teste de rollback.
- A seleção da função Encontrista é determinística mesmo diante de duplicatas.
- O histórico reconhece “Coordenador dos Dirigentes” sem diferenciar case.
- Comentários comprovadamente obsoletos de settings foram corrigidos.
- Fluxos de mídia agrupam banco e auditoria em transação, preservam o arquivo
  anterior em rollback e removem novo upload quando a transação falha.

## Resultado da 0J

- Gate final aprovado sem falhas críticas ou altas sem mitigação.
- Um bug de contrato no detalhe gerenciado de Encontro foi corrigido: funções
  e participações não paginadas agora são consumidas como listas diretas.
- O backend preservou listas diretas nesses endpoints e dois testes de regressão
  foram adicionados ao frontend.
- Smoke pelo BFF local validou login, sessão, dashboard, Alpinistas, Encontros,
  logout e rejeição de Origin incorreta, sem deixar dados temporários.
- O smoke externo não foi executado porque a credencial local do DevTunnel
  expirou; a unit permanece habilitada, mas requer novo login e inicialização
  antes da próxima validação remota. Essa pendência operacional não bloqueia a
  remodelagem de domínio da Fase 1.

## Invariantes herdadas da Fase 0

A modelagem e a implementação da Fase 1 devem preservar:

1. Autorização default deny.
2. Superuser técnico separado das roles de negócio.
3. Contratos Alpinista summary/full como fronteira de privacidade.
4. O browser sem acesso ou manipulação de JWT.
5. O BFF do Next.js como fronteira entre browser e backend.
6. Access e refresh em cookies HttpOnly.
7. CSRF double-submit com comparação exata de Origin.
8. Ausência de rota pública para `/media`.
9. Semântica HTTP de `400`, `401`, `403`, `404` e `405`.
10. Paginação sem assumir que a primeira página representa todo o dataset.
11. Migrations incrementais, revisáveis e coerentes com dados existentes.
12. Atomicidade em operações com múltiplas escritas.
13. Preservação de histórico durante a remodelagem.
14. `core/legacy` como fonte de transformação, nunca como modelo-alvo.
15. O baseline de testes da Fase 0, salvo redução explicitamente justificada.

## Manutenção operacional

Tokens expirados da blacklist devem ser removidos periodicamente com:

```bash
cd backend
./.venv/bin/python manage.py flushexpiredtokens
```

A periodicidade pertence à operação do ambiente; a 0I não adiciona scheduler.

## Débitos aceitos ao fim da Fase 0

Esses itens formam backlog conhecido e não bloqueiam a Fase 1.

| Débito | Risco atual | Motivo do deferimento | Gatilho futuro |
|---|---|---|---|
| Logging técnico estruturado | Baixo: diagnóstico descentralizado. | Instância única e auditoria funcional. | Centralização de logs ou observabilidade. |
| Reconciliação periódica de mídia | Baixo: órfãos em falha externa abrupta. | Compensação transacional cobre os fluxos atuais. | Storage remoto ou operação crítica. |
| Refresh distribuído | Baixo: coordenação somente por processo. | BFF executa em uma instância. | Escala horizontal. |
| Duração absoluta máxima de sessão | Médio: ausência de limite adicional ao ciclo dos tokens. | Política formal ainda não definida. | Requisito de segurança ou operação. |
| Agendamento de `flushexpiredtokens` | Baixo: crescimento da blacklist. | Rotina pode ser executada manualmente no ambiente atual. | Operação contínua ou volume relevante. |
| Dois warnings `no-img-element` | Baixo: custo potencial de performance. | Imagens protegidas exigem sessão; otimização não pode vazar cookies. | Loader autenticado com contrato seguro. |
| Unicidade semântica da função Encontrista | Baixo: duplicatas possíveis, com seleção determinística. | Regra de domínio ainda não fechada. | Decisão de domínio na Fase 1. |
| Renovação da credencial DevTunnel | Baixo e operacional: smoke remoto pode ficar indisponível. | Credencial pertence ao ambiente, não ao código. | Expiração ou falha de autenticação do tunnel. |

## Fase 1 — direção de modelagem

A Fase 1 começa pela modelagem do domínio e pelas decisões de migração e
compatibilidade, não pela implementação isolada de telas. O schema definitivo
ainda não está definido.

Direções conhecidas:

- Grupo pós-encontro como entidade de domínio e preservação do histórico de
  grupo.
- Paróquia e Região Administrativa como conceitos explícitos.
- Status e histórico de vínculo.
- Separação entre pessoa/Alpinista, inscrição e participação.
- Ciclo de Encontros, funções e equipes.
- Regras advisory e explicáveis em vez de hard blocks indevidos.
- Palestras e seus históricos.
- Eventos e evolução futura da área Meu SIA.
- Requisitos e processos LGPD.
- Migração final dos aproximadamente 3000 registros somente depois de domínio,
  mappings e profiling estarem estáveis.
