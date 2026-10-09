import { NextRequest, NextResponse } from "next/server";

import { validateCsrf } from "./csrf";
import { getSiaServerConfig } from "./sia-config";

export const PUBLIC_REGISTRATION_MAX_BODY_BYTES = 64 * 1024;
export const PUBLIC_REGISTRATION_TIMEOUT_MS = 8_000;

const PUBLIC_ID_PATTERN = (
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
);
const BODY_METHODS = new Set(["POST"]);
const TOP_LEVEL_FIELDS = new Set([
  "dados_declarados",
  "responsavel",
  "dados_cuidado",
  "dados_esppa",
]);
const SECTION_FIELDS: Record<string, ReadonlySet<string>> = {
  dados_declarados: new Set([
    "nome_completo",
    "apelido",
    "data_nascimento",
    "cpf",
    "email",
    "telefone_whatsapp",
    "cep",
    "logradouro",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "uf",
    "como_conheceu",
    "como_conheceu_outro",
    "batismo",
    "primeira_comunhao",
    "crisma",
  ]),
  responsavel: new Set([
    "nome_completo",
    "cpf",
    "parentesco",
    "telefone_whatsapp",
    "email",
  ]),
  dados_cuidado: new Set([
    "possui_alergias",
    "alergias",
    "possui_restricoes_intolerancias",
    "restricoes_intolerancias",
    "usa_medicamentos",
    "medicamentos",
    "horarios_medicamentos",
    "observacoes_medicamentos",
    "neurodivergencia_apoio",
    "neurodivergencia_condicao",
    "necessidades_apoio",
    "sensibilidades_desconfortos",
    "o_que_ajuda",
    "outras_informacoes",
    "observacoes",
  ]),
  dados_esppa: new Set([
    "estado_civil",
    "nome_conjuge",
    "telefone_conjuge",
    "nome_referencia",
    "relacao_referencia",
    "telefone_referencia",
  ]),
};

type JsonObject = Record<string, unknown>;

function isObject(value: unknown): value is JsonObject {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function hasOnlyFields(value: JsonObject, fields: ReadonlySet<string>): boolean {
  return Object.keys(value).every((field) => fields.has(field));
}

function isAllowedPayload(value: unknown): value is JsonObject {
  if (!isObject(value) || !hasOnlyFields(value, TOP_LEVEL_FIELDS)) return false;
  if (!isObject(value.dados_declarados)) return false;

  return Object.entries(SECTION_FIELDS).every(([section, fields]) => {
    const sectionValue = value[section];
    if (sectionValue === undefined) return section !== "dados_declarados";
    if (sectionValue === null) return section !== "dados_declarados";
    return isObject(sectionValue) && hasOnlyFields(sectionValue, fields);
  });
}

function responseHeaders(): Headers {
  return new Headers({
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
  });
}

function jsonResponse(body: unknown, status: number, headers = responseHeaders()) {
  return NextResponse.json(body, { status, headers });
}

function publicNotFound() {
  return jsonResponse({ detail: "Recurso público não encontrado." }, 404);
}

function temporaryFailure() {
  return jsonResponse(
    { detail: "Serviço temporariamente indisponível." },
    502,
  );
}

function validPublicId(publicId: string): boolean {
  return PUBLIC_ID_PATTERN.test(publicId);
}

function publicBackendUrl(publicId: string): URL {
  const { backendOrigin } = getSiaServerConfig();
  return new URL(
    `/api/public/encontros/${encodeURIComponent(publicId)}/inscricao/`,
    backendOrigin,
  );
}

async function readPublicPayload(request: NextRequest): Promise<
  | { payload: JsonObject }
  | { response: NextResponse }
> {
  const contentType = request.headers.get("content-type")
    ?.split(";", 1)[0]
    .trim()
    .toLowerCase();
  if (contentType !== "application/json") {
    return {
      response: jsonResponse(
        { detail: "O corpo deve usar application/json." },
        415,
      ),
    };
  }

  const declaredLength = Number(request.headers.get("content-length"));
  if (
    Number.isFinite(declaredLength)
    && declaredLength > PUBLIC_REGISTRATION_MAX_BODY_BYTES
  ) {
    return {
      response: jsonResponse({ detail: "Corpo da requisição muito grande." }, 413),
    };
  }

  const bytes = await request.arrayBuffer();
  if (bytes.byteLength > PUBLIC_REGISTRATION_MAX_BODY_BYTES) {
    return {
      response: jsonResponse({ detail: "Corpo da requisição muito grande." }, 413),
    };
  }

  let payload: unknown;
  try {
    payload = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return {
      response: jsonResponse({ detail: "JSON inválido." }, 400),
    };
  }
  if (!isAllowedPayload(payload)) {
    return {
      response: jsonResponse({ detail: "Payload público inválido." }, 400),
    };
  }
  return { payload };
}

function minimalEncounter(body: unknown): JsonObject | null {
  if (!isObject(body)) return null;
  const {
    titulo,
    tipo,
    inscricoes_abrem_em: opensAt,
    inscricoes_encerram_em: closesAt,
    inscricoes_abertas: isOpen,
  } = body;
  if (
    typeof titulo !== "string"
    || !["Escalada", "Esppa"].includes(String(tipo))
    || typeof opensAt !== "string"
    || typeof closesAt !== "string"
    || typeof isOpen !== "boolean"
  ) {
    return null;
  }
  return {
    titulo,
    tipo,
    inscricoes_abrem_em: opensAt,
    inscricoes_encerram_em: closesAt,
    inscricoes_abertas: isOpen,
  };
}

async function upstreamJson(upstream: Response): Promise<unknown> {
  const contentType = upstream.headers.get("content-type");
  if (!contentType?.includes("application/json")) return null;
  try {
    return await upstream.json();
  } catch {
    return null;
  }
}

async function clientResponse(upstream: Response, method: string) {
  if (upstream.status === 404) return publicNotFound();
  if (upstream.status === 429) {
    const headers = responseHeaders();
    const retryAfter = upstream.headers.get("retry-after");
    if (retryAfter && /^\d+$/.test(retryAfter)) {
      headers.set("Retry-After", retryAfter);
    }
    return jsonResponse(
      { detail: "Muitas tentativas. Tente novamente mais tarde." },
      429,
      headers,
    );
  }
  if (method === "GET" && upstream.status === 200) {
    const encontro = minimalEncounter(await upstreamJson(upstream));
    return encontro ? jsonResponse(encontro, 200) : temporaryFailure();
  }
  if (method === "POST" && upstream.status === 201) {
    return jsonResponse({ mensagem: "Inscrição enviada com sucesso." }, 201);
  }
  if (method === "POST" && upstream.status === 400) {
    return jsonResponse({ detail: "Revise os dados informados." }, 400);
  }
  return temporaryFailure();
}

export async function proxyPublicRegistration(
  request: NextRequest,
  publicId: string,
): Promise<NextResponse> {
  const method = request.method.toUpperCase();
  if (!validPublicId(publicId)) return publicNotFound();
  if (request.nextUrl.search) {
    return jsonResponse({ detail: "Parâmetros não permitidos." }, 400);
  }
  if (method !== "GET" && !BODY_METHODS.has(method)) {
    return jsonResponse({ detail: "Método não permitido." }, 405);
  }

  const csrfFailure = validateCsrf(request);
  if (csrfFailure) return csrfFailure;

  let body: BodyInit | undefined;
  if (method === "POST") {
    const parsed = await readPublicPayload(request);
    if ("response" in parsed) return parsed.response;
    body = JSON.stringify(parsed.payload);
  }

  const headers = new Headers({ Accept: "application/json" });
  if (body !== undefined) headers.set("Content-Type", "application/json");

  try {
    const upstream = await fetch(publicBackendUrl(publicId), {
      method,
      headers,
      body,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(PUBLIC_REGISTRATION_TIMEOUT_MS),
    });
    return clientResponse(upstream, method);
  } catch {
    return temporaryFailure();
  }
}
