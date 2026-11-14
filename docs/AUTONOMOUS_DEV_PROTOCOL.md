# Protocolo de Desenvolvimento Autônomo Supervisionado

Este protocolo registra AUT-01 a AUT-05, conforme AUT-P1.1 revisado. Não substitui os `AGENTS.md`, as permissões das ferramentas ou a autorização expressa do humano.

## Decisões

- **AUT-01:** commits locais exigem revisão independente e autorização expressa no pacote; o executor é o ARCH.
- **AUT-02:** o DEV é o único escritor de código no working tree, limitado à allowlist; ARCH coordena e QA revisa independentemente.
- **AUT-03:** testes focados e lint devem estar especificados no pacote; exceções valem somente para o pacote que as declara.
- **AUT-04:** no máximo duas rodadas DEV → QA para corrigir defeitos objetivos dentro da allowlist; ampliação de escopo ou terceira rodada exige decisão humana.
- **AUT-05:** o primeiro piloto proposto, AUT-A1, cobre a integração dos componentes reais `EncounterWorkspace` e `EncounterCandidatesPanel`, com dependências externas simuladas. Sua execução exige autorização própria.

## Pacote e ciclo

Um único pacote pode estar ativo por vez, inclusive durante QA, correção, commit ou reconciliação. O pacote aprovado pelo humano define ID, objetivo, baseline Git, allowlist, arquivos protegidos, comandos exatos por agente, escritas incidentais permitidas, critérios de aceite, condição de commit, limite de rodadas e pontos de parada. O ARCH confere baseline, índice, stash, working tree e hashes antes de delegar; divergências interrompem o trabalho.

O DEV implementa e relata os arquivos e seus SHA-256. O ARCH audita o resultado e o QA o revisa de forma independente, sem depender das conclusões do DEV. Arquivos novos não rastreados não aparecem no `git diff`: ARCH e QA devem inspecionar integralmente seu conteúdo e conferir os SHA-256. Após QA aprovado e gates cumpridos, o ARCH só faz stage nominal e commit local se o pacote os autorizar. Cada pacote termina com relatório e parada para decisão humana; não há avanço automático.

## Ledger e interrupções

O AUT-LEDGER registra eventos e estados LIVRE, ATIVO e INDETERMINADO. Só se delega escrita quando LIVRE. Para liberar o escritor, exige-se relato de término, terminal ocioso sem prompt pendente e auditoria de status, diff e hashes contra a allowlist e arquivos protegidos. Resultado desconhecido ou desconexão gera INDETERMINADO e bloqueia novo escritor até reconciliação humana ou técnica comprovada e registrada; reexecução exige nova autorização humana.

O ledger é controle cooperativo: não há trava técnica de exclusividade de escrita confirmada. Essa limitação deve constar do relatório do pacote. Em timeout de comunicação, verifique o estado e não reenvie a tarefa automaticamente.

Diante de qualquer pedido de aprovação humana por ferramenta, sandbox ou agente, interrompa o pacote, registre o bloqueio quando possível e informe comando e motivo ao humano. Ninguém aprova pelo humano, usa `--raw` para responder a prompts, nem contorna o pedido. Retome somente após decisão humana expressa.

## Limites e arquivo dos papéis

Push, merge, deploy, migrations persistentes, instalações e ações externas estão fora da autonomia padrão. Testes seguem os comandos autorizados no pacote e os limites dos guias aplicáveis. Pendências não são consideradas resolvidas automaticamente.

As cópias em `docs/ops/maestri-roles/` são versões sanitizadas das instruções configuradas na revisão AUT-P1.2A, não reproduções byte a byte. `MANIFEST.sha256` verifica os arquivos arquivados a partir da raiz do repositório; seus hashes não representam hashes dos prompts ativos. Alterações dos papéis e de seu arquivo exigem autorização própria; a aplicação e propagação das instruções nas sessões devem ser verificadas separadamente.
