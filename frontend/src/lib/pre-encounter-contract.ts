export type PreEncounterContextCapabilities = {
  consultar_operacao: boolean;
  registrar_checkin: boolean;
  aumentar_capacidade: boolean;
};

export type PreEncounterItemCapabilities = {
  regularizar: boolean;
  registrar_pagamento: boolean;
  consultar_cuidados: boolean;
  conferir_cuidados: boolean;
  visualizar_foto: boolean;
  alterar_foto: boolean;
  decidir_vaga: boolean;
};

export type PreEncounterRegistrationLookupItem = {
  inscricao_id: number;
  identificador: string;
  nome: string;
  data_nascimento: string | null;
  cpf_mascarado: string | null;
  telefone_mascarado: string | null;
};

export type PreEncounterPersonLookupItem = {
  pessoa_id: number;
  nome: string;
  data_nascimento: string | null;
  cpf_mascarado: string | null;
  telefone_mascarado: string | null;
};

type PaginatedLookup<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type PaginatedPreEncounterRegistrationLookup =
  PaginatedLookup<PreEncounterRegistrationLookupItem>;
export type PaginatedPreEncounterPersonLookup =
  PaginatedLookup<PreEncounterPersonLookupItem>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireBoolean(record: Record<string, unknown>, key: string): boolean {
  const value = record[key];
  if (typeof value !== "boolean") {
    throw new Error(`Capability inválida: ${key}.`);
  }
  return value;
}

function requireNumber(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    throw new Error(`Identificador inválido: ${key}.`);
  }
  return value;
}

function requireString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string") throw new Error(`Campo inválido: ${key}.`);
  return value;
}

function nullableString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  if (value === null) return null;
  if (typeof value === "string") return value;
  throw new Error(`Campo inválido: ${key}.`);
}

function parsePage<T>(value: unknown, parseItem: (item: unknown) => T): PaginatedLookup<T> {
  if (!isRecord(value) || !Array.isArray(value.results)) {
    throw new Error("Lookup paginado inválido.");
  }
  const count = value.count;
  if (typeof count !== "number" || !Number.isInteger(count) || count < 0) {
    throw new Error("Contagem de lookup inválida.");
  }
  const next = nullableString(value, "next");
  const previous = nullableString(value, "previous");
  return { count, next, previous, results: value.results.map(parseItem) };
}

export function parsePreEncounterContextCapabilities(
  value: unknown,
): PreEncounterContextCapabilities {
  if (!isRecord(value)) throw new Error("Capabilities de Pré-Encontro inválidas.");
  return {
    consultar_operacao: requireBoolean(value, "consultar_operacao"),
    registrar_checkin: requireBoolean(value, "registrar_checkin"),
    aumentar_capacidade: requireBoolean(value, "aumentar_capacidade"),
  };
}

export function parsePreEncounterItemCapabilities(
  value: unknown,
): PreEncounterItemCapabilities {
  if (!isRecord(value)) throw new Error("Capabilities do atendimento inválidas.");
  return {
    regularizar: requireBoolean(value, "regularizar"),
    registrar_pagamento: requireBoolean(value, "registrar_pagamento"),
    consultar_cuidados: requireBoolean(value, "consultar_cuidados"),
    conferir_cuidados: requireBoolean(value, "conferir_cuidados"),
    visualizar_foto: requireBoolean(value, "visualizar_foto"),
    alterar_foto: requireBoolean(value, "alterar_foto"),
    decidir_vaga: requireBoolean(value, "decidir_vaga"),
  };
}

function parseRegistrationLookupItem(value: unknown): PreEncounterRegistrationLookupItem {
  if (!isRecord(value)) throw new Error("Inscrição de lookup inválida.");
  return {
    inscricao_id: requireNumber(value, "inscricao_id"),
    identificador: requireString(value, "identificador"),
    nome: requireString(value, "nome"),
    data_nascimento: nullableString(value, "data_nascimento"),
    cpf_mascarado: nullableString(value, "cpf_mascarado"),
    telefone_mascarado: nullableString(value, "telefone_mascarado"),
  };
}

function parsePersonLookupItem(value: unknown): PreEncounterPersonLookupItem {
  if (!isRecord(value)) throw new Error("Pessoa de lookup inválida.");
  return {
    pessoa_id: requireNumber(value, "pessoa_id"),
    nome: requireString(value, "nome"),
    data_nascimento: nullableString(value, "data_nascimento"),
    cpf_mascarado: nullableString(value, "cpf_mascarado"),
    telefone_mascarado: nullableString(value, "telefone_mascarado"),
  };
}

export function parsePreEncounterRegistrationLookup(
  value: unknown,
): PaginatedPreEncounterRegistrationLookup {
  return parsePage(value, parseRegistrationLookupItem);
}

export function parsePreEncounterPersonLookup(
  value: unknown,
): PaginatedPreEncounterPersonLookup {
  return parsePage(value, parsePersonLookupItem);
}
