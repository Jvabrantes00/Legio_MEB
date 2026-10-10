// @vitest-environment jsdom

import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./sia-api", () => ({
  ensureCsrfToken: vi.fn().mockResolvedValue("csrf-publico"),
}));

import * as publicRoute from "../app/api/public/convites/route";
import { PublicInvitation } from "../components/PublicInvitation";
import { ensureCsrfToken } from "./sia-api";
import { proxyPublicInvitation } from "./server/public-invitation-bff";

const APP_ORIGIN = "http://localhost:3000";
const BACKEND_ORIGIN = "http://localhost:8000";
const PATH = "/api/public/convites/";
const TOKEN = "A".repeat(43);

function invitation(overrides: Record<string, unknown> = {}) {
  return {
    estado: "pendente",
    titulo_encontro: "Escalada 2030",
    datas_encontro: ["2030-06-01", "2030-06-02"],
    prazo_resposta: "2030-05-20T18:00:00-03:00",
    finalidade: "participar",
    pode_responder: true,
    mensagem: "Confirme ou recuse este convite dentro do prazo informado.",
    ...overrides,
  };
}

function bffRequest(body: Record<string, unknown>, headers: HeadersInit = {}) {
  const requestHeaders = new Headers({
    origin: APP_ORIGIN,
    cookie: "sia_csrf=csrf-publico; sia_access=jwt-nao-encaminhar",
    "x-csrf-token": "csrf-publico",
    "content-type": "application/json",
  });
  new Headers(headers).forEach((value, key) => requestHeaders.set(key, value));
  return new NextRequest(`${APP_ORIGIN}${PATH}`, {
    method: "POST",
    headers: requestHeaders,
    body: JSON.stringify(body),
  });
}

function payload(overrides: Record<string, unknown> = {}) {
  return {
    token: TOKEN,
    data_nascimento: "2000-01-01",
    acao: "validar",
    ...overrides,
  };
}

beforeEach(() => {
  process.env.SIA_BACKEND_URL = BACKEND_ORIGIN;
  process.env.SIA_APP_ORIGIN = APP_ORIGIN;
  vi.restoreAllMocks();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("BFF público de convite", () => {
  it("usa endpoint fixo, payload allowlist e não encaminha credenciais ou token em header", async () => {
    let forwarded: unknown;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementationOnce(async (_target, init) => {
      forwarded = await new Response(init?.body).json();
      return Response.json({ ...invitation(), pessoa_id: 99, digest: "nao-expor" });
    });
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => undefined);

    const response = await publicRoute.POST(bffRequest(payload(), {
      authorization: "Bearer atacante",
    }));
    const [target, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);

    expect(String(target)).toBe(`${BACKEND_ORIGIN}/api/public/convites/`);
    expect(String(target)).not.toContain(TOKEN);
    expect(forwarded).toEqual(payload());
    expect(headers.has("authorization")).toBe(false);
    expect(headers.has("cookie")).toBe(false);
    expect(headers.has("x-csrf-token")).toBe(false);
    expect(headers.has("token")).toBe(false);
    expect(consoleSpy).not.toHaveBeenCalled();
    expect(await response.json()).toEqual(invitation());
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.get("referrer-policy")).toBe("no-referrer");
  });

  it("rejeita campo extra e exige same-origin com double-submit CSRF", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const extra = await proxyPublicInvitation(bffRequest(payload({ pessoa_id: 1 })));
    const wrongOrigin = await proxyPublicInvitation(bffRequest(payload(), {
      origin: "https://evil.example",
    }));
    expect(extra.status).toBe(400);
    expect(wrongOrigin.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("uniformiza pré-auth, rate limit e falha temporária", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json({ detail: "token existe" }, { status: 404 }))
      .mockResolvedValueOnce(Response.json({ detail: "interno" }, { status: 429 }))
      .mockRejectedValueOnce(new Error("host privado"));
    const missing = await proxyPublicInvitation(bffRequest(payload()));
    const throttled = await proxyPublicInvitation(bffRequest(payload()));
    const temporary = await proxyPublicInvitation(bffRequest(payload()));
    expect(missing.status).toBe(404);
    expect(await missing.json()).toEqual({
      detail: "Não foi possível validar este convite. Confira os dados ou procure a equipe de Fichas.",
    });
    expect(throttled.status).toBe(429);
    expect(temporary.status).toBe(502);
  });

  it("uniformiza token malformado antes de consultar o backend", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const response = await proxyPublicInvitation(bffRequest(payload({
      token: "malformado",
    })));
    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({
      detail: "Não foi possível validar este convite. Confira os dados ou procure a equipe de Fichas.",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("página pública de convite", () => {
  it("trata falha de obtenção do CSRF sem enviar mutação", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch");
    vi.mocked(ensureCsrfToken).mockRejectedValueOnce(new Error("CSRF indisponível"));
    render(React.createElement(PublicInvitation, { token: TOKEN }));
    await user.type(screen.getByLabelText("Data de nascimento"), "2000-01-01");
    await user.click(screen.getByRole("button", { name: "Acessar convite" }));
    expect((await screen.findByRole("alert")).textContent).toContain(
      "Serviço temporariamente indisponível.",
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("exige nascimento antes de chamar o BFF e mostra validação genérica", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(React.createElement(PublicInvitation, { token: TOKEN }));
    await user.click(screen.getByRole("button", { name: "Acessar convite" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Informe sua data de nascimento.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("valida, renderiza o mínimo e confirma sem confundir com presença", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json(invitation()))
      .mockResolvedValueOnce(Response.json(invitation({
        estado: "confirmado",
        pode_responder: false,
        mensagem: "Sua confirmação foi registrada.",
      })));
    render(React.createElement(PublicInvitation, { token: TOKEN }));
    await user.type(screen.getByLabelText("Data de nascimento"), "2000-01-01");
    await user.click(screen.getByRole("button", { name: "Acessar convite" }));
    expect(await screen.findByText("Escalada 2030")).not.toBeNull();
    expect(screen.getByText(/presença efetiva.*separadamente/i)).not.toBeNull();
    await user.click(screen.getByRole("button", { name: "Confirmar convite" }));
    expect(await screen.findByText("Sua confirmação foi registrada.")).not.toBeNull();
    expect(screen.queryByRole("button", { name: "Confirmar convite" })).toBeNull();
    const sent = JSON.parse(String(fetchMock.mock.calls[1][1]?.body));
    expect(sent).toEqual(payload({ acao: "confirmar" }));
  });

  it("exige confirmação explícita antes de enviar recusa", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json(invitation()))
      .mockResolvedValueOnce(Response.json(invitation({
        estado: "recusado",
        pode_responder: false,
        mensagem: "Sua resposta de recusa foi registrada.",
      })));
    render(React.createElement(PublicInvitation, { token: TOKEN }));
    await user.type(screen.getByLabelText("Data de nascimento"), "2000-01-01");
    await user.click(screen.getByRole("button", { name: "Acessar convite" }));
    await screen.findByText("Escalada 2030");
    await user.click(screen.getByRole("button", { name: "Recusar" }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/confirma que deseja recusar/i)).not.toBeNull();
    await user.click(screen.getByRole("button", { name: "Sim, recusar convite" }));
    expect(await screen.findByText("Sua resposta de recusa foi registrada.")).not.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each([
    ["expirado", "O prazo deste convite terminou."],
    ["suspenso", "Este convite está em análise pela equipe de Fichas."],
    ["indisponivel", "Esta oportunidade não está mais disponível."],
  ])("mostra %s em modo somente leitura", async (estado, mensagem) => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json(invitation({
      estado,
      mensagem,
      pode_responder: false,
    })));
    render(React.createElement(PublicInvitation, { token: TOKEN }));
    await user.type(screen.getByLabelText("Data de nascimento"), "2000-01-01");
    await user.click(screen.getByRole("button", { name: "Acessar convite" }));
    expect(await screen.findByText(mensagem)).not.toBeNull();
    expect(screen.queryByRole("button", { name: "Confirmar convite" })).toBeNull();
  });

  it.each([
    [429, "Muitas tentativas. Tente novamente mais tarde."],
    [502, "Serviço temporariamente indisponível."],
    [404, "Não foi possível validar este convite. Confira os dados ou procure a equipe de Fichas."],
  ])("oferece feedback acessível para erro %s", async (status, message) => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}, { status }));
    render(React.createElement(PublicInvitation, { token: TOKEN }));
    await user.type(screen.getByLabelText("Data de nascimento"), "2000-01-01");
    await user.click(screen.getByRole("button", { name: "Acessar convite" }));
    expect((await screen.findByRole("alert")).textContent).toContain(message);
  });
});
