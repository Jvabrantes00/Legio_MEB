const LOCAL_HTTP_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

export interface SiaServerConfig {
  backendOrigin: string;
  appOrigin: string;
  secureCookies: boolean;
}

function requiredOrigin(name: "SIA_BACKEND_URL" | "SIA_APP_ORIGIN"): URL {
  const value = process.env[name];
  if (!value) {
    throw new Error(`A variável server-side obrigatória ${name} não foi configurada.`);
  }

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${name} deve ser uma origem HTTP(S) válida.`);
  }

  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    throw new Error(`${name} deve conter somente uma origem HTTP(S), sem caminho ou credenciais.`);
  }
  return url;
}

export function getSiaServerConfig(): SiaServerConfig {
  const backend = requiredOrigin("SIA_BACKEND_URL");
  const app = requiredOrigin("SIA_APP_ORIGIN");

  if (app.protocol === "http:" && !LOCAL_HTTP_HOSTS.has(app.hostname)) {
    throw new Error("SIA_APP_ORIGIN só pode usar HTTP em desenvolvimento local explícito.");
  }

  return {
    backendOrigin: backend.origin,
    appOrigin: app.origin,
    secureCookies: app.protocol === "https:",
  };
}

export function backendApiUrl(path: readonly string[], search = ""): URL {
  const { backendOrigin } = getSiaServerConfig();
  const encodedPath = path.map((part) => encodeURIComponent(part)).join("/");
  const url = new URL(`/api/${encodedPath}/`, backendOrigin);
  url.search = search;
  return url;
}
