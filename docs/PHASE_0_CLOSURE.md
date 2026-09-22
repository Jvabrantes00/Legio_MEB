# Fase 0 — Fechamento da Estabilização

Este documento registra historicamente o encerramento da Fase 0. O estado vivo,
as decisões atuais e a próxima atividade continuam em `PROJECT_STATE.md`.

## 1. Objetivo da Fase 0

Transformar a base existente do SIA/MEB em uma plataforma estável para a
remodelagem de domínio: segura, testável, executável em PostgreSQL e com
contratos claros entre frontend, BFF e API.

## 2. Estado inicial encontrado

A aplicação já continha cadastros e fluxos relevantes, mas apresentava
configuração sensível acoplada ao código, cobertura insuficiente, contratos
frontend/API divergentes, autorização fragmentada, mídia sem fronteira
consolidada e dependência conceitual do legado. O ambiente e o build também
precisavam de uma referência reproduzível.

## 3. Resumo 0A–0J

| Etapa | Resultado principal |
|---|---|
| 0A | Configuração e secrets retirados do código; hosts, CORS, CSRF e debug passaram a ser controlados por ambiente. |
| 0B | Dependências, versões, lint, Tailwind e build foram estabilizados. |
| 0C | Suíte de regressão e settings isolados de teste estabeleceram o baseline. |
| 0D | Status, CPF, atomicidade e agregados do dashboard foram corrigidos. |
| 0E | Roles, default deny, summary/full, mídia protegida, auditoria e admin técnico foram consolidados. |
| 0F | JWT via BFF, cookies HttpOnly, CSRF, Origin exata, rotação, blacklist, logout e guards foram estabilizados. |
| 0G | Paginação, formulários, payloads, capabilities, contratos de apresentação e erros foram alinhados. |
| 0H | PostgreSQL e a camada pura `core/legacy` foram validados sem antecipar a migração real. |
| 0I | Allowlists, logging sem PII, atomicidade de lotes/mídia e casos-limite remanescentes foram resolvidos. |
| 0J | O gate transversal foi aprovado e liberou formalmente a Fase 1. |

## 4. Arquitetura resultante

A fronteira estabilizada é:

```text
Browser
  → Next.js / BFF
    → Django REST Framework
      → PostgreSQL
```

O browser usa somente o BFF para autenticação e recursos de negócio. O backend
permanece autoridade sobre autorização, validação, dados e contratos.

## 5. Segurança resultante

Secrets não são versionados. Configurações variáveis pertencem ao ambiente.
JWT não é entregue ao JavaScript; access e refresh permanecem em cookies
HttpOnly. Mutações no BFF exigem double-submit e igualdade exata da Origin.
Destinos arbitrários, wildcard amplo e URL concreta de tunnel não fazem parte
da configuração versionada.

## 6. Autorização e privacidade

A política é default deny. Superuser é bypass técnico e não representa a role
Suporte. A matriz documenta os papéis de negócio e suas superfícies. Contratos
summary/full são fronteiras de privacidade. Mídia é entregue somente por
actions autenticadas, e nested mismatch retorna `404`.

## 7. Integridade e atomicidade

CPF é opcional, normalizado e único quando informado. Participações preservam
as constraints existentes. Operações com múltiplas escritas usam transações;
estoque usa bloqueio de concorrência. Fluxos de lote e mídia têm cobertura de
rollback e compensação. Migrations permanecem incrementais e revisáveis.

## 8. Frontend/API

O frontend respeita capabilities sem substituir autorização do backend.
Criação de Alpinista nasce como `pendente`, edição usa `PATCH`, paginação
segue o envelope DRF e o dashboard usa agregados do backend. Funções e
Participações de Encontro são listas diretas no contrato atual.

No gate 0J foi corrigido o último desalinhamento: o detalhe gerenciado de
Encontro tratava essas duas listas como paginadas. O consumidor foi ajustado e
dois testes de regressão foram adicionados.

## 9. Testes e baseline final

| Verificação | Resultado final |
|---|---|
| Backend | 192/192 PASS |
| Frontend | 104/104 PASS em 9 arquivos |
| Lint | 0 erros; 2 warnings `no-img-element` justificados |
| TypeScript | PASS |
| Next.js build | PASS |
| Django check | PASS |
| Migrations | Nenhuma pendente |

## 10. Infraestrutura de desenvolvimento

O ambiente de referência usa notebook Ubuntu, PostgreSQL local e serviços
systemd para backend, frontend e tunnel, com desenvolvimento por Remote SSH.
Arquivos de ambiente e credenciais permanecem locais. A renovação da
credencial do DevTunnel é uma rotina operacional, não uma mudança no código.

## 11. Legado

`core/legacy` é uma camada anticorrupção sem ORM, conexão MySQL, escrita ou
escolha de novas chaves. Ela transforma registros raw em contratos canônicos,
issues e quarentena. A importação final dos aproximadamente 3000 registros
somente ocorrerá depois da estabilização do domínio da Fase 1.

## 12. Débitos aceitos

Permaneceram como backlog não bloqueante: logging estruturado, reconciliação
periódica de mídia, refresh distribuído, duração absoluta de sessão,
agendamento de `flushexpiredtokens`, dois warnings de imagem protegida,
decisão semântica sobre unicidade de Encontrista e renovação operacional da
credencial do DevTunnel. Riscos e gatilhos são mantidos em
`PROJECT_STATE.md`.

## 13. Lições técnicas

- Contratos precisam ser validados dos dois lados da integração.
- Ocultar dados na UI não substitui um serializer mínimo.
- Autorização deve partir de negação, com exceções explícitas e testadas.
- Banco, storage e auditoria exigem compensação além da transação local.
- Migração de legado deve seguir o domínio estabilizado, não defini-lo.
- Métricas e totais devem vir de agregados, nunca de uma página parcial.

## 14. Invariantes para a Fase 1

A Fase 1 deve preservar default deny, separação entre superuser e roles,
summary/full, BFF como fronteira, JWT HttpOnly, CSRF com Origin exata, mídia
protegida, semântica HTTP, paginação correta, migrations revisáveis,
atomicidade, histórico, isolamento do legado e o baseline de testes. Uma quebra
necessária deve ter impacto, compatibilidade, migration e testes documentados
antes da implementação.

## 15. Critério de saída

Todos os critérios críticos e altos do gate foram atendidos. Os débitos
restantes têm risco conhecido, justificativa de deferimento e gatilho futuro.

**0J APROVADA — FASE 0 CONCLUÍDA — FASE 1 LIBERADA**
