# SIA/MEB — Contexto do Projeto

Este arquivo é o ponto de entrada da documentação. Ele roteia o contexto; não
substitui os documentos de referência nem os `AGENTS.md` aplicáveis.

## Estado atual

- Fase 0 concluída.
- Fase 1 em andamento.
- 1B.3B — Pessoa e backfill inicial concluída.
- Próxima implementação: 1B.3C — Grupo e Frequência.
- A criação automática de `PerfilAlpinista` continua bloqueada até a
  reconciliação das evidências do legado.

O estado vivo e o roadmap estão em [[PROJECT_STATE]].

## Como carregar contexto

### Regra geral

1. Leia e aplique primeiro os `AGENTS.md` que alcançam o arquivo ou diretório
   da tarefa.
2. Use este arquivo como roteador.
3. Não leia toda a pasta `docs/` por padrão.
4. Carregue somente os documentos relacionados à tarefa atual.
5. Não releia documentos quando a informação necessária já estiver
   suficientemente disponível no contexto da sessão.
6. Amplie a leitura apenas quando surgir evidência de dependência adicional.

### Arquitetura

Para decisões ou mudanças arquiteturais, consulte:

- [[ARCHITECTURE]]
- [[PROJECT_STATE]]

### Autorização, papéis e dados sensíveis

Para permissions, roles, escopo, privacidade ou dados sensíveis, consulte:

- [[AUTHORIZATION_MATRIX]]
- [[ARCHITECTURE]]

### Backend, domínio e migrations

Para models, migrations, services ou regras de domínio, consulte:

- [[PROJECT_STATE]]
- [[ARCHITECTURE]]
- a decisão ou documentação específica do domínio afetado, quando existir.

Leia também `/backend/AGENTS.md`. Os models, migrations e contratos atuais
continuam sendo a fonte técnica primária da implementação.

### Frontend, BFF e contratos

Leia `/frontend/AGENTS.md` e carregue somente a documentação do contrato,
feature ou fronteira arquitetural afetada. Para autenticação, BFF, mídia ou
summary/full, consulte também [[ARCHITECTURE]] e, quando houver autorização
envolvida, [[AUTHORIZATION_MATRIX]].

### Compatibilidade e regressão da Fase 0

Consulte [[PHASE_0_CLOSURE]] somente quando a tarefa envolver:

- compatibilidade com o baseline estabilizado;
- invariantes ou regressão da Fase 0;
- decisões históricas relevantes para a alteração.

## AGENTS

Os arquivos `AGENTS.md` permanecem em suas posições originais porque a
localização define seu escopo:

- `/AGENTS.md` — projeto inteiro;
- `/backend/AGENTS.md` — backend;
- `/frontend/AGENTS.md` — frontend.

Use [[AGENTS_INDEX]] como mapa de escopo. O índice não substitui a leitura dos
AGENTS aplicáveis.

## Navegação

- [[PROJECT_STATE]] — estado vivo, decisões e roadmap.
- [[ARCHITECTURE]] — fronteiras técnicas e arquitetura corrente.
- [[AUTHORIZATION_MATRIX]] — autorização implementada.
- [[PHASE_0_CLOSURE]] — fechamento histórico da Fase 0.
- [[AGENTS_INDEX]] — localização e alcance dos guias de agentes.
