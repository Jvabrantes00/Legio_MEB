// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EncounterCandidatesPanel } from "../EncounterCandidatesPanel";
import { EncounterWorkspace, type EncounterWorkspaceTab } from "../EncounterWorkspace";
import { siaFetch } from "../../lib/sia-api";

vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
vi.mock("../EncounterAgendaSection", () => ({ EncounterAgendaSection: () => null }));

const mockedFetch = vi.mocked(siaFetch);
const base = "/encontros/37/workspace/";
const capabilities = {
  consultar_resumo: true, consultar_encontristas: true, consultar_contato: false,
  acessar_pre_encontro: false, acessar_equipes: false, acessar_formacao: false,
  acessar_agenda: false, consultar_inscricoes: false, configurar_inscricoes: false,
};
const summary = {
  encontro: { id: 37, nome: "Encontro Exemplo", tipo: "ESCALADA", local: "Local fictício" },
  lifecycle: "EM_PREPARACAO",
  agenda: { configurada: false, oficializada: false, quantidade_itens: 0, proximo_item: null, datas_principais: [], pre_encontro_data: null },
  encontristas: { inscricoes_recebidas: 0, pendentes: 0, confirmados: 0, total_funil: 0, por_situacao: { INSCRITO: 0, CANCELADO: 0, AGUARDANDO_DECISAO: 0, APTO: 0, NAO_APTO: 0, CONFIRMADO: 0 } },
  pre_encontro: { configurado: false, data: null, capacidade: null, quantidade_checkins: 0, quantidade_aptos: 0, quantidade_aguardando_decisao: 0 },
  equipes: { quantidade_equipes: 0, quantidade_funcoes: 0, vagas_estruturais: null, vagas_preenchidas: 0 },
  formacao: { total_sessoes: 0, planejadas: 0, realizadas: 0, canceladas: 0 },
  alertas: [],
};
const candidate = {
  ref: { origem_tipo: "INSCRICAO", origem_id: "ficticio-1" }, nome: "Pessoa Exemplo",
  origem: { codigo: "INSCRICAO", label: "Inscrição" },
  situacao: { codigo: "INSCRITO", label: "Inscrito" },
  presenca_pre: false, aptidao: null, pessoa_id: null,
};
function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
function page(results: unknown[], next: string | null = null, previous: string | null = null) {
  return { count: results.length, next, previous, results };
}
function arrange(options: { contact?: boolean; allowed?: boolean; candidates?: (path: string) => Response | Promise<Response> } = {}) {
  mockedFetch.mockImplementation((path) => {
    const url = String(path);
    if (url === `${base}capabilities/`) return Promise.resolve(json({ ...capabilities, consultar_contato: options.contact ?? false, consultar_encontristas: options.allowed ?? true }));
    if (url === base) return Promise.resolve(json(summary));
    if (url.startsWith(`${base}encontristas/?`)) return Promise.resolve(options.candidates?.(url) ?? json(page([candidate])));
    return Promise.reject(new Error(`URL inesperada: ${url}`));
  });
}
function candidatePaths() {
  return mockedFetch.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith(`${base}encontristas/?`));
}
function Harness() {
  const [tab, setTab] = useState<EncounterWorkspaceTab>("visao-geral");
  return <EncounterWorkspace encontroId="37" activeTab={tab} onTabChange={setTab} renderEncontristas={(caps) => <EncounterCandidatesPanel encontroId="37" capabilities={caps} />} />;
}
async function openPanel(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("tab", { name: "Encontristas" }));
}

describe("integração Workspace e Encontristas", () => {
  beforeEach(() => { mockedFetch.mockReset(); });
  afterEach(() => cleanup());

  it("apresenta o resumo sem contato nem campos privados", async () => {
    arrange({ candidates: () => json(page([{ ...candidate, telefone: "555-0101", email: "privado@example.test", cuidados: "conteúdo privado" }])) });
    const user = userEvent.setup();
    render(<Harness />);
    await openPanel(user);
    expect(await screen.findByText("Pessoa Exemplo")).toBeTruthy();
    expect(screen.getByLabelText("Buscar por nome")).toBeTruthy();
    expect(screen.queryByRole("columnheader", { name: "Telefone" })).toBeNull();
    for (const value of ["555-0101", "privado@example.test", "conteúdo privado"]) expect(screen.queryByText(value)).toBeNull();
    expect(candidatePaths()).toEqual([`${base}encontristas/?page=1`]);
  });

  it("apresenta a projeção completa quando contato é autorizado", async () => {
    arrange({ contact: true, candidates: () => json(page([{ ...candidate, telefone: "555-0101" }])) });
    const user = userEvent.setup();
    render(<Harness />);
    await openPanel(user);
    expect(await screen.findByText("555-0101")).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Telefone" })).toBeTruthy();
    expect(screen.getByLabelText("Buscar por nome ou telefone")).toBeTruthy();
    expect(candidatePaths()).toEqual([`${base}encontristas/?page=1`]);
  });

  it("oculta a aba e não consulta encontristas sem permissão", async () => {
    arrange({ allowed: false });
    render(<Harness />);
    await screen.findByRole("heading", { name: "Encontro Exemplo" });
    expect(screen.queryByRole("tab", { name: "Encontristas" })).toBeNull();
    expect(candidatePaths()).toEqual([]);
  });

  it("consulta ao navegar e reinicia a página na busca e nos filtros", async () => {
    arrange({ candidates: (path) => {
      const params = new URL(path, "http://localhost").searchParams;
      return json(page([candidate], params.get("page") === "1" ? "next" : null, params.get("page") === "2" ? "previous" : null));
    } });
    const user = userEvent.setup();
    render(<Harness />);
    await screen.findByRole("heading", { name: "Encontro Exemplo" });
    expect(candidatePaths()).toEqual([]);
    await openPanel(user);
    await screen.findByText("Pessoa Exemplo");
    await user.click(screen.getByRole("button", { name: "Próxima página" }));
    await screen.findByText("Página 2");
    await user.type(screen.getByLabelText("Buscar por nome"), "  Pessoa  ");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    await waitFor(() => expect(candidatePaths().at(-1)).toBe(`${base}encontristas/?page=1&search=Pessoa`));
    await screen.findByText("Página 1");
    await user.click(screen.getByRole("button", { name: "Próxima página" }));
    await screen.findByText("Página 2");
    await user.selectOptions(screen.getByLabelText("Situação"), "APTO");
    await waitFor(() => expect(candidatePaths().at(-1)).toBe(`${base}encontristas/?page=1&search=Pessoa&situacao=APTO`));
    await screen.findByText("Página 1");
    await user.click(screen.getByRole("button", { name: "Próxima página" }));
    await screen.findByText("Página 2");
    await user.selectOptions(screen.getByLabelText("Origem"), "PESSOA");
    await waitFor(() => expect(candidatePaths().at(-1)).toBe(`${base}encontristas/?page=1&search=Pessoa&situacao=APTO&origem=PESSOA`));
    expect(await screen.findByText("Página 1")).toBeTruthy();
    expect(candidatePaths()).toContain(`${base}encontristas/?page=2`);
  });

  it("exibe erro e repete a consulta sem mostrar dados obsoletos", async () => {
    let filteredCalls = 0;
    arrange({ candidates: (path) => {
      if (!path.includes("search=")) return json(page([candidate]));
      filteredCalls += 1;
      return filteredCalls === 1 ? json({ detail: "Falha de consulta" }, 400) : json(page([{ ...candidate, nome: "Resultado novo" }]));
    } });
    const user = userEvent.setup();
    render(<Harness />);
    await openPanel(user);
    await screen.findByText("Pessoa Exemplo");
    await user.type(screen.getByLabelText("Buscar por nome"), "Novo");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Falha de consulta");
    expect(screen.queryByText("Pessoa Exemplo")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Resultado novo")).toBeTruthy();
    expect(screen.queryByText("Pessoa Exemplo")).toBeNull();
    expect(candidatePaths().filter((path) => path === `${base}encontristas/?page=1&search=Novo`)).toHaveLength(2);
  });
});
