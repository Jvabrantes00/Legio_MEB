const positive = (value: string | null) => value !== null && /^[1-9]\d*$/.test(value);

export function isAllowedEncounterTeamRequest(method: string, path: readonly string[], query = new URLSearchParams()): boolean {
  const keys = [...query.keys()];
  if (new Set(keys).size !== keys.length) return false;
  if (path.length === 1 && path[0] === "convites-encontros") {
    if (method === "POST") return keys.length === 0;
    return method === "GET" && keys.every((key) => ["encontro", "finalidade", "page"].includes(key))
      && positive(query.get("encontro")) && query.get("finalidade") === "trabalhar"
      && (!query.has("page") || positive(query.get("page")));
  }
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
