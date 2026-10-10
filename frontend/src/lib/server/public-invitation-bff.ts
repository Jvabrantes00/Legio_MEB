import { NextRequest, NextResponse } from "next/server";

import { validateCsrf } from "./csrf";
import { getSiaServerConfig } from "./sia-config";

export const PUBLIC_INVITATION_MAX_BODY_BYTES = 1024;
export const PUBLIC_INVITATION_TIMEOUT_MS = 8_000;

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{43}$/;
const CIVIL_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const ACTIONS = new Set(["validar", "confirmar", "recusar"]);
const RESPONSE_STATES = new Set([
  "pendente",
  "confirmado",
  "recusado",
  "expirado",
  "suspenso",
  "indisponivel",
]);

type JsonObject = Record<string, unknown>;
type InvitationPayload = JsonObject & {
  token: string;
  data_nascimento: string;
  acao: string;
};

function isObject(value: unknown): value is JsonObject {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function responseHeaders(): Headers {
  return new Headers({
    "Cache-Control": "private, no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
  });
}

function jsonResponse(body: unknown, status: number, headers = responseHeaders()) {
  return NextResponse.json(body, { status, headers });
}

function invalidInvitation() {
  return jsonResponse({
    detail: "Não foi possível validar este convite. Confira os dados ou procure a equipe de Fichas.",
  }, 404);
}

function temporaryFailure() {
  return jsonResponse({ detail: "Serviço temporariamente indisponível." }, 502);
}

function hasAllowedShape(value: unknown): value is InvitationPayload {
  if (!isObject(value)) return false;
  const keys = Object.keys(value);
  return keys.length === 3
    && keys.every((key) => ["token", "data_nascimento", "acao"].includes(key))
    && typeof value.token === "string"
    && typeof value.data_nascimento === "string"
    && typeof value.acao === "string"
    && ACTIONS.has(value.acao);
}

async function readPayload(request: NextRequest): Promise<
  { payload: JsonObject } | { response: NextResponse }
> {
  const contentType = request.headers.get("content-type")
    ?.split(";", 1)[0]
    .trim()
    .toLowerCase();
  if (contentType !== "application/json") {
    return { response: jsonResponse({ detail: "O corpo deve usar application/json." }, 415) };
  }
  const declaredLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(declaredLength) && declaredLength > PUBLIC_INVITATION_MAX_BODY_BYTES) {
    return { response: jsonResponse({ detail: "Corpo da requisição muito grande." }, 413) };
  }
  const bytes = await request.arrayBuffer();
  if (bytes.byteLength > PUBLIC_INVITATION_MAX_BODY_BYTES) {
    return { response: jsonResponse({ detail: "Corpo da requisição muito grande." }, 413) };
  }
  let value: unknown;
  try {
    value = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return { response: jsonResponse({ detail: "JSON inválido." }, 400) };
  }
  if (!hasAllowedShape(value)) {
    return { response: jsonResponse({ detail: "Payload público inválido." }, 400) };
  }
  if (
    !TOKEN_PATTERN.test(value.token)
    || !CIVIL_DATE_PATTERN.test(value.data_nascimento)
  ) return { response: invalidInvitation() };
  return { payload: value };
}

function minimalInvitation(value: unknown): JsonObject | null {
  if (!isObject(value)) return null;
  const dates = value.datas_encontro;
  if (
    typeof value.estado !== "string"
    || !RESPONSE_STATES.has(value.estado)
    || typeof value.titulo_encontro !== "string"
    || !Array.isArray(dates)
    || !dates.every((item) => typeof item === "string" && CIVIL_DATE_PATTERN.test(item))
    || typeof value.prazo_resposta !== "string"
    || value.finalidade !== "participar"
    || typeof value.pode_responder !== "boolean"
    || typeof value.mensagem !== "string"
  ) {
    return null;
  }
  return {
    estado: value.estado,
    titulo_encontro: value.titulo_encontro,
    datas_encontro: dates,
    prazo_resposta: value.prazo_resposta,
    finalidade: "participar",
    pode_responder: value.pode_responder,
    mensagem: value.mensagem,
  };
}

async function readUpstreamJson(response: Response): Promise<unknown> {
  if (!response.headers.get("content-type")?.includes("application/json")) return null;
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function proxyPublicInvitation(request: NextRequest): Promise<NextResponse> {
  if (request.method.toUpperCase() !== "POST") {
    return jsonResponse({ detail: "Método não permitido." }, 405);
  }
  if (request.nextUrl.search) {
    return jsonResponse({ detail: "Parâmetros não permitidos." }, 400);
  }
  const csrfFailure = validateCsrf(request);
  if (csrfFailure) return csrfFailure;
  const parsed = await readPayload(request);
  if ("response" in parsed) return parsed.response;

  const { backendOrigin } = getSiaServerConfig();
  const target = new URL("/api/public/convites/", backendOrigin);
  try {
    const upstream = await fetch(target, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(parsed.payload),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(PUBLIC_INVITATION_TIMEOUT_MS),
    });
    if (upstream.status === 404) return invalidInvitation();
    if (upstream.status === 429) {
      const headers = responseHeaders();
      const retryAfter = upstream.headers.get("retry-after");
      if (retryAfter && /^\d+$/.test(retryAfter)) headers.set("Retry-After", retryAfter);
      return jsonResponse({ detail: "Muitas tentativas. Tente novamente mais tarde." }, 429, headers);
    }
    if (upstream.status !== 200) return temporaryFailure();
    const convite = minimalInvitation(await readUpstreamJson(upstream));
    return convite ? jsonResponse(convite, 200) : temporaryFailure();
  } catch {
    return temporaryFailure();
  }
}
