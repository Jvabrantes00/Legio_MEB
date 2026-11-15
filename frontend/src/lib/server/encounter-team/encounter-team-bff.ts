export function isAllowedEncounterTeamRequest(method: string, path: readonly string[], searchParams = new URLSearchParams()): boolean {
  return method === "GET" && path.length === 1 && path[0] === "equipes-encontros"
    && searchParams.size === 1 && /^[1-9]\d*$/.test(searchParams.get("encontro") ?? "");
}
