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

export type AlpinistaFormValues = Record<string, string | boolean> & {
  is_neurodivergente: boolean;
};

export function buildAlpinistaFormEntries(
  values: AlpinistaFormValues,
  mode: "create" | "update",
): Array<[string, string]> {
  const entries: Array<[string, string]> = [];

  for (const [key, value] of Object.entries(values)) {
    if (mode === "create" && key === "status") continue;
    if (key === "tipo_neurodivergente" && !values.is_neurodivergente) continue;
    if (value === "" || value === null) continue;
    entries.push([key, String(value)]);
  }

  return entries;
}
