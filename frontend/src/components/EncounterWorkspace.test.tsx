// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";

import {
  EncounterWorkspace,
  type EncounterWorkspaceTab,
} from "./EncounterWorkspace";
import { siaFetch } from "../lib/sia-api";

vi.mock("../lib/sia-api", () => ({ siaFetch: vi.fn() }));
vi.mock("./EncounterAgendaSection", () => ({
  EncounterAgendaSection: () => <section data-testid="calendar-top">Calendário preservado no topo</section>,
}));

const mockedFetch = vi.mocked(siaFetch);

const capabilities = {
  consultar_resumo: true,
  consultar_encontristas: true,
  consultar_contato: false,
  acessar_pre_encontro: true,
  acessar_equipes: true,
  acessar_formacao: true,
  acessar_agenda: true,
  consultar_inscricoes: true,
  configurar_inscricoes: false,
};

const summary = {
  encontro: { id: 37, nome: "Escalada Serra Azul", tipo: "ESCALADA", local: "Casa de Encontros" },
  lifecycle: "EM_PREPARACAO",
  agenda: {
    configurada: true,
    oficializada: true,
    quantidade_itens: 5,
    proximo_item: "2030-03-12",
    datas_principais: ["2030-03-12", "2030-03-13"],
    pre_encontro_data: "2030-03-01",
  },
  encontristas: {
    inscricoes_recebidas: 21,
    pendentes: 9,
    confirmados: 12,
    total_funil: 21,
    por_situacao: {
      INSCRITO: 5,
      CANCELADO: 0,
      AGUARDANDO_DECISAO: 2,
      APTO: 2,
      NAO_APTO: 0,
      CONFIRMADO: 12,
    },
  },
  pre_encontro: {
    configurado: true,
    data: "2030-03-01",
    capacidade: 40,
    quantidade_checkins: 16,
    quantidade_aptos: 12,
    quantidade_aguardando_decisao: 2,
  },
  equipes: {
    modelo_equipes: "LEGADO",
    quantidade_equipes: 4,
    quantidade_funcoes: 10,
    vagas_estruturais: 24,
    vagas_preenchidas: 18,
  },
  formacao: { total_sessoes: 3, planejadas: 2, realizadas: 1, canceladas: 0 },
  alertas: [{ codigo: "INSCRICOES_NAO_CONFIGURADAS", mensagem: "Inscrições ainda não configuradas." }],
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function arrange(nextCapabilities = capabilities, summaryResponse = json(summary)) {
  mockedFetch.mockImplementation((path) => {
    if (path === "/encontros/37/workspace/capabilities/") return Promise.resolve(json(nextCapabilities));
    if (path === "/encontros/37/workspace/") return Promise.resolve(summaryResponse);
    return Promise.reject(new Error(`Path inesperado: ${String(path)}`));
  });
}

function WorkspaceHarness({
  includeEncontristas = true,
  includePreEncounter = true,
  includeTeam = true,
}: {
  includeEncontristas?: boolean;
  includePreEncounter?: boolean;
  includeTeam?: boolean;
} = {}) {
  const [tab, setTab] = useState<EncounterWorkspaceTab>("visao-geral");
  return (
    <EncounterWorkspace
      encontroId="37"
      activeTab={tab}
      onTabChange={setTab}
      renderEncontristas={includeEncontristas
        ? (workspaceCapabilities) => (
            <p>
              Conteúdo de Encontristas
              {workspaceCapabilities.consultar_contato ? " full" : " summary"}
            </p>
          )
        : undefined}
      renderPreEncounter={includePreEncounter
        ? () => <p>Conteúdo de Pré-Encontro</p>
        : undefined}
      renderTeam={includeTeam ? () => <p>Conteúdo de Equipe</p> : undefined}
    />
  );
}

describe("Workspace canônico do Encontro", () => {
  beforeEach(() => {
    mockedFetch.mockReset();
  });
  afterEach(() => cleanup());

  it("exibe somente as quatro abas aprovadas e mantém o Calendário no topo", async () => {
    arrange();
    render(<WorkspaceHarness />);

    expect(await screen.findByRole("heading", { name: "Escalada Serra Azul" })).toBeTruthy();
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual([
      "Visão geral",
      "Encontristas",
      "Pré-Encontro",
      "Equipe",
    ]);
    expect(screen.queryByRole("tab", { name: "Formação" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "Calendário" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Formação" })).toBeNull();
    expect(screen.getByRole("tab", { name: "Equipe" })).toBeTruthy();
    const calendar = screen.getByTestId("calendar-top");
    const tabs = screen.getByTestId("workspace-tabs-scroll");
    expect(screen.getAllByTestId("calendar-top")).toHaveLength(1);
    expect(calendar.compareDocumentPosition(tabs) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(tabs.className).toContain("overflow-x-auto");
  });

  it("usa exclusivamente o summary canônico, seus agregados e alertas", async () => {
    arrange();
    render(<WorkspaceHarness />);

    expect(await screen.findByText("Inscrições ainda não configuradas.")).toBeTruthy();
    expect(screen.getByText("21")).toBeTruthy();
    expect(screen.getByText("9")).toBeTruthy();
    expect(screen.getAllByText("12").length).toBeGreaterThan(0);
    expect(screen.queryByText("Sessões")).toBeNull();
    expect(screen.queryByText("Planejadas")).toBeNull();
    expect(screen.queryByText("Realizadas")).toBeNull();
    expect(screen.queryByText("Canceladas")).toBeNull();
    expect(screen.getByText("Próximo item")).toBeTruthy();
    expect(mockedFetch).toHaveBeenCalledWith("/encontros/37/workspace/", expect.any(Object));
    expect(mockedFetch.mock.calls.some(([path]) => path === "/encontros/37/")).toBe(false);
    expect(mockedFetch.mock.calls.every(([path]) => String(path).includes("/workspace/"))).toBe(true);
    expect(document.body.textContent?.toLocaleLowerCase()).not.toContain("cpf");
    expect(document.body.textContent?.toLocaleLowerCase()).not.toContain("cuidados");
    expect(document.body.textContent?.toLocaleLowerCase()).not.toContain("storage");
    expect(document.body.textContent?.toLocaleLowerCase()).not.toContain("pagamento");
  });

  it("usa capabilities para áreas e mantém o Pré-Encontro navegável", async () => {
    arrange({ ...capabilities, acessar_equipes: false, acessar_formacao: false, acessar_agenda: false });
    const user = userEvent.setup();
    render(<WorkspaceHarness />);

    await screen.findByRole("tab", { name: "Pré-Encontro" });
    expect(screen.queryByRole("tab", { name: "Equipe" })).toBeNull();
    expect(screen.queryByTestId("calendar-top")).toBeNull();
    await user.click(screen.getByRole("tab", { name: "Pré-Encontro" }));
    expect(screen.getByText("Conteúdo de Pré-Encontro")).toBeTruthy();
  });

  it("renderiza somente o slot da aba ativa e entrega capabilities a Encontristas", async () => {
    arrange();
    const user = userEvent.setup();
    render(<WorkspaceHarness />);

    await screen.findByRole("tab", { name: "Encontristas" });
    expect(screen.queryByText(/Conteúdo de Encontristas/)).toBeNull();
    expect(screen.queryByText("Conteúdo de Pré-Encontro")).toBeNull();
    expect(screen.queryByText("Conteúdo de Equipe")).toBeNull();

    await user.click(screen.getByRole("tab", { name: "Encontristas" }));
    expect(screen.getByText("Conteúdo de Encontristas summary")).toBeTruthy();
    expect(screen.queryByText("Conteúdo de Pré-Encontro")).toBeNull();
    expect(screen.queryByText("Conteúdo de Equipe")).toBeNull();

    await user.click(screen.getByRole("tab", { name: "Pré-Encontro" }));
    expect(screen.queryByText(/Conteúdo de Encontristas/)).toBeNull();
    expect(screen.getByText("Conteúdo de Pré-Encontro")).toBeTruthy();
    expect(screen.queryByText("Conteúdo de Equipe")).toBeNull();

    await user.click(screen.getByRole("tab", { name: "Equipe" }));
    expect(screen.queryByText(/Conteúdo de Encontristas/)).toBeNull();
    expect(screen.queryByText("Conteúdo de Pré-Encontro")).toBeNull();
    expect(screen.getByText("Conteúdo de Equipe")).toBeTruthy();
  });

  it("não apresenta área sem slot mesmo quando a capability existe", async () => {
    arrange();
    render(<WorkspaceHarness includeEncontristas={false} includeTeam={false} />);

    await screen.findByRole("tab", { name: "Visão geral" });
    expect(screen.queryByRole("tab", { name: "Encontristas" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "Equipe" })).toBeNull();
    expect(screen.getByRole("tab", { name: "Pré-Encontro" })).toBeTruthy();
  });

  it("não apresenta slot quando a capability correspondente foi revogada", async () => {
    arrange({
      ...capabilities,
      consultar_encontristas: false,
      acessar_pre_encontro: false,
      acessar_equipes: false,
    });
    render(<WorkspaceHarness />);

    await screen.findByRole("tab", { name: "Visão geral" });
    expect(screen.queryByRole("tab", { name: "Encontristas" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "Pré-Encontro" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "Equipe" })).toBeNull();
  });

  it("não monta slots inativos nem amplia superfícies legadas", async () => {
    arrange();
    const renderEncontristas = vi.fn(() => <p>Operação legada de Encontristas</p>);
    const renderPreEncounter = vi.fn(() => <p>Operação de Pré-Encontro</p>);
    const renderTeam = vi.fn(() => <p>Operação legada de Equipe</p>);

    function SlotHarness() {
      const [tab, setTab] = useState<EncounterWorkspaceTab>("visao-geral");
      return (
        <EncounterWorkspace
          encontroId="37"
          activeTab={tab}
          onTabChange={setTab}
          renderEncontristas={renderEncontristas}
          renderPreEncounter={renderPreEncounter}
          renderTeam={renderTeam}
        />
      );
    }

    const user = userEvent.setup();
    render(<SlotHarness />);
    await screen.findByRole("tab", { name: "Encontristas" });
    expect(renderEncontristas).not.toHaveBeenCalled();
    expect(renderPreEncounter).not.toHaveBeenCalled();
    expect(renderTeam).not.toHaveBeenCalled();

    await user.click(screen.getByRole("tab", { name: "Encontristas" }));
    expect(renderEncontristas).toHaveBeenCalledWith(capabilities);
    expect(renderPreEncounter).not.toHaveBeenCalled();
    expect(renderTeam).not.toHaveBeenCalled();
    await user.click(screen.getByRole("tab", { name: "Equipe" }));
    expect(renderTeam).toHaveBeenLastCalledWith(capabilities, summary.equipes, null);
  });

  it("preserva a navegação quando somente o summary falha", async () => {
    arrange(capabilities, json({ detail: "Falha" }, 500));
    render(<WorkspaceHarness />);

    expect(await screen.findByText("O Workspace está temporariamente indisponível.")).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Visão geral" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Encontristas" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Pré-Encontro" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Equipe" })).toBeTruthy();
  });

  it("preserva o estado de loading enquanto as capabilities são carregadas", async () => {
    let resolveCapabilities: (response: Response) => void = () => undefined;
    const pendingCapabilities = new Promise<Response>((resolve) => {
      resolveCapabilities = resolve;
    });
    mockedFetch
      .mockReturnValueOnce(pendingCapabilities)
      .mockResolvedValueOnce(json(summary));

    render(<WorkspaceHarness />);
    expect(screen.getByRole("status").textContent).toContain("Carregando Workspace");

    resolveCapabilities(json(capabilities));
    expect(await screen.findByRole("heading", { name: "Escalada Serra Azul" })).toBeTruthy();
  });

  it("apresenta 403 e 404 de capabilities como estados distintos", async () => {
    mockedFetch.mockResolvedValueOnce(json({ detail: "Negado" }, 403));
    const { unmount } = render(<WorkspaceHarness />);
    expect(await screen.findByText("Você não tem permissão para acessar esta área do Encontro.")).toBeTruthy();
    unmount();

    mockedFetch.mockReset();
    mockedFetch.mockResolvedValueOnce(json({ detail: "Ausente" }, 404));
    render(<WorkspaceHarness />);
    expect(await screen.findByText("Encontro não encontrado.")).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("tab")).toBeNull());
  });
});
