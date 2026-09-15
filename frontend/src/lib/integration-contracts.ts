export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

type QueryValue = string | number | boolean | null | undefined;

export function buildPaginatedPath(
  path: string,
  params: Record<string, QueryValue>,
  page: number,
): string {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }

  if (page > 1) query.set("page", String(page));
  const queryString = query.toString();
  return queryString ? `${path}?${queryString}` : path;
}

export function paginationControls<T>(response: PaginatedResponse<T>) {
  return {
    total: response.count,
    hasNext: response.next !== null,
    hasPrevious: response.previous !== null,
  };
}

export function appendUniqueById<T extends { id: number }>(
  current: T[],
  incoming: T[],
): T[] {
  const items = new Map(current.map((item) => [item.id, item]));
  for (const item of incoming) items.set(item.id, item);
  return Array.from(items.values());
}

export function startPaginatedSearch(search: string) {
  return { search, page: 1 };
}

export type SacramentValue = "" | "true" | "false";

export interface AlpinistaFormValues {
  nome: string;
  email: string;
  telefone: string;
  cpf: string;
  dataNascimento: string;
  endereco: string;
  nomePai: string;
  telefonePai: string;
  nomeMae: string;
  telefoneMae: string;
  restricaoSaude: string;
  medicacao: string;
  conheciaEscalada: string;
  grupo: string;
  status: string;
  is_neurodivergente: boolean;
  tipo_neurodivergente: string;
  batizado: SacramentValue;
  primeira_comunhao: SacramentValue;
  crismado: SacramentValue;
}

type AlpinistaPayload = Record<string, string | boolean | null>;

const NULLABLE_TEXT_FIELDS = [
  "cpf", "endereco", "nomePai", "telefonePai", "nomeMae", "telefoneMae",
  "restricaoSaude", "medicacao", "conheciaEscalada", "grupo",
] as const;
const SACRAMENT_FIELDS = ["batizado", "primeira_comunhao", "crismado"] as const;

function buildAlpinistaPayload(
  values: AlpinistaFormValues,
  mode: "create" | "update",
): AlpinistaPayload {
  if (!values.nome.trim() || !values.email.trim() || !values.telefone.trim()) {
    throw new Error("Nome, e-mail e telefone são obrigatórios.");
  }

  const payload: AlpinistaPayload = {
    nome: values.nome.trim(),
    email: values.email.trim(),
    telefone: values.telefone.trim(),
    is_neurodivergente: values.is_neurodivergente,
  };

  for (const field of NULLABLE_TEXT_FIELDS) {
    const value = values[field].trim();
    if (value) payload[field] = value;
    else if (mode === "update") payload[field] = null;
  }

  if (values.dataNascimento) payload.dataNascimento = values.dataNascimento;
  else if (mode === "update") payload.dataNascimento = null;

  if (values.is_neurodivergente && values.tipo_neurodivergente.trim()) {
    payload.tipo_neurodivergente = values.tipo_neurodivergente.trim();
  } else if (mode === "update") {
    payload.tipo_neurodivergente = null;
  }

  for (const field of SACRAMENT_FIELDS) {
    const value = values[field];
    if (value) payload[field] = value === "true";
    else if (mode === "update") payload[field] = null;
  }

  if (mode === "update") payload.status = values.status;
  return payload;
}

export function buildAlpinistaCreatePayload(values: AlpinistaFormValues) {
  return buildAlpinistaPayload(values, "create");
}

export function buildAlpinistaUpdatePayload(values: AlpinistaFormValues) {
  return buildAlpinistaPayload(values, "update");
}
