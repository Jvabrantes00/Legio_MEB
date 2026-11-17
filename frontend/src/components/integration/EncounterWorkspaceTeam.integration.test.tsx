// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { siaFetch } from "../../lib/sia-api";
import { EncounterTeamPanel } from "../encounter-team/EncounterTeamPanel";
import { EncounterWorkspace, type EncounterWorkspaceTab } from "../EncounterWorkspace";
vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
vi.mock("../EncounterAgendaSection", () => ({ EncounterAgendaSection: () => null }));
const caps = { consultar_resumo: true, consultar_encontristas: false, consultar_contato: false, acessar_pre_encontro: false, acessar_equipes: true, acessar_formacao: false, acessar_agenda: false, consultar_inscricoes: false, configurar_inscricoes: false };
const summary = { encontro: { id: 37, nome: "Encontro Exemplo", tipo: "ESCALADA", local: "Local fictício" }, lifecycle: "EM_PREPARACAO", agenda: { configurada: false, oficializada: false, quantidade_itens: 0, proximo_item: null, datas_principais: [], pre_encontro_data: null }, encontristas: { inscricoes_recebidas: 0, pendentes: 0, confirmados: 0, total_funil: 0, por_situacao: { INSCRITO: 0, CANCELADO: 0, AGUARDANDO_DECISAO: 0, APTO: 0, NAO_APTO: 0, CONFIRMADO: 0 } }, pre_encontro: { configurado: false, data: null, capacidade: null, quantidade_checkins: 0, quantidade_aptos: 0, quantidade_aguardando_decisao: 0 }, equipes: { modelo_equipes: "CANONICO", quantidade_equipes: 0, quantidade_funcoes: 0, vagas_estruturais: null, vagas_preenchidas: 0 }, formacao: { total_sessoes: 0, planejadas: 0, realizadas: 0, canceladas: 0 }, alertas: [] };
function Harness() { const [tab, setTab] = useState<EncounterWorkspaceTab>("visao-geral"); return <EncounterWorkspace encontroId="37" activeTab={tab} onTabChange={setTab} renderTeam={(capabilities, equipes, resumoErro) => <EncounterTeamPanel encontroId={37} capabilities={capabilities} equipes={equipes} resumoErro={resumoErro} />} />; }
beforeEach(() => { vi.mocked(siaFetch).mockReset(); });
afterEach(cleanup);
it("injeta a consulta somente ao abrir a aba de equipe", async () => {
  vi.mocked(siaFetch).mockImplementation(async (path) => {
    const url = String(path);
    const body = url === "/encontros/37/workspace/capabilities/" ? caps : url === "/encontros/37/workspace/" ? summary : url === "/encontros/37/workspace/equipes/" ? [] : null;
    if (body === null) throw new Error(`URL inesperada: ${url}`);
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  const user = userEvent.setup(); render(<Harness />);
  await screen.findByRole("heading", { name: "Encontro Exemplo" });
  expect(vi.mocked(siaFetch).mock.calls.some(([path]) => String(path) === "/encontros/37/workspace/equipes/")).toBe(false);
  await user.click(screen.getByRole("tab", { name: "Equipe" }));
  expect(await screen.findByText("Equipes ainda não preparadas")).toBeTruthy();
  expect(vi.mocked(siaFetch).mock.calls.some(([path]) => String(path) === "/encontros/37/workspace/equipes/")).toBe(true);
});
it.each([0, 1])("trata modelo legado com %i registros", async (count) => {
  const legacySummary = { ...summary, equipes: { ...summary.equipes, modelo_equipes: "LEGADO", quantidade_equipes: count } };
  const team = { id: 1, encontro_id: 37, codigo: "A", nome: "Equipe preexistente", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [] };
  vi.mocked(siaFetch).mockImplementation(async (path) => {
    const url = String(path);
    const body = url === "/encontros/37/workspace/capabilities/" ? caps : url === "/encontros/37/workspace/" ? legacySummary : url === "/encontros/37/workspace/equipes/" ? [team] : null;
    if (body === null) throw new Error("URL inesperada");
    return new Response(JSON.stringify(body), { status: 200 });
  });
  const user = userEvent.setup(); render(<Harness />);
  await screen.findByRole("heading", { name: "Encontro Exemplo" });
  expect(vi.mocked(siaFetch).mock.calls.some(([path]) => String(path) === "/encontros/37/workspace/equipes/")).toBe(false);
  await user.click(screen.getByRole("tab", { name: "Equipe" }));
  expect(screen.getByText(/modelo canônico de Equipes não está ativo/)).toBeTruthy();
  if (count) {
    expect(await screen.findByText("Equipe preexistente")).toBeTruthy();
    expect(screen.getByText("Canônicos preexistentes — não ativos no modelo LEGADO")).toBeTruthy();
  }
  expect(vi.mocked(siaFetch).mock.calls.some(([path]) => String(path) === "/encontros/37/workspace/equipes/")).toBe(Boolean(count));
  expect(screen.queryByText("Equipes ainda não preparadas")).toBeNull();
});
