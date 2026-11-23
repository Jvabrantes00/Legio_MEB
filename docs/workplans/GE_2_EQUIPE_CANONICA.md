# GE-2 — equipe canônica

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
