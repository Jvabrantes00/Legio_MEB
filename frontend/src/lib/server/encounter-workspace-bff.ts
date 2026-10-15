const POSITIVE_INTEGER = /^[1-9]\d*$/;
const LIST_QUERY_KEYS = new Set(["page", "search", "situacao", "origem"]);

function isId(value: string | undefined): boolean {
  return Boolean(value && POSITIVE_INTEGER.test(value));
}

export function isAllowedEncounterWorkspaceRequest(
  method: string,
  path: readonly string[],
  searchParams = new URLSearchParams(),
): boolean {
  if (
    path.length < 3
    || path[0] !== "encontros"
    || !isId(path[1])
    || path[2] !== "workspace"
  ) return false;

  const tail = path.slice(3);
  const isSummary = tail.length === 0;
  const isCapabilities = tail.length === 1 && tail[0] === "capabilities";
  const isCandidates = tail.length === 1 && tail[0] === "encontristas";
  const isRegistrationConfig = tail.length === 2
    && tail[0] === "inscricoes"
    && tail[1] === "configuracao";
  if (!isSummary && !isCapabilities && !isCandidates && !isRegistrationConfig) return false;
  if (isRegistrationConfig && !["GET", "POST", "PATCH"].includes(method)) return false;
  if (!isRegistrationConfig && method !== "GET") return false;
  if (!isCandidates && searchParams.size > 0) return false;
  if (isCandidates) {
    for (const key of searchParams.keys()) {
      if (!LIST_QUERY_KEYS.has(key)) return false;
    }
    const page = searchParams.get("page");
    if (page !== null && !POSITIVE_INTEGER.test(page)) return false;
  }
  return true;
}
