// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { EncounterTeamInvites } from "./EncounterTeamInvites";
import { siaFetch } from "../../lib/sia-api";
import type { EncounterTeam } from "../../lib/encounter-team/encounter-team-contract";
vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
it("mostra estado sem resposta e não sugere envio externo", async () => {
  vi.mocked(siaFetch).mockImplementation(async (path) => Response.json(String(path).startsWith("/alpinistas") ? { count: 0, next: null, previous: null, results: [] } : { count: 1, next: null, previous: null, results: [{ id: 1, pessoa_id: 2, pessoa_nome: "Pessoa", encontro_id: 1, finalidade: "trabalhar", status: "sem_resposta", role_trabalho_proposta_id: null, trabalho_id: null, trabalho_status: null, criado_em: "2026-01-01" }] }));
  render(<EncounterTeamInvites encontroId={1} teams={[]} enabled />);
  expect(await screen.findByText(/Pessoa — Sem resposta/)).toBeTruthy();
  const list = screen.getByRole("list", { name: "Convites registrados" });
  expect(within(list).getAllByRole("listitem")).toHaveLength(1);
  expect(within(list).getByRole("listitem").className).toContain("border");
  expect(screen.getByLabelText("Buscar alpinista por nome").tagName).toBe("INPUT");
  expect(screen.getByLabelText("Função").tagName).toBe("SELECT");
  expect(screen.getByLabelText("Paginação de alpinistas").className).toContain("gap-2");
  expect(screen.queryByText(/convite enviado/i)).toBeNull();
  expect(screen.queryByText(/etapa posterior/)).toBeNull();
});

it("atualiza a resposta na lista antes e depois da recarga", async () => {
  let resolveReload!: (response: Response) => void;
  let listCount = 0;
  const invite = { id: 1, pessoa_id: 2, pessoa_nome: "Pessoa", encontro_id: 1, finalidade: "trabalhar", status: "convidado", role_trabalho_proposta_id: null, trabalho_id: null, trabalho_status: null, criado_em: "2026-01-01" };
  const page = (status: string) => ({ count: 1, next: null, previous: null, results: [{ ...invite, status }] });
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    if (init?.method === "POST") return Response.json({});
    if (String(path).startsWith("/alpinistas")) return Response.json({ count: 0, next: null, previous: null, results: [] });
    listCount += 1;
    if (listCount === 1) return Response.json(page("convidado"));
    return new Promise<Response>((resolve) => { resolveReload = resolve; });
  });
  render(<EncounterTeamInvites encontroId={1} teams={[]} enabled />);
  fireEvent.click(await screen.findByRole("button", { name: "Registrar recusa" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar registro definitivo" }));
  expect(await screen.findByText("Pessoa — Recusado")).toBeTruthy();
  expect(screen.queryByText(/Pessoa — Pendente/)).toBeNull();
  await waitFor(() => expect(resolveReload).toBeDefined());
  resolveReload(Response.json(page("recusado")));
  await waitFor(() => expect(screen.getByText("Pessoa — Recusado")).toBeTruthy());
  expect(screen.queryByRole("button", { name: "Registrar recusa" })).toBeNull();
});

it("confirma duplicidade na lista e impede POSTs simultâneos", async () => {
  let resolvePost!: (response: Response) => void;
  const page = { count: 1, next: null, previous: null };
  const person = { id: 5, pessoa_id: 7, nome: "Pessoa", grupo: "A" };
  const invite = { id: 9, pessoa_id: 7, pessoa_nome: "Pessoa", encontro_id: 1, finalidade: "trabalhar", status: "convidado", role_trabalho_proposta_id: 3, trabalho_id: null, trabalho_status: null, criado_em: "2026-01-01" };
  const team = { id: 1, nome: "Apoio", roles: [{ id: 3, nome: "Membro", quantidade_estrutural: 1 }] } as EncounterTeam;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    if (init?.method === "POST") return new Promise<Response>((resolve) => { resolvePost = resolve; });
    return Response.json({ ...page, results: String(path).startsWith("/alpinistas") ? [person] : [invite] });
  });
  render(<EncounterTeamInvites encontroId={1} teams={[team]} enabled />);
  await screen.findByRole("option", { name: /Pessoa/ });
  fireEvent.change(screen.getByLabelText("Alpinista"), { target: { value: "7" } });
  fireEvent.change(screen.getByLabelText("Função"), { target: { value: "3" } });
  const button = screen.getByRole("button", { name: "Registrar convite" });
  fireEvent.click(button); fireEvent.click(button);
  expect(vi.mocked(siaFetch).mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  resolvePost(Response.json({ non_field_errors: ["Os campos pessoa_id, encontro_id, finalidade devem criar um set único."] }, { status: 400 }));
  expect(await screen.findByText("Já existe um convite de trabalho para esta pessoa neste Encontro.")).toBeTruthy();
  expect(screen.getByRole("alert").className).toContain("bg-red-50");
  await waitFor(() => expect(vi.mocked(siaFetch).mock.calls.filter(([path]) => String(path).startsWith("/convites-encontros/?")).length).toBeGreaterThanOrEqual(3));
  expect(screen.queryByText(/Convite registrado no SIA/)).toBeNull();
});

it("mostra falha de rede sem classificá-la como duplicidade e permite tentar novamente", async () => {
  const team = { id: 1, nome: "Apoio", roles: [{ id: 3, nome: "Membro", quantidade_estrutural: 1 }] } as EncounterTeam;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    if (init?.method === "POST") throw new Error("Conexão indisponível");
    return Response.json({ count: 1, next: null, previous: null, results: String(path).startsWith("/alpinistas") ? [{ id: 1, pessoa_id: 7, nome: "Pessoa", grupo: "A" }] : [] });
  });
  render(<EncounterTeamInvites encontroId={1} teams={[team]} enabled />);
  await screen.findByRole("option", { name: /Pessoa/ });
  fireEvent.change(screen.getByLabelText("Alpinista"), { target: { value: "7" } });
  fireEvent.change(screen.getByLabelText("Função"), { target: { value: "3" } });
  fireEvent.click(screen.getByRole("button", { name: "Registrar convite" }));
  expect(await screen.findByText("Conexão indisponível")).toBeTruthy();
  expect(screen.queryByText(/Já existe um convite/)).toBeNull();
  expect((screen.getByRole("button", { name: "Registrar convite" }) as HTMLButtonElement).disabled).toBe(false);
});
