import { NextRequest, NextResponse } from "next/server";

import { applyAuthenticationResult, authenticatedDjangoRequest } from "./django-auth";
import { validateCsrf } from "./csrf";
import { backendApiUrl, getSiaServerConfig } from "./sia-config";

const ALLOWED_RESOURCES = new Set([
  "alpinistas",
  "encontros",
  "eventos",
  "funcoes",
  "participacoes-encontros",
  "participacoes-eventos",
  "logs",
  "dashboard-stats",
  "materiais",
  "entregas-materiais",
]);
const BLOCKED_QUERY_KEYS = new Set(["url", "target", "host"]);
const BODY_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const MEDIA_PATHS = [
  /^\/api\/alpinistas\/\d+\/foto-arquivo\/$/,
  /^\/api\/encontros\/\d+\/fotos\/\d+\/arquivo\/$/,
];

function invalidPathPart(part: string): boolean {
  return !part || part === "." || part === ".." || /[\\/\0]/.test(part);
}

export function validateProxyPath(path: readonly string[], searchParams: URLSearchParams) {
  if (!path.length || path.some(invalidPathPart) || !ALLOWED_RESOURCES.has(path[0])) {
    throw new Error("Caminho de API não permitido.");
  }
  for (const key of searchParams.keys()) {
    if (BLOCKED_QUERY_KEYS.has(key.toLowerCase())) {
      throw new Error("Parâmetro de destino não permitido.");
    }
  }
}

function forwardedHeaders(request: NextRequest, access: string): Headers {
  const headers = new Headers({ Authorization: `Bearer ${access}` });
  const accept = request.headers.get("accept");
  const contentType = request.headers.get("content-type");
  if (accept) headers.set("Accept", accept);
  if (contentType) headers.set("Content-Type", contentType);
  return headers;
}

function isProtectedMediaPath(pathname: string): boolean {
  return MEDIA_PATHS.some((pattern) => pattern.test(pathname));
}

export function toBffMediaReference(value: string): string | null | undefined {
  const config = getSiaServerConfig();
  let url: URL;
  try {
    url = new URL(value, config.backendOrigin);
  } catch {
    return undefined;
  }
  if (!isProtectedMediaPath(url.pathname)) return undefined;
  if (url.origin !== config.backendOrigin) return null;
  return `/api/sia${url.pathname.slice(4)}${url.search}`;
}

export function toBffApiReference(value: string): string | undefined {
  const config = getSiaServerConfig();
  let url: URL;
  try {
    url = new URL(value, config.backendOrigin);
  } catch {
    return undefined;
  }
  if (url.origin !== config.backendOrigin || !url.pathname.startsWith("/api/")) {
    return undefined;
  }

  const relativePath = url.pathname.slice(5);
  let parts: string[];
  try {
    parts = relativePath.split("/").filter(Boolean).map(decodeURIComponent);
    validateProxyPath(parts, url.searchParams);
  } catch {
    return undefined;
  }
  return `/${relativePath}${url.search}`;
}

function rewriteBackendReferences(value: unknown): unknown {
  if (typeof value === "string") {
    const media = toBffMediaReference(value);
    if (media !== undefined) return media;
    return toBffApiReference(value) ?? value;
  }
  if (Array.isArray(value)) return value.map(rewriteBackendReferences);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, rewriteBackendReferences(item)]),
    );
  }
  return value;
}

async function createClientResponse(upstream: Response): Promise<NextResponse> {
  const headers = new Headers({ "Cache-Control": "private, no-store" });
  const contentType = upstream.headers.get("content-type");
  const contentDisposition = upstream.headers.get("content-disposition");
  if (contentType) headers.set("Content-Type", contentType);
  if (contentDisposition) headers.set("Content-Disposition", contentDisposition);

  if (upstream.status === 204 || !upstream.body) {
    return new NextResponse(null, { status: upstream.status, headers });
  }

  if (contentType?.includes("application/json")) {
    const text = await upstream.text();
    try {
      const body = JSON.stringify(rewriteBackendReferences(JSON.parse(text)));
      return new NextResponse(body, { status: upstream.status, headers });
    } catch {
      return new NextResponse(text, { status: upstream.status, headers });
    }
  }

  const contentLength = upstream.headers.get("content-length");
  if (contentLength) headers.set("Content-Length", contentLength);
  return new NextResponse(upstream.body, { status: upstream.status, headers });
}

export async function proxySiaRequest(
  request: NextRequest,
  path: readonly string[],
): Promise<NextResponse> {
  const csrfFailure = validateCsrf(request);
  if (csrfFailure) return csrfFailure;

  try {
    validateProxyPath(path, request.nextUrl.searchParams);
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Caminho inválido." },
      { status: 400, headers: { "Cache-Control": "private, no-store" } },
    );
  }

  const target = backendApiUrl(path, request.nextUrl.search);
  const canHaveBody = BODY_METHODS.has(request.method);
  const requestBody = canHaveBody ? await request.arrayBuffer() : undefined;

  try {
    const result = await authenticatedDjangoRequest(request, (access) => {
      const init: RequestInit = {
        method: request.method,
        headers: forwardedHeaders(request, access),
        body: requestBody?.slice(0),
        cache: "no-store",
        redirect: "manual",
      };
      return fetch(target, init);
    });
    const response = await createClientResponse(result.upstream);
    applyAuthenticationResult(response, result);
    return response;
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível contatar a API do SIA." },
      { status: 502, headers: { "Cache-Control": "private, no-store" } },
    );
  }
}
