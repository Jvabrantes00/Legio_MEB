// @vitest-environment jsdom
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { siaFetch } from "../../lib/sia-api";
import { EncounterTeamPanel } from "./EncounterTeamPanel";
vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
const fetchMock = vi.mocked(siaFetch);
const caps = { consultar_resumo: true, consultar_encontristas: true, consultar_contato: false, acessar_pre_encontro: false, acessar_equipes: true, acessar_formacao: false, acessar_agenda: false, consultar_inscricoes: false, configurar_inscricoes: false };
const equipes = { modelo_equipes: "CANONICO" as const, quantidade_equipes: 1 };
const team = { id: 1, encontro_id: 2, codigo: "A", nome: "Equipe Exemplo", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: 4, capacidade: { resultado: "AVISO", motivos: [{ codigo: "CAPACIDADE_MINIMA_NAO_ATINGIDA", categoria: "AVISO", mensagem: "Abaixo" }] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [{ id: 3, codigo: "R", nome: "Apoio", ordem: 0, quantidade_estrutural: null, concede_registro_presenca: false, trabalhos: [{ id: 4, pessoa_id: 5, pessoa_nome: "Pessoa Exemplo", status: "alocado", cpf: "segredo" }] }] };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
describe("painel de equipes", () => {
  beforeEach(() => fetchMock.mockReset()); afterEach(cleanup);
  it("distingue resumo carregando de resumo indisponível sem consultar equipes", () => {
    const view = render(<EncounterTeamPanel encontroId={2} capabilities={caps} equipes={null} />);
    expect(screen.getByRole("status").textContent).toContain("Carregando resumo de equipes...");
    expect(screen.queryByText("Resumo de equipes indisponível.")).toBeNull();
    view.rerender(<EncounterTeamPanel encontroId={2} capabilities={caps} equipes={null} resumoErro="Falha" />);
    expect(screen.getByRole("alert").textContent).toContain("Resumo de equipes indisponível.");
    expect(screen.queryByRole("status")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("nega por padrão e revoga acesso", async () => {
    fetchMock.mockResolvedValue(json([team]));
    const view = render(<EncounterTeamPanel encontroId={2} capabilities={null} equipes={equipes} />);
    expect(fetchMock).not.toHaveBeenCalled();
    view.rerender(<EncounterTeamPanel encontroId={2} capabilities={caps} equipes={equipes} />);
    await screen.findByText("Pessoa Exemplo — alocado");
    view.rerender(<EncounterTeamPanel encontroId={2} capabilities={{ ...caps, acessar_equipes: false }} equipes={equipes} />);
    expect(screen.queryByText("Pessoa Exemplo — alocado")).toBeNull();
  });
  it("exibe carregamento, conteúdo seguro e aviso", async () => {
    fetchMock.mockResolvedValue(json([team]));
    render(<EncounterTeamPanel encontroId={2} capabilities={caps} equipes={equipes} />);
    expect(screen.getByRole("status")).toBeTruthy();
    expect(await screen.findByText("Pessoa Exemplo — alocado")).toBeTruthy();
    expect(screen.getByText("Vagas estruturais: não definida")).toBeTruthy();
    expect(screen.getByText("Abaixo")).toBeTruthy();
    expect(screen.getByText("Visão canônica somente leitura. Não substitui a montagem de equipes.")).toBeTruthy();
    expect(screen.queryByText("segredo")).toBeNull(); expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
  it("apresenta vazio, erro, retry e 403", async () => {
    fetchMock.mockResolvedValueOnce(json([])).mockResolvedValueOnce(json({ detail: "Falha" }, 500)).mockResolvedValueOnce(json({ detail: "negado" }, 403)).mockResolvedValueOnce(json([team]));
    const view = render(<EncounterTeamPanel encontroId={2} capabilities={caps} equipes={equipes} />);
    await screen.findByText("Equipes ainda não preparadas");
    view.rerender(<EncounterTeamPanel encontroId={3} capabilities={caps} equipes={equipes} />);
    await screen.findByRole("alert");
    const user = userEvent.setup(); await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Você não tem permissão");
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await screen.findByText("Equipe Exemplo");
  });
  it("aborta e ignora resposta antiga ao trocar encontro e desmontar", async () => {
    let resolveOld!: (response: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; })).mockResolvedValueOnce(json([{ ...team, nome: "Nova" }]));
    const view = render(<EncounterTeamPanel encontroId={2} capabilities={caps} equipes={equipes} />);
    const oldSignal = fetchMock.mock.calls[0][1]?.signal as AbortSignal;
    view.rerender(<EncounterTeamPanel encontroId={3} capabilities={caps} equipes={equipes} />);
    expect(oldSignal.aborted).toBe(true); await screen.findByText("Nova");
    await act(async () => resolveOld(json([team])));
    expect(screen.queryByText("Equipe Exemplo")).toBeNull();
    const newSignal = fetchMock.mock.calls[1][1]?.signal as AbortSignal;
    view.unmount(); await waitFor(() => expect(newSignal.aborted).toBe(true));
  });
  it("não consulta no legado vazio e identifica registros canônicos preexistentes", async () => {
    fetchMock.mockResolvedValue(json([team]));
    const view = render(<EncounterTeamPanel encontroId={2} capabilities={caps} equipes={{ modelo_equipes: "LEGADO", quantidade_equipes: 0 }} />);
    expect(screen.getByText(/modelo canônico de Equipes não está ativo/)).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByText("Equipes ainda não preparadas")).toBeNull();
    view.rerender(<EncounterTeamPanel encontroId={2} capabilities={caps} equipes={{ modelo_equipes: "LEGADO", quantidade_equipes: 1 }} />);
    expect(await screen.findByText("Equipe Exemplo")).toBeTruthy();
    expect(screen.getByText("Canônicos preexistentes — não ativos no modelo LEGADO")).toBeTruthy();
  });
});
