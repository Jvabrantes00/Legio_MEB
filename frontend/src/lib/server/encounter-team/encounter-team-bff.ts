const positive = (value: string | null) => value !== null && /^[1-9]\d*$/.test(value);

export function isAllowedEncounterTeamRequest(method: string, path: readonly string[], query = new URLSearchParams()): boolean {
  const keys = [...query.keys()];
  if (new Set(keys).size !== keys.length) return false;
  if (path.length === 1 && path[0] === "convites-encontros") {
    if (method === "POST") return keys.length === 0;
    return method === "GET" && keys.every((key) => ["encontro", "finalidade", "page", "status"].includes(key))
      && positive(query.get("encontro")) && query.get("finalidade") === "trabalhar"
      && (!query.has("status") || ["convidado", "confirmado", "recusado", "sem_resposta"].includes(query.get("status") ?? ""))
      && (!query.has("page") || positive(query.get("page")));
  }
  if (path.length === 3 && path[0] === "convites-encontros" && positive(path[1]) && path[2] === "responder-trabalho") return method === "POST" && keys.length === 0;
  if (path.length === 1 && path[0] === "trabalhos-encontros") return method === "POST" && keys.length === 0;
  if (path.length === 3 && path[0] === "trabalhos-encontros" && positive(path[1]) && ["alocar", "realocar", "desalocar"].includes(path[2])) return method === "POST" && keys.length === 0;
  if (path.length === 3 && path[0] === "encontros" && positive(path[1]) && !keys.length) {
    return (path[2] === "modelo-equipes" && ["GET", "POST"].includes(method))
      || (path[2] === "preparar-equipes" && method === "POST");
  }
  if (path.length === 2 && path[0] === "alpinistas" && path[1] === "seletor-trabalho" && method === "GET") {
    return keys.every((key) => ["search", "page", "ordering"].includes(key))
      && (!query.has("page") || positive(query.get("page")))
      && (!query.has("ordering") || ["nome", "-nome"].includes(query.get("ordering") ?? ""));
  }
  return false;
}

export function parseWorkActionBody(value: unknown, action: string): Record<string, number | boolean> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Corpo inválido.");
  const body = value as Record<string, unknown>;
  if (action === "desalocar") {
    if (Object.keys(body).length) throw new Error("Corpo inválido.");
    return {};
  }
  if (!["alocar", "realocar"].includes(action) || Object.keys(body).some((key) => !["role_equipe_id", "confirmar_avisos"].includes(key)) || !Number.isSafeInteger(body.role_equipe_id) || (body.role_equipe_id as number) <= 0 || ("confirmar_avisos" in body && typeof body.confirmar_avisos !== "boolean")) throw new Error("Corpo inválido.");
  return { role_equipe_id: body.role_equipe_id as number, ...("confirmar_avisos" in body ? { confirmar_avisos: body.confirmar_avisos as boolean } : {}) };
}

export function parseStartWorkBody(value: unknown): { convite_id: number; confirmar_avisos?: boolean } {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Corpo inválido.");
  const body = value as Record<string, unknown>;
  if (Object.keys(body).some((key) => !["convite_id", "confirmar_avisos"].includes(key)) || !Number.isSafeInteger(body.convite_id) || (body.convite_id as number) <= 0 || ("confirmar_avisos" in body && typeof body.confirmar_avisos !== "boolean")) throw new Error("Corpo inválido.");
  return { convite_id: body.convite_id as number, ...("confirmar_avisos" in body ? { confirmar_avisos: body.confirmar_avisos as boolean } : {}) };
}
