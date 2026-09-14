const CSRF_COOKIE = "sia_csrf";
const CSRF_HEADER = "X-CSRF-Token";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  for (const item of document.cookie.split(";")) {
    const cookie = item.trim();
    if (cookie.startsWith(prefix)) return decodeURIComponent(cookie.slice(prefix.length));
  }
  return null;
}

export async function ensureCsrfToken(): Promise<string> {
  let token = readCookie(CSRF_COOKIE);
  if (token) return token;

  const response = await fetch("/api/auth/csrf", {
    method: "GET",
    cache: "no-store",
    credentials: "same-origin",
  });
  if (!response.ok) throw new Error("Não foi possível iniciar a proteção CSRF.");
  token = readCookie(CSRF_COOKIE);
  if (!token) throw new Error("O navegador não armazenou o token CSRF.");
  return token;
}

function assertRelativeSiaPath(path: string) {
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("://")) {
    throw new Error("siaFetch aceita somente caminhos relativos da API.");
  }
  const pathname = path.split("?", 1)[0];
  for (const rawPart of pathname.split("/")) {
    if (!rawPart) continue;
    let part: string;
    try {
      part = decodeURIComponent(rawPart);
    } catch {
      throw new Error("Caminho de API inválido.");
    }
    if (part === "." || part === ".." || /[\\/\0]/.test(part)) {
      throw new Error("Caminho de API inválido.");
    }
  }
}

export async function siaFetch(path: string, init: RequestInit = {}): Promise<Response> {
  assertRelativeSiaPath(path);
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.delete("Authorization");
  headers.delete("Cookie");

  if (MUTATING_METHODS.has(method)) {
    headers.set(CSRF_HEADER, await ensureCsrfToken());
  }

  return fetch(`/api/sia${path}`, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
    cache: init.cache ?? "no-store",
  });
}

export async function authMutation(path: "/api/auth/login" | "/api/auth/logout", init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set(CSRF_HEADER, await ensureCsrfToken());
  return fetch(path, {
    ...init,
    method: "POST",
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
}
