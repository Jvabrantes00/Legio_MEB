// @vitest-environment jsdom

import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import DetalhesEncontro from "./page";
import { siaFetch } from "../../../../lib/sia-api";

const state = vi.hoisted(() => ({
  id: "37",
  equipes: { modelo_equipes: "CANONICO", quantidade_equipes: 0 } as { modelo_equipes: "CANONICO" | "LEGADO"; quantidade_equipes: number } | null,
  resumoErro: null as string | null,
  session: null as null | {
    id: number;
    username: string;
    roles: string[];
    superuser: boolean;
  },
  capabilities: {
    consultar_resumo: true,
    consultar_encontristas: true,
    consultar_contato: false,
    acessar_pre_encontro: true,
    acessar_equipes: false,
    acessar_formacao: false,
    acessar_agenda: true,
    consultar_inscricoes: false,
    configurar_inscricoes: false,
  },
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: state.id }),
}));
vi.mock("../../../../components/SiaSessionProvider", () => ({
  useSiaSession: () => ({ session: state.session, loading: false, error: null }),
}));
vi.mock("../../../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
vi.mock("../../../../lib/pre-encounter-contract", () => ({
  parsePreEncounterContextCapabilities: (value: unknown) => value,
}));
vi.mock("../../../../components/EncounterWorkspace", () => ({
  EncounterWorkspace: ({
    renderEncontristas, renderTeam,
  }: {
    renderEncontristas?: (capabilities: typeof state.capabilities) => ReactNode;
    renderTeam?: (capabilities: typeof state.capabilities, equipes: typeof state.equipes, erro: string | null) => ReactNode;
  }) => (
    <div data-testid="workspace">
      {state.capabilities.acessar_equipes ? renderTeam?.(state.capabilities, state.equipes, state.resumoErro) : null}
      {state.capabilities.consultar_encontristas
        ? renderEncontristas?.(state.capabilities)
        : null}
    </div>
  ),
}));
vi.mock("../../../../components/EncounterCandidatesPanel", () => ({
  EncounterCandidatesPanel: ({
    encontroId,
    capabilities,
  }: {
    encontroId: string;
    capabilities: typeof state.capabilities;
  }) => (
    <div data-testid="canonical-candidates">
      {encontroId}:{capabilities.consultar_contato ? "full" : "summary"}
    </div>
  ),
}));
vi.mock("../../../../components/EncounterRegistrationConfigCard", () => ({
  EncounterRegistrationConfigCard: () => <div data-testid="registration-config">Configuração</div>,
}));
vi.mock("../../../../components/PreEncounterCheckin", () => ({
  PreEncounterCheckin: () => <div>Pré-Encontro</div>,
}));
vi.mock("../../../../components/ConfirmedAlpinistasTable", () => ({
  ConfirmedAlpinistasTable: () => <div>Confirmados legados</div>,
}));

const mockedFetch = vi.mocked(siaFetch);

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("integração de Encontristas no Workspace", () => {
  beforeEach(() => {
    state.id = "37";
    state.equipes = { modelo_equipes: "CANONICO", quantidade_equipes: 0 };
    state.resumoErro = null;
    state.capabilities.acessar_equipes = false;
    mockedFetch.mockReset();
    mockedFetch.mockResolvedValue(json({}));
    state.session = {
      id: 1,
      username: "comunicacao",
      roles: ["Comunicação"],
      superuser: false,
    };
    state.capabilities.consultar_encontristas = true;
    state.capabilities.consultar_contato = false;
    state.capabilities.consultar_inscricoes = false;
    state.capabilities.configurar_inscricoes = false;
  });

  afterEach(() => cleanup());

  it("oferece a projeção summary para Comunicação sem operações legadas", async () => {
    render(<DetalhesEncontro />);

    expect(await screen.findByText("37:summary")).toBeTruthy();
    expect(screen.queryByText("Operações legadas — transição")).toBeNull();
    expect(screen.queryByTestId("registration-config")).toBeNull();
    expect(mockedFetch).toHaveBeenCalledWith(
      "/encontros/37/pre-encontro/capabilities/",
    );
    expect(mockedFetch.mock.calls.every(([path]) => (
      path === "/encontros/37/pre-encontro/capabilities/"
    ))).toBe(true);
  });

  it("preserva configuração, full e operações legadas para a variante managed", async () => {
    state.session = {
      id: 2,
      username: "fichas-comunicacao",
      roles: ["Comunicação", "Fichas"],
      superuser: false,
    };
    state.capabilities.consultar_contato = true;
    state.capabilities.consultar_inscricoes = true;
    state.capabilities.configurar_inscricoes = true;

    render(<DetalhesEncontro />);

    expect(await screen.findByText("37:full")).toBeTruthy();
    expect(screen.getByTestId("registration-config")).toBeTruthy();
    expect(screen.getByText("Operações legadas — transição")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Fila de Espera" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Confirmar Selecionados/ })).toBeTruthy();
  });


  it("alterna a visão administrativa mantendo a matriz montada e reinicia em outro Encontro", async () => {
    state.session = { id: 2, username: "fichas", roles: ["Fichas"], superuser: false };
    state.equipes = { modelo_equipes: "LEGADO", quantidade_equipes: 0 };
    state.capabilities.acessar_equipes = true;
    mockedFetch.mockImplementation(async (path) => {
      if (String(path) === "/funcoes/") return json([{ id: 1, nome: "Apoio" }]);
      if (String(path).includes("workspace/equipes/")) return json([]);
      if (String(path).includes("participacoes-encontros")) return json([]);
      return json({});
    });
    const user = userEvent.setup();
    const view = render(<DetalhesEncontro />);
    const legacy = await screen.findByText("Montagem das Equipes");
    const group = screen.getByRole("group", { name: "Visão de equipes" });
    const legacyButton = within(group).getByRole("button", { name: "Matriz legada" });
    const canonicalButton = within(group).getByRole("button", { name: "Visão canônica" });
    expect(group.classList.contains("flex-wrap")).toBe(true);
    expect(group.classList.contains("gap-2")).toBe(true);
    for (const button of [legacyButton, canonicalButton]) {
      expect(button.classList.contains("focus-visible:ring-2")).toBe(true);
      expect(button.classList.contains("focus-visible:ring-offset-2")).toBe(true);
      expect(button.classList.contains("focus-visible:ring-gray-800")).toBe(true);
    }
    const expectSelection = (active: HTMLElement, inactive: HTMLElement) => {
      expect(active.getAttribute("aria-pressed")).toBe("true");
      expect(inactive.getAttribute("aria-pressed")).toBe("false");
      for (const name of ["bg-gray-800", "text-white"]) expect(active.classList.contains(name)).toBe(true);
      for (const name of ["bg-gray-100", "text-gray-600", "hover:bg-gray-200"]) expect(inactive.classList.contains(name)).toBe(true);
    };
    expectSelection(legacyButton, canonicalButton);
    expect(screen.queryByText("Equipes ainda não preparadas")).toBeNull();
    expect(mockedFetch.mock.calls.some(([path]) => String(path).includes("workspace/equipes/"))).toBe(false);
    await user.click(canonicalButton);
    expectSelection(canonicalButton, legacyButton);
    expect(legacy.closest("[hidden]")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Montagem das Equipes" })).toBeNull();
    expect(screen.getByText(/modelo canônico de Equipes não está ativo/)).toBeTruthy();
    expect(mockedFetch.mock.calls.some(([path]) => String(path).includes("workspace/equipes/"))).toBe(false);
    await user.click(screen.getByRole("button", { name: "Matriz legada" }));
    expect(screen.getByText("Montagem das Equipes")).toBe(legacy);
    await user.click(screen.getByRole("button", { name: "Visão canônica" }));
    state.id = "38"; view.rerender(<DetalhesEncontro />);
    expect(screen.getByRole("button", { name: "Matriz legada" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Montagem das Equipes")).toBe(legacy);
  });

  it("abre o modelo canônico por padrão sem alterá-lo", async () => {
    state.session = { id: 2, username: "fichas", roles: ["Fichas"], superuser: false };
    state.capabilities.acessar_equipes = true;
    mockedFetch.mockImplementation(async (path) => String(path).includes("workspace/equipes/") ? json([]) : json({}));
    render(<DetalhesEncontro />);
    expect((await screen.findByRole("button", { name: "Visão canônica" })).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("button", { name: "Matriz legada" }).getAttribute("aria-pressed")).toBe("false");
    expect(mockedFetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
  });

  it("mantém a visão resumida e distingue carregamento e falha do resumo", async () => {
    state.capabilities.acessar_equipes = true;
    state.equipes = null;
    const view = render(<DetalhesEncontro />);
    expect(await screen.findByText("Carregando resumo de equipes...")).toBeTruthy();
    expect(mockedFetch.mock.calls.some(([path]) => String(path).includes("workspace/equipes/"))).toBe(false);
    state.resumoErro = "Falha"; view.rerender(<DetalhesEncontro />);
    expect(screen.getByRole("alert").textContent).toContain("Resumo de equipes indisponível.");
    expect(screen.queryByText("Carregando resumo de equipes...")).toBeNull();
  });

  it("segue capabilities contextuais sem liberar superfícies legadas", async () => {
    state.session = {
      id: 3,
      username: "coordenacao-contextual",
      roles: [],
      superuser: false,
    };
    state.capabilities.consultar_contato = true;

    render(<DetalhesEncontro />);

    expect(await screen.findByText("37:full")).toBeTruthy();
    expect(screen.queryByText("Operações legadas — transição")).toBeNull();
    expect(screen.queryByTestId("registration-config")).toBeNull();
  });

  it("mantém default deny quando consultar_encontristas não foi concedida", async () => {
    state.capabilities.consultar_encontristas = false;
    render(<DetalhesEncontro />);

    expect(await screen.findByTestId("workspace")).toBeTruthy();
    expect(screen.queryByTestId("canonical-candidates")).toBeNull();
    expect(screen.queryByText("Operações legadas — transição")).toBeNull();
  });
});
