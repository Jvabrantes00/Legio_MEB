export type EncounterWorkspaceCandidateOrigin = "INSCRICAO" | "PESSOA" | "AVULSO";
export type EncounterWorkspaceCandidateStatus =
  | "INSCRITO"
  | "CANCELADO"
  | "AGUARDANDO_DECISAO"
  | "APTO"
  | "NAO_APTO"
  | "CONFIRMADO";
export type EncounterWorkspaceAptitude =
  | "apto"
  | "nao_apto"
  | "aguardando_decisao_diretoria"
  | null;

export type EncounterWorkspaceCapabilities = {
  consultar_resumo: boolean;
  consultar_encontristas: boolean;
  consultar_contato: boolean;
  acessar_pre_encontro: boolean;
  acessar_equipes: boolean;
  acessar_formacao: boolean;
  acessar_agenda: boolean;
};

export type EncounterCandidateSummary = {
  ref: { origem_tipo: EncounterWorkspaceCandidateOrigin; origem_id: string };
  nome: string;
  origem: { codigo: EncounterWorkspaceCandidateOrigin; label: string };
  situacao: { codigo: EncounterWorkspaceCandidateStatus; label: string };
  presenca_pre: boolean;
  aptidao: EncounterWorkspaceAptitude;
  pessoa_id: number | null;
};

export type EncounterCandidateFull = EncounterCandidateSummary & {
  telefone: string;
};

export type EncounterCandidatePage<T extends EncounterCandidateSummary = EncounterCandidateSummary> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type EncounterWorkspaceSummary = {
  encontro: { id: number; nome: string; tipo: string; local: string };
  lifecycle: string;
  agenda: {
    configurada: boolean;
    oficializada: boolean;
    quantidade_itens: number;
    proximo_item: string | null;
    datas_principais: string[];
    pre_encontro_data: string | null;
  };
  encontristas: {
    inscricoes_recebidas: number;
    total_funil: number;
    por_situacao: Record<EncounterWorkspaceCandidateStatus, number>;
  };
  pre_encontro: {
    configurado: boolean;
    data: string | null;
    capacidade: number | null;
    quantidade_checkins: number;
    quantidade_aptos: number;
    quantidade_aguardando_decisao: number;
  };
  equipes: {
    quantidade_equipes: number;
    quantidade_funcoes: number;
    vagas_estruturais: number | null;
    vagas_preenchidas: number;
  };
  formacao: {
    total_sessoes: number;
    planejadas: number;
    realizadas: number;
    canceladas: number;
  };
  alertas: { codigo: string; mensagem: string }[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(record: Record<string, unknown>, key: string): string {
  if (typeof record[key] !== "string") throw new Error(`Campo inválido: ${key}.`);
  return record[key];
}

function integer(record: Record<string, unknown>, key: string, nullable = false): number | null {
  if (nullable && record[key] === null) return null;
  const value = record[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`Campo inválido: ${key}.`);
  }
  return value;
}

function bool(record: Record<string, unknown>, key: string): boolean {
  if (typeof record[key] !== "boolean") throw new Error(`Campo inválido: ${key}.`);
  return record[key];
}

function nullableText(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  if (value === null) return null;
  if (typeof value === "string") return value;
  throw new Error(`Campo inválido: ${key}.`);
}

const ORIGINS = ["INSCRICAO", "PESSOA", "AVULSO"] as const;
const STATUSES = ["INSCRITO", "CANCELADO", "AGUARDANDO_DECISAO", "APTO", "NAO_APTO", "CONFIRMADO"] as const;
const APTITUDES = ["apto", "nao_apto", "aguardando_decisao_diretoria"] as const;

function enumValue<T extends string>(value: unknown, values: readonly T[], key: string): T {
  if (typeof value !== "string" || !values.includes(value as T)) {
    throw new Error(`Campo inválido: ${key}.`);
  }
  return value as T;
}

export function parseEncounterWorkspaceCapabilities(value: unknown): EncounterWorkspaceCapabilities {
  if (!isRecord(value)) throw new Error("Capabilities do Workspace inválidas.");
  return {
    consultar_resumo: bool(value, "consultar_resumo"),
    consultar_encontristas: bool(value, "consultar_encontristas"),
    consultar_contato: bool(value, "consultar_contato"),
    acessar_pre_encontro: bool(value, "acessar_pre_encontro"),
    acessar_equipes: bool(value, "acessar_equipes"),
    acessar_formacao: bool(value, "acessar_formacao"),
    acessar_agenda: bool(value, "acessar_agenda"),
  };
}

export function parseEncounterCandidateSummary(value: unknown): EncounterCandidateSummary {
  if (!isRecord(value) || !isRecord(value.ref) || !isRecord(value.origem) || !isRecord(value.situacao)) {
    throw new Error("Encontrista inválido.");
  }
  const aptitude = value.aptidao === null
    ? null
    : enumValue(value.aptidao, APTITUDES, "aptidao");
  const pessoaId = integer(value, "pessoa_id", true);
  return {
    ref: {
      origem_tipo: enumValue(value.ref.origem_tipo, ORIGINS, "origem_tipo"),
      origem_id: text(value.ref, "origem_id"),
    },
    nome: text(value, "nome"),
    origem: {
      codigo: enumValue(value.origem.codigo, ORIGINS, "origem.codigo"),
      label: text(value.origem, "label"),
    },
    situacao: {
      codigo: enumValue(value.situacao.codigo, STATUSES, "situacao.codigo"),
      label: text(value.situacao, "label"),
    },
    presenca_pre: bool(value, "presenca_pre"),
    aptidao: aptitude,
    pessoa_id: pessoaId,
  };
}

export function parseEncounterCandidateFull(value: unknown): EncounterCandidateFull {
  if (!isRecord(value)) throw new Error("Encontrista completo inválido.");
  return { ...parseEncounterCandidateSummary(value), telefone: text(value, "telefone") };
}

export function parseEncounterCandidatePage<T extends EncounterCandidateSummary>(
  value: unknown,
  parseItem: (item: unknown) => T = parseEncounterCandidateSummary as (item: unknown) => T,
): EncounterCandidatePage<T> {
  if (!isRecord(value) || !Array.isArray(value.results)) throw new Error("Página inválida.");
  const count = integer(value, "count");
  const next = nullableText(value, "next");
  const previous = nullableText(value, "previous");
  return { count: count as number, next, previous, results: value.results.map(parseItem) };
}
