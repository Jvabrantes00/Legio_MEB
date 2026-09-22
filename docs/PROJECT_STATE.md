# SIA/MEB — Estado do Projeto

## Última atualização

- Data: 22 de setembro de 2026.
- Branch: `sia/fase-0-estabilizacao`.
- Fase atual: **Fase 0 — estabilização**, em fechamento.

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
| 0I Débitos técnicos restantes | ⏳ Próxima |
| 0J Gate e auditoria final | ⏳ Pendente |
| Fase 1 Remodelagem de domínio | Depois de 0J |

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

Último baseline integral validado ao final da 0G:

| Verificação | Resultado |
|---|---|
| Backend | 184/184 testes passando |
| Frontend | 102/102 testes passando em 9 arquivos |
| Lint | 0 erros; 2 warnings justificados |
| TypeScript | PASS |
| Build Next.js | PASS |

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

## Débitos conhecidos para 0I

- Substituir `fields = '__all__'` remanescentes por allowlists explícitas,
  priorizando serializers de dados sensíveis.
- Introduzir logging estruturado sem registrar dados pessoais ou tokens.
- Revisar atomicidade conjunta entre banco, arquivo físico e log de auditoria.
- Avaliar remoção ou justificativa final de `HasRecognizedSiaRole`.
- Revisar o fluxo `remover-encontristas`.
- Tratar explicitamente possível `MultipleObjectsReturned` na resolução de
  Encontrista.
- Comparar historicamente o significado de Coordenador dos Dirigentes antes
  de modelar equivalência.
- Remover comentários e referências obsoletas em settings.
- Definir rotina para detectar e limpar órfãos físicos de mídia.
- Definir rotina operacional para tokens expirados da blacklist.
- Avaliar coordenação distribuída de refresh caso existam múltiplas
  instâncias do BFF.
- Definir duração absoluta de sessão além das expirações deslizantes.
- Manter justificados ou resolver com segurança os warnings de imagem
  protegida.

## Fase 1 — direção, não implementação

- Grupo pós-encontro como entidade própria.
- Histórico de grupo, paróquia e RA.
- Ciclo explícito de inscrição e participação.
- Regras de domínio dos diferentes tipos de encontro.
- Capacidades advisory e sugestões explicáveis de equipe.
- Área “Meu SIA”.
- Requisitos e processos LGPD.
- Loader do legado somente após estabilização do domínio, mappings e
  profiling dos dados reais.
