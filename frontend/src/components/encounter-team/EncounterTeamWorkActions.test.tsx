// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { siaFetch } from "../../lib/sia-api";
import type { EncounterTeam } from "../../lib/encounter-team/encounter-team-contract";
import { EncounterTeamWorkActions } from "./EncounterTeamWorkActions";
vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const teams = [{ nome: "Equipe", roles: [{ id: 1, nome: "Origem", quantidade_estrutural: 2, trabalhos: [{ status: "alocado" }] }, { id: 2, nome: "Destino", quantidade_estrutural: 3, trabalhos: [] }] }] as EncounterTeam[];
const posts = () => vi.mocked(siaFetch).mock.calls.filter(([, init]) => init?.method === "POST");
it.each([["Alocar", undefined, "alocar", { role_equipe_id: 2 }], ["Realocar", 1, "realocar", { role_equipe_id: 2 }], ["Desalocar", 1, "desalocar", {}]] as const)("%s exige confirmação e envia o corpo exato", async (label, currentRoleId, action, body) => {
  vi.mocked(siaFetch).mockResolvedValue(Response.json({})); const refresh = vi.fn();
  render(<EncounterTeamWorkActions trabalhoId={7} teams={teams} currentRoleId={currentRoleId} refresh={refresh} />);
  const trigger = screen.getByRole("button", { name: label }); fireEvent.click(trigger);
  const dialog = screen.getByRole("dialog"); expect(posts()).toHaveLength(0);
  expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Confirmar" }));
  if (action !== "desalocar") { fireEvent.change(within(dialog).getByLabelText("Função"), { target: { value: "2" } }); expect(within(dialog).getByText(/Equipe — Destino.*ocupação: 0/)).toBeTruthy(); }
  if (action === "realocar") { expect(within(dialog).queryByRole("option", { name: /Origem/ })).toBeNull(); expect(within(dialog).getByText(/De Equipe — Origem para Equipe — Destino/)).toBeTruthy(); }
  if (action === "desalocar") expect(within(dialog).getByText(/não é a retirada definitiva/)).toBeTruthy();
  const confirm = within(dialog).getByRole("button", { name: "Confirmar" }); fireEvent.click(confirm); fireEvent.click(confirm);
  expect(posts()).toHaveLength(1); expect(posts()[0][0]).toBe(`/trabalhos-encontros/7/${action}/`); expect(JSON.parse(String(posts()[0][1]?.body))).toEqual(body);
  await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
});
it.each(["Cancelar", "Escape"])("%s fecha sem requisição e devolve foco", (method) => {
  render(<EncounterTeamWorkActions trabalhoId={7} teams={teams} />); const trigger = screen.getByRole("button", { name: "Alocar" }); fireEvent.click(trigger);
  const dialog = screen.getByRole("dialog"); if (method === "Cancelar") fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" })); else fireEvent.keyDown(dialog, { key: "Escape" });
  expect(posts()).toHaveLength(0); expect(screen.queryByRole("dialog")).toBeNull(); expect(document.activeElement).toBe(trigger);
});
it("exige aceite de aviso antes de reenviar", async () => {
  vi.mocked(siaFetch).mockResolvedValueOnce(Response.json({ avaliacao: { resultado: "AVISO", motivos: [{ codigo: "ALPINISTA_INATIVO", categoria: "AVISO", mensagem: "Aviso" }] } }, { status: 400 })).mockResolvedValueOnce(Response.json({}));
  render(<EncounterTeamWorkActions trabalhoId={7} teams={teams} />); fireEvent.click(screen.getByRole("button", { name: "Alocar" })); fireEvent.change(screen.getByLabelText("Função"), { target: { value: "2" } });
  expect(posts()).toHaveLength(0); fireEvent.click(screen.getByRole("button", { name: "Confirmar" })); await screen.findByText("Aviso"); expect(posts()).toHaveLength(1);
  expect((screen.getByRole("button", { name: "Confirmar" }) as HTMLButtonElement).disabled).toBe(true); fireEvent.click(screen.getByLabelText("Confirmo os avisos")); fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  expect(posts()).toHaveLength(2); expect(JSON.parse(String(posts()[1][1]?.body))).toEqual({ role_equipe_id: 2, confirmar_avisos: true });
});
it("lotação bloqueia reenvio e solicita atualização", async () => {
  vi.mocked(siaFetch).mockResolvedValue(Response.json({ avaliacao: { resultado: "BLOQUEIO", motivos: [{ codigo: "QUANTIDADE_ESTRUTURAL_EXCEDIDA", categoria: "BLOQUEIO", mensagem: "Lotada" }] } }, { status: 400 })); const refresh = vi.fn();
  render(<EncounterTeamWorkActions trabalhoId={7} teams={teams} refresh={refresh} />); fireEvent.click(screen.getByRole("button", { name: "Alocar" })); fireEvent.change(screen.getByLabelText("Função"), { target: { value: "2" } }); fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  await screen.findByText(/sem vagas e nada foi alterado/); expect(screen.queryByRole("button", { name: "Confirmar" })).toBeNull(); expect(posts()).toHaveLength(1); expect(refresh).toHaveBeenCalledTimes(1);
});
it("apresenta falha de rede e atualiza", async () => {
  vi.mocked(siaFetch).mockRejectedValue(new Error("rede")); const refresh = vi.fn(); render(<EncounterTeamWorkActions trabalhoId={7} teams={teams} currentRoleId={1} refresh={refresh} />);
  fireEvent.click(screen.getByRole("button", { name: "Desalocar" })); fireEvent.click(screen.getByRole("button", { name: "Confirmar" })); await screen.findByText("Não foi possível contatar o servidor."); expect(refresh).toHaveBeenCalledTimes(1);
});

it.each([[403, { detail: "negado" }, /permissão/], [400, { non_field_errors: ["Erro de domínio"] }, /Erro de domínio/]])("apresenta erro %i e atualiza", async (status, body, message) => {
  vi.mocked(siaFetch).mockResolvedValue(Response.json(body, { status })); const refresh = vi.fn(); render(<EncounterTeamWorkActions trabalhoId={7} teams={teams} currentRoleId={1} refresh={refresh} />);
  fireEvent.click(screen.getByRole("button", { name: "Desalocar" })); expect(posts()).toHaveLength(0); fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  await screen.findByText(message); expect(posts()).toHaveLength(1); expect(refresh).toHaveBeenCalledTimes(1);
});
