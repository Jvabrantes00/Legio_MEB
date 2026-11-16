const RESULTS = ["ELEGIVEL", "AVISO", "BLOQUEIO"] as const;
const CODES = ["PERFIL_ALPINISTA_AUSENTE", "ALPINISTA_INATIVO", "ATIVIDADE_NAO_DETERMINADA", "AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA", "CAMINHO_FORMATIVO_NAO_DETERMINADO", "REVISAO_MANUAL_TRABALHO_AVC", "REVISAO_MANUAL_TRABALHO_ACAMPAMENTO", "CAPACIDADE_MINIMA_NAO_ATINGIDA", "CAPACIDADE_MAXIMA_EXCEDIDA", "COMPOSICAO_ESTRUTURAL_INCOMPLETA", "QUANTIDADE_ESTRUTURAL_EXCEDIDA"] as const;
const STATUSES = ["aguardando_alocacao", "alocado", "trabalhou", "faltou", "retirado"] as const;
type Result = typeof RESULTS[number];
type Reason = { codigo: typeof CODES[number]; categoria: Result; mensagem: string; contexto?: Record<string, number> };
type Assessment = { resultado: Result; motivos: Reason[] };
type Role = { id: number; codigo: string; nome: string; ordem: number; quantidade_estrutural: number | null; concede_registro_presenca: boolean; trabalhos: { id: number; pessoa_id: number; pessoa_nome: string; status: typeof STATUSES[number] }[] };
export type EncounterTeam = { id: number; encontro_id: number; codigo: string; nome: string; ordem: number; capacidade_minima_recomendada: number | null; capacidade_maxima_recomendada: number | null; capacidade: Assessment; composicao: Assessment; roles: Role[] };

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Estrutura de equipe inválida.");
  return value as Record<string, unknown>;
}
function text(value: unknown): string { if (typeof value !== "string") throw new Error("Texto inválido."); return value; }
function integer(value: unknown): number { if (typeof value !== "number" || !Number.isInteger(value) || value < 0) throw new Error("Inteiro inválido."); return value; }
function nullableInteger(value: unknown): number | null { return value === null ? null : integer(value); }
function bool(value: unknown): boolean { if (typeof value !== "boolean") throw new Error("Booleano inválido."); return value; }
function enumeration<T extends string>(value: unknown, values: readonly T[]): T { if (typeof value !== "string" || !values.includes(value as T)) throw new Error("Enum inválido."); return value as T; }
function list<T>(value: unknown, parse: (value: unknown) => T): T[] { if (!Array.isArray(value)) throw new Error("Lista inválida."); return value.map(parse); }
function reason(value: unknown): Reason {
  const r = record(value);
  const result: Reason = { codigo: enumeration(r.codigo, CODES), categoria: enumeration(r.categoria, RESULTS), mensagem: text(r.mensagem) };
  if (r.contexto !== undefined) {
    const context = record(r.contexto);
    result.contexto = {};
    for (const key of ["equipe_id", "role_id", "ocupacao", "referencia", "quantidade_estrutural"]) {
      if (key in context) result.contexto[key] = integer(context[key]);
    }
  }
  return result;
}
function assessment(value: unknown): Assessment { const r = record(value); return { resultado: enumeration(r.resultado, RESULTS), motivos: list(r.motivos, reason) }; }
function role(value: unknown): Role {
  const r = record(value);
  return { id: integer(r.id), codigo: text(r.codigo), nome: text(r.nome), ordem: integer(r.ordem), quantidade_estrutural: nullableInteger(r.quantidade_estrutural), concede_registro_presenca: bool(r.concede_registro_presenca), trabalhos: list(r.trabalhos, (value) => { const t = record(value); return { id: integer(t.id), pessoa_id: integer(t.pessoa_id), pessoa_nome: text(t.pessoa_nome), status: enumeration(t.status, STATUSES) }; }) };
}
export function parseEncounterTeams(value: unknown): EncounterTeam[] {
  return list(value, (value) => { const r = record(value); return { id: integer(r.id), encontro_id: integer(r.encontro_id), codigo: text(r.codigo), nome: text(r.nome), ordem: integer(r.ordem), capacidade_minima_recomendada: nullableInteger(r.capacidade_minima_recomendada), capacidade_maxima_recomendada: nullableInteger(r.capacidade_maxima_recomendada), capacidade: assessment(r.capacidade), composicao: assessment(r.composicao), roles: list(r.roles, role) }; });
}
export function buildEncounterTeamPath(encontroId: number): string {
  if (!Number.isSafeInteger(encontroId) || encontroId <= 0) throw new Error("Encontro inválido.");
  return `/encontros/${encontroId}/workspace/equipes/`;
}
