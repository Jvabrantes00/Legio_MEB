import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

import { POST as login } from "../../app/api/auth/login/route";
import { POST as logout } from "../../app/api/auth/logout/route";
import { GET as csrf } from "../../app/api/auth/csrf/route";
import { GET as me } from "../../app/api/auth/me/route";
import { siaFetch } from "../sia-api";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  setAuthCookies,
} from "./auth-cookies";
import { validateCsrf } from "./csrf";
import {
  proxySiaRequest,
  toBffApiReference,
  toBffMediaReference,
  validateProxyPath,
} from "./sia-proxy";

const APP_ORIGIN = "http://localhost:3000";
const BACKEND_ORIGIN = "http://localhost:8000";
const JWT_ACCESS = "access.payload.signature";
const JWT_REFRESH = "refresh.payload.signature";

function request(
  path: string,
  init: RequestInit = {},
  cookies = `${ACCESS_COOKIE}=${JWT_ACCESS}; ${REFRESH_COOKIE}=${JWT_REFRESH}`,
) {
  const headers = new Headers(init.headers);
  if (cookies) headers.set("cookie", cookies);
  return new NextRequest(`${APP_ORIGIN}${path}`, { ...init, headers });
}

function mutationRequest(path: string, init: RequestInit = {}) {
  const token = "csrf-token";
  const headers = new Headers(init.headers);
  headers.set("origin", APP_ORIGIN);
  headers.set("x-csrf-token", token);
  headers.set("cookie", `sia_csrf=${token}; ${ACCESS_COOKIE}=${JWT_ACCESS}; ${REFRESH_COOKIE}=${JWT_REFRESH}`);
  return new NextRequest(`${APP_ORIGIN}${path}`, { ...init, headers });
}

function setCookies(response: Response): string {
  return response.headers.get("set-cookie") ?? "";
}

beforeEach(() => {
  process.env.SIA_BACKEND_URL = BACKEND_ORIGIN;
  process.env.SIA_APP_ORIGIN = APP_ORIGIN;
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("cookies de autenticação", () => {
  it("define access e refresh como HttpOnly, Lax, sem Domain e com os TTLs esperados", () => {
    const response = NextResponse.json({ ok: true });
    setAuthCookies(response, { access: JWT_ACCESS, refresh: JWT_REFRESH });
    const cookies = setCookies(response);

    expect(cookies).toContain("sia_access=");
    expect(cookies).toContain("sia_refresh=");
    expect(cookies).toContain("HttpOnly");
    expect(cookies).toContain("SameSite=lax");
    expect(cookies).toContain("Max-Age=900");
    expect(cookies).toContain("Max-Age=604800");
    expect(cookies).not.toContain("Domain=");
    expect(cookies).not.toContain("Secure");
  });

  it("ativa Secure quando a origem do app usa HTTPS", () => {
    process.env.SIA_APP_ORIGIN = "https://sia.example.test";
    const response = NextResponse.json({ ok: true });
    setAuthCookies(response, { access: JWT_ACCESS, refresh: JWT_REFRESH });
    expect(setCookies(response)).toContain("Secure");
  });
});

describe("CSRF double-submit e Origin", () => {
  it("aceita token igual e Origin exata", () => {
    const valid = mutationRequest("/api/sia/alpinistas/", { method: "POST" });
    expect(validateCsrf(valid)).toBeNull();
  });

  it.each([
    ["sem header", { origin: APP_ORIGIN, cookie: "sia_csrf=csrf-token" }],
    ["token incorreto", { origin: APP_ORIGIN, cookie: "sia_csrf=outro", "x-csrf-token": "csrf-token" }],
    ["Origin incorreta", { origin: "https://evil.example", cookie: "sia_csrf=csrf-token", "x-csrf-token": "csrf-token" }],
  ])("recusa %s", (_name, headers) => {
    const invalid = request("/api/sia/alpinistas/", { method: "POST", headers }, "");
    expect(validateCsrf(invalid)?.status).toBe(403);
  });

  it("não exige CSRF em GET", () => {
    expect(validateCsrf(request("/api/sia/alpinistas/", { method: "GET" }, ""))).toBeNull();
  });
});

describe("cliente HTTP do browser", () => {
  it("anexa somente o CSRF em mutações e usa o BFF same-origin", async () => {
    vi.stubGlobal("document", { cookie: "sia_csrf=csrf-do-browser" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({ ok: true }),
    );
    await siaFetch("/alpinistas/1/", {
      method: "PATCH",
      headers: { authorization: "Bearer nunca-encaminhar", cookie: "segredo=nao" },
      body: JSON.stringify({ nome: "Teste" }),
    });
    const [target, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(target).toBe("/api/sia/alpinistas/1/");
    expect(headers.get("x-csrf-token")).toBe("csrf-do-browser");
    expect(headers.has("authorization")).toBe(false);
    expect(headers.has("cookie")).toBe(false);
  });

  it("rejeita URL absoluta antes de chamar fetch", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    await expect(siaFetch("https://evil.example/api/alpinistas/"))
      .rejects.toThrow("caminhos relativos");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("login e logout", () => {
  it("inicializa um CSRF legível pelo JavaScript, sem HttpOnly", () => {
    const response = csrf(request("/api/auth/csrf", { method: "GET" }, ""));
    const cookies = setCookies(response);
    expect(response.status).toBe(204);
    expect(cookies).toContain("sia_csrf=");
    expect(cookies).toContain("SameSite=lax");
    expect(cookies).not.toContain("HttpOnly");
  });

  it("valida a sessão, grava cookies HttpOnly e nunca devolve JWT", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json({ access: JWT_ACCESS, refresh: JWT_REFRESH }))
      .mockResolvedValueOnce(Response.json({ id: 7, username: "teste", roles: ["Fichas"], superuser: false }));
    const response = await login(mutationRequest("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ username: "teste", password: "segredo-de-teste" }),
    }));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload).toEqual({ id: 7, username: "teste", roles: ["Fichas"], superuser: false });
    expect(JSON.stringify(payload)).not.toContain(JWT_ACCESS);
    expect(setCookies(response)).toContain("HttpOnly");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("mantém erro de credenciais genérico e não grava sessão", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}, { status: 401 }));
    const response = await login(mutationRequest("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ username: "x", password: "y" }),
    }));
    expect(response.status).toBe(401);
    expect(setCookies(response)).toBe("");
    expect(await response.json()).toEqual({ detail: "Usuário ou senha incorretos." });
  });

  it("logout local expira autenticação, legado e CSRF", async () => {
    const response = logout(mutationRequest("/api/auth/logout", { method: "POST" }));
    const cookies = setCookies(response);
    expect(response.status).toBe(204);
    expect(cookies).toContain("sia_access=");
    expect(cookies).toContain("sia_refresh=");
    expect(cookies).toContain("sia_token=");
    expect(cookies).toContain("sia_csrf=");
    expect(cookies).toContain("Max-Age=0");
  });

  it("/me retorna somente a sessão segura usando autenticação server-side", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({ id: 7, username: "teste", roles: ["Fichas"], superuser: false }),
    );
    const response = await me(request("/api/auth/me"));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ id: 7, username: "teste", roles: ["Fichas"], superuser: false });
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("authorization"))
      .toBe(`Bearer ${JWT_ACCESS}`);
  });
});

describe("proxy controlado", () => {
  it("rejeita recursos, travessia e parâmetros de destino arbitrários", () => {
    expect(() => validateProxyPath(["admin"], new URLSearchParams())).toThrow();
    expect(() => validateProxyPath(["alpinistas", ".."], new URLSearchParams())).toThrow();
    expect(() => validateProxyPath(["alpinistas"], new URLSearchParams("url=https://evil.example"))).toThrow();
  });

  it("fixa o host, preserva query e ignora Authorization do browser", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({ results: [] }, { status: 200 }),
    );
    const incoming = request("/api/sia/alpinistas/?search=Joao&page=2", {
      headers: { authorization: "Bearer atacante" },
    });
    const response = await proxySiaRequest(incoming, ["alpinistas"]);
    const [target, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);

    expect(response.status).toBe(200);
    expect(String(target)).toBe(`${BACKEND_ORIGIN}/api/alpinistas/?search=Joao&page=2`);
    expect(headers.get("authorization")).toBe(`Bearer ${JWT_ACCESS}`);
    expect(headers.get("authorization")).not.toContain("atacante");
    expect(headers.has("cookie")).toBe(false);
  });

  it("preserva JSON e status 201", async () => {
    let body = "";
    vi.spyOn(globalThis, "fetch").mockImplementationOnce(async (_target, init) => {
      body = await new Response(init?.body).text();
      expect(new Headers(init?.headers).get("content-type")).toBe("application/json");
      return Response.json({ id: 1 }, { status: 201 });
    });
    const incoming = mutationRequest("/api/sia/encontros/", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ encontro: "Teste" }),
    });
    const response = await proxySiaRequest(incoming, ["encontros"]);
    expect(response.status).toBe(201);
    expect(JSON.parse(body)).toEqual({ encontro: "Teste" });
  });

  it("preserva o boundary e o fluxo de multipart sem remontar o upload", async () => {
    const form = new FormData();
    form.set("foto", new Blob(["imagem"], { type: "image/png" }), "foto.png");
    let contentType = "";
    let body = "";
    vi.spyOn(globalThis, "fetch").mockImplementationOnce(async (_target, init) => {
      contentType = new Headers(init?.headers).get("content-type") ?? "";
      body = await new Response(init?.body).text();
      return Response.json({ foto: "/api/alpinistas/1/foto-arquivo/" });
    });
    const incoming = mutationRequest("/api/sia/alpinistas/1/foto/", { method: "PATCH", body: form });
    const response = await proxySiaRequest(incoming, ["alpinistas", "1", "foto"]);
    expect(response.status).toBe(200);
    expect(contentType).toMatch(/^multipart\/form-data; boundary=/);
    expect(body).toContain('name="foto"; filename="foto.png"');
  });

  it("preserva 204 sem fabricar corpo", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(null, { status: 204 }));
    const response = await proxySiaRequest(
      mutationRequest("/api/sia/encontros/1/", { method: "DELETE" }),
      ["encontros", "1"],
    );
    expect(response.status).toBe(204);
    expect(await response.text()).toBe("");
  });

  it("não tenta refresh em 403", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({ detail: "Sem permissão." }, { status: 403 }),
    );
    const response = await proxySiaRequest(request("/api/sia/eventos/"), ["eventos"]);
    expect(response.status).toBe(403);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("em 401 faz um refresh e repete exatamente uma vez", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json({}, { status: 401 }))
      .mockResolvedValueOnce(Response.json({ access: "novo.payload.signature" }))
      .mockResolvedValueOnce(Response.json({ results: [] }, { status: 200 }));
    const response = await proxySiaRequest(request("/api/sia/alpinistas/"), ["alpinistas"]);
    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(setCookies(response)).toContain("sia_access=novo.payload.signature");
  });

  it("não entra em loop se o retry também retornar 401", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json({}, { status: 401 }))
      .mockResolvedValueOnce(Response.json({ access: "novo.payload.signature" }))
      .mockResolvedValueOnce(Response.json({}, { status: 401 }));
    const response = await proxySiaRequest(request("/api/sia/alpinistas/"), ["alpinistas"]);
    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(setCookies(response)).toContain("Max-Age=0");
  });

  it("refresh inválido devolve 401 e limpa os cookies", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json({}, { status: 401 }))
      .mockResolvedValueOnce(Response.json({}, { status: 401 }));
    const response = await proxySiaRequest(request("/api/sia/alpinistas/"), ["alpinistas"]);
    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(setCookies(response)).toContain("sia_access=");
    expect(setCookies(response)).toContain("sia_refresh=");
  });
});

describe("referências retornadas pelo Django", () => {
  it("converte mídia protegida para o BFF e rejeita host arbitrário", () => {
    expect(toBffMediaReference(`${BACKEND_ORIGIN}/api/alpinistas/10/foto-arquivo/`))
      .toBe("/api/sia/alpinistas/10/foto-arquivo/");
    expect(toBffMediaReference("/api/encontros/2/fotos/3/arquivo/"))
      .toBe("/api/sia/encontros/2/fotos/3/arquivo/");
    expect(toBffMediaReference("https://evil.example/api/alpinistas/10/foto-arquivo/"))
      .toBeNull();
  });

  it("converte paginação absoluta do backend para caminho lógico do cliente", () => {
    expect(toBffApiReference(`${BACKEND_ORIGIN}/api/alpinistas/?page=2`))
      .toBe("/alpinistas/?page=2");
    expect(toBffApiReference("https://evil.example/api/alpinistas/?page=2"))
      .toBeUndefined();
  });

  it("faz streaming de mídia e mantém metadados seguros", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("bytes", {
      status: 200,
      headers: {
        "content-type": "image/png",
        "content-length": "5",
        "content-disposition": 'inline; filename="foto.png"',
        "set-cookie": "django=nao-repassar",
      },
    }));
    const response = await proxySiaRequest(
      request("/api/sia/alpinistas/10/foto-arquivo/"),
      ["alpinistas", "10", "foto-arquivo"],
    );
    expect(response.headers.get("content-type")).toBe("image/png");
    expect(response.headers.get("content-length")).toBe("5");
    expect(response.headers.get("content-disposition")).toContain("foto.png");
    expect(response.headers.has("set-cookie")).toBe(false);
    expect(await response.text()).toBe("bytes");
  });
});
