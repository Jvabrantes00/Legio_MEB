import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import * as publicRoute from "../../app/api/public/encontros/[publicId]/inscricao/route";
import { config as pageGuardConfig } from "../../proxy";
import {
  PUBLIC_REGISTRATION_MAX_BODY_BYTES,
  PUBLIC_REGISTRATION_TIMEOUT_MS,
  proxyPublicRegistration,
} from "./public-registration-bff";

const APP_ORIGIN = "http://localhost:3000";
const BACKEND_ORIGIN = "http://localhost:8000";
const PUBLIC_ID = "123e4567-e89b-42d3-a456-426614174000";
const PUBLIC_PATH = `/api/public/encontros/${PUBLIC_ID}/inscricao/`;
const BACKEND_PATH = `${BACKEND_ORIGIN}/api/public/encontros/${PUBLIC_ID}/inscricao/`;

function request(path: string, init: RequestInit = {}) {
  return new NextRequest(`${APP_ORIGIN}${path}`, init);
}

function mutationRequest(
  init: RequestInit = {},
  token = "csrf-publico",
) {
  const headers = new Headers(init.headers);
  headers.set("origin", APP_ORIGIN);
  headers.set("x-csrf-token", token);
  headers.set(
    "cookie",
    `sia_csrf=${token}; sia_access=jwt-nao-encaminhar; sia_refresh=refresh-nao-encaminhar`,
  );
  headers.set("content-type", "application/json");
  return request(PUBLIC_PATH, { ...init, method: "POST", headers });
}

function payload(overrides: Record<string, unknown> = {}) {
  return {
    dados_declarados: {
      nome_completo: "Pessoa Sensível",
      data_nascimento: "2000-01-01",
      email: "pessoa@example.test",
      cep: "70000-000",
      logradouro: "Rua Sensível",
      numero: "10",
      bairro: "Bairro",
      cidade: "Brasília",
      uf: "DF",
      como_conheceu: "indicacao",
    },
    ...overrides,
  };
}

function context(publicId = PUBLIC_ID) {
  return { params: Promise.resolve({ publicId }) };
}

beforeEach(() => {
  process.env.SIA_BACKEND_URL = BACKEND_ORIGIN;
  process.env.SIA_APP_ORIGIN = APP_ORIGIN;
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("BFF público de inscrição", () => {
  it("faz GET somente no endpoint público fixo e minimiza a resposta", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({
        titulo: "Escalada 2030",
        tipo: "Escalada",
        inscricoes_abrem_em: "2030-01-01T08:00:00-03:00",
        inscricoes_encerram_em: "2030-02-01T08:00:00-03:00",
        inscricoes_abertas: true,
        encontro_id: 17,
        pessoa: { cpf: "52998224725" },
      }),
    );

    const response = await publicRoute.GET(
      request(PUBLIC_PATH),
      context(),
    );
    const [target, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);

    expect(String(target)).toBe(BACKEND_PATH);
    expect(init?.method).toBe("GET");
    expect(init?.cache).toBe("no-store");
    expect(init?.redirect).toBe("error");
    expect(init?.signal).toBeInstanceOf(AbortSignal);
    expect(headers.get("accept")).toBe("application/json");
    expect(headers.has("authorization")).toBe(false);
    expect(headers.has("cookie")).toBe(false);
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(await response.json()).toEqual({
      titulo: "Escalada 2030",
      tipo: "Escalada",
      inscricoes_abrem_em: "2030-01-01T08:00:00-03:00",
      inscricoes_encerram_em: "2030-02-01T08:00:00-03:00",
      inscricoes_abertas: true,
    });
  });

  it("faz POST com contrato allowlist e nunca encaminha JWT, cookies ou Authorization", async () => {
    let forwardedBody: unknown;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementationOnce(
      async (_target, init) => {
        forwardedBody = await new Response(init?.body).json();
        return Response.json(
          { mensagem: "Inscrição enviada com sucesso.", jwt: "nao-expor" },
          {
            status: 201,
            headers: { "set-cookie": "sia_access=jwt-do-backend" },
          },
        );
      },
    );
    const incoming = mutationRequest({
      headers: { authorization: "Bearer atacante" },
      body: JSON.stringify(payload()),
    });

    const response = await publicRoute.POST(incoming, context());
    const [target, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);

    expect(String(target)).toBe(BACKEND_PATH);
    expect(forwardedBody).toEqual(payload());
    expect(headers.get("content-type")).toBe("application/json");
    expect(headers.has("authorization")).toBe(false);
    expect(headers.has("cookie")).toBe(false);
    expect(headers.has("origin")).toBe(false);
    expect(headers.has("x-csrf-token")).toBe(false);
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({
      mensagem: "Inscrição enviada com sucesso.",
    });
    expect(response.headers.has("set-cookie")).toBe(false);
  });

  it.each([
    ["Origin ausente", { "x-csrf-token": "csrf", cookie: "sia_csrf=csrf" }],
    ["Origin incorreta", { origin: "https://evil.example", "x-csrf-token": "csrf", cookie: "sia_csrf=csrf" }],
    ["header CSRF ausente", { origin: APP_ORIGIN, cookie: "sia_csrf=csrf" }],
    ["cookie CSRF ausente", { origin: APP_ORIGIN, "x-csrf-token": "csrf" }],
    ["tokens diferentes", { origin: APP_ORIGIN, "x-csrf-token": "um", cookie: "sia_csrf=outro" }],
  ])("recusa escrita com %s", async (_name, headers) => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const response = await proxyPublicRegistration(
      request(PUBLIC_PATH, {
        method: "POST",
        headers: { ...headers, "content-type": "application/json" },
        body: JSON.stringify(payload()),
      }),
      PUBLIC_ID,
    );

    expect(response.status).toBe(403);
    expect(await response.json()).toEqual({
      detail: "Requisição recusada pela proteção CSRF.",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("permite GET sem CSRF, mas mantém no-store", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({
        titulo: "ESPPA",
        tipo: "Esppa",
        inscricoes_abrem_em: "2030-01-01T08:00:00-03:00",
        inscricoes_encerram_em: "2030-02-01T08:00:00-03:00",
        inscricoes_abertas: false,
      }),
    );

    const response = await proxyPublicRegistration(
      request(PUBLIC_PATH),
      PUBLIC_ID,
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });

  it("rejeita UUID inválido, travessia, query de destino e campos internos", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const invalidIds = ["17", "../admin", `${PUBLIC_ID}/cancelar`];

    for (const publicId of invalidIds) {
      const response = await proxyPublicRegistration(
        request(PUBLIC_PATH),
        publicId,
      );
      expect(response.status).toBe(404);
    }

    const queryResponse = await proxyPublicRegistration(
      request(`${PUBLIC_PATH}?target=https://evil.example`),
      PUBLIC_ID,
    );
    expect(queryResponse.status).toBe(400);

    const internalFieldResponse = await proxyPublicRegistration(
      mutationRequest({
        body: JSON.stringify(payload({ pessoa_id: 99 })),
      }),
      PUBLIC_ID,
    );
    expect(internalFieldResponse.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("limita o corpo real e não confia somente em Content-Length", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const oversized = payload({
      dados_cuidado: {
        observacoes: "x".repeat(PUBLIC_REGISTRATION_MAX_BODY_BYTES),
      },
    });
    const response = await proxyPublicRegistration(
      mutationRequest({ body: JSON.stringify(oversized) }),
      PUBLIC_ID,
    );

    expect(response.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("normaliza 404, propaga throttle e não revela host ou erro interno", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json(
        { detail: `No model at ${BACKEND_ORIGIN}/admin` },
        { status: 404 },
      ))
      .mockResolvedValueOnce(Response.json(
        { detail: "Throttle internals" },
        { status: 429, headers: { "retry-after": "37" } },
      ))
      .mockResolvedValueOnce(Response.json(
        { stack: `SQL failure at ${BACKEND_ORIGIN}` },
        { status: 500 },
      ));

    const missing = await proxyPublicRegistration(
      request(PUBLIC_PATH),
      PUBLIC_ID,
    );
    const throttled = await proxyPublicRegistration(
      request(PUBLIC_PATH),
      PUBLIC_ID,
    );
    const failed = await proxyPublicRegistration(
      request(PUBLIC_PATH),
      PUBLIC_ID,
    );

    expect(missing.status).toBe(404);
    expect(await missing.json()).toEqual({
      detail: "Recurso público não encontrado.",
    });
    expect(throttled.status).toBe(429);
    expect(throttled.headers.get("retry-after")).toBe("37");
    expect(failed.status).toBe(502);
    const bodies = JSON.stringify([
      await throttled.json(),
      await failed.json(),
    ]);
    expect(bodies).not.toContain(BACKEND_ORIGIN);
    expect(bodies).not.toContain("SQL");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("converte indisponibilidade e contrato upstream inválido em erro temporário", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Error(`Falha em ${BACKEND_ORIGIN}`))
      .mockResolvedValueOnce(Response.json({ encontro_id: 17 }));

    const unavailable = await proxyPublicRegistration(
      request(PUBLIC_PATH),
      PUBLIC_ID,
    );
    const invalidContract = await proxyPublicRegistration(
      request(PUBLIC_PATH),
      PUBLIC_ID,
    );

    expect(unavailable.status).toBe(502);
    expect(invalidContract.status).toBe(502);
    expect(await unavailable.json()).toEqual({
      detail: "Serviço temporariamente indisponível.",
    });
  });

  it("não registra payload sensível nem detalhes da falha", async () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => undefined);
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
      new Error("Pessoa Sensível pessoa@example.test Rua Sensível"),
    );

    const response = await proxyPublicRegistration(
      mutationRequest({ body: JSON.stringify(payload()) }),
      PUBLIC_ID,
    );

    expect(response.status).toBe(502);
    expect(log).not.toHaveBeenCalled();
    expect(warn).not.toHaveBeenCalled();
    expect(error).not.toHaveBeenCalled();
  });

  it("usa timeout e não oferece métodos de edição ou cancelamento", async () => {
    expect(PUBLIC_REGISTRATION_TIMEOUT_MS).toBe(8_000);
    expect(Object.keys(publicRoute).sort()).toEqual(["GET", "POST"]);
    expect(pageGuardConfig.matcher.every((path) => !path.startsWith("/api/")))
      .toBe(true);
  });
});
