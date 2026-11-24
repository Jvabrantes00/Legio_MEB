// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { EncounterTeamInviteActions } from "./EncounterTeamInviteActions";
import { siaFetch } from "../../lib/sia-api";
vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const invite = { id: 1, pessoa_id: 2, pessoa_nome: "Pessoa", encontro_id: 3, finalidade: "trabalhar" as const, status: "confirmado" as const, role_trabalho_proposta_id: 4, trabalho_id: null, trabalho_status: null, criado_em: "2026" };
it("exige confirmação explícita dos avisos antes do reenvio", async () => {
  vi.mocked(siaFetch).mockResolvedValueOnce(Response.json({ avaliacao: { resultado: "AVISO", motivos: [{ codigo: "PERFIL_ALPINISTA_AUSENTE", categoria: "AVISO", mensagem: "Aviso" }] } }, { status: 400 })).mockResolvedValueOnce(Response.json({ id: 5 }, { status: 201 }));
  const refresh = vi.fn();
  render(<EncounterTeamInviteActions invite={invite} refresh={refresh} />);
  fireEvent.click(screen.getByRole("button", { name: "Iniciar trabalho" }));
  expect(await screen.findByText(/Aviso \(PERFIL/)).toBeTruthy();
  expect(JSON.parse(String(vi.mocked(siaFetch).mock.calls[0][1]?.body))).toEqual({ convite_id: 1 });
  fireEvent.click(screen.getByLabelText("Confirmo os avisos"));
  fireEvent.click(screen.getByRole("button", { name: "Iniciar com confirmação" }));
  expect(await screen.findByText("Trabalho iniciado.")).toBeTruthy();
  expect(JSON.parse(String(vi.mocked(siaFetch).mock.calls[1][1]?.body))).toEqual({ convite_id: 1, confirmar_avisos: true });
  expect(refresh).toHaveBeenCalledTimes(2);
});
const answers = [
  ["Confirmar resposta", "confirmado", "confirmar a resposta", /Confirmado sem trabalho/],
  ["Registrar recusa", "recusado", "registrar a recusa", /Resposta: Recusado/],
  ["Registrar que não houve resposta (definitivo)", "sem_resposta", "registrar que não houve resposta", /Resposta: Sem resposta/],
] as const;
it.each(answers)("exige confirmação para %s e permite cancelar", (label, _status, description) => {
  render(<EncounterTeamInviteActions invite={{ ...invite, status: "convidado" }} refresh={vi.fn()} />);
  const trigger = screen.getByRole("button", { name: label });
  trigger.focus(); fireEvent.click(trigger);
  expect(siaFetch).not.toHaveBeenCalled();
  const dialog = screen.getByRole("dialog", { name: "Confirmar resposta definitiva" });
  expect(within(dialog).getByText(new RegExp(description))).toBeTruthy();
  expect(within(dialog).getByText(/DEFINITIVO.*não pode ser alterado/)).toBeTruthy();
  expect(within(dialog).getByText(/não envia mensagem à pessoa/)).toBeTruthy();
  expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Confirmar registro definitivo" }));
  for (const [name] of answers) expect((screen.getByRole("button", { name }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(trigger);
  expect(siaFetch).not.toHaveBeenCalled();
});
it.each(answers)("envia %s somente após confirmação e atualiza o estado", async (label, status, _description, displayed) => {
  let resolve!: (response: Response) => void;
  vi.mocked(siaFetch).mockImplementation(() => new Promise<Response>((done) => { resolve = done; }));
  const refresh = vi.fn(); const onAnswered = vi.fn();
  render(<EncounterTeamInviteActions invite={{ ...invite, status: "convidado" }} refresh={refresh} onAnswered={onAnswered} />);
  fireEvent.click(screen.getByRole("button", { name: label }));
  expect(siaFetch).not.toHaveBeenCalled();
  const confirm = screen.getByRole("button", { name: "Confirmar registro definitivo" });
  fireEvent.click(confirm); fireEvent.click(confirm);
  expect(siaFetch).toHaveBeenCalledTimes(1);
  expect(vi.mocked(siaFetch).mock.calls[0][0]).toBe("/convites-encontros/1/responder-trabalho/");
  expect(JSON.parse(String(vi.mocked(siaFetch).mock.calls[0][1]?.body))).toEqual({ status });
  resolve(Response.json({}));
  expect(await screen.findByText(displayed)).toBeTruthy();
  expect(screen.queryByRole("dialog")).toBeNull();
  for (const [name] of answers) expect(screen.queryByRole("button", { name })).toBeNull();
  expect(onAnswered).toHaveBeenCalledWith(status);
  await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
});
it("Escape cancela e devolve foco ao acionador", () => {
  render(<EncounterTeamInviteActions invite={{ ...invite, status: "convidado" }} refresh={vi.fn()} />);
  const trigger = screen.getByRole("button", { name: "Confirmar resposta" });
  fireEvent.click(trigger);
  fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(trigger);
  expect(siaFetch).not.toHaveBeenCalled();
});
it("mantém a confirmação e atualiza a lista após erro", async () => {
  vi.mocked(siaFetch).mockResolvedValue(Response.json({ detail: "Erro" }, { status: 400 }));
  const refresh = vi.fn();
  render(<EncounterTeamInviteActions invite={{ ...invite, status: "convidado" }} refresh={refresh} />);
  fireEvent.click(screen.getByRole("button", { name: "Registrar recusa" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar registro definitivo" }));
  expect(await screen.findByText(/Não foi possível concluir/)).toBeTruthy();
  expect(screen.getByRole("dialog")).toBeTruthy();
  expect(refresh).toHaveBeenCalledTimes(1);
});
it("preserva bloqueio e informa lotação sem reenviar automaticamente", async () => {
  vi.mocked(siaFetch).mockResolvedValueOnce(Response.json({ avaliacao: { resultado: "BLOQUEIO", motivos: [{ codigo: "ALPINISTA_INATIVO", categoria: "BLOQUEIO", mensagem: "Bloqueado" }] } }, { status: 400 }));
  const { unmount } = render(<EncounterTeamInviteActions invite={invite} refresh={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Iniciar trabalho" }));
  expect(await screen.findByText(/Bloqueado/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Iniciar com confirmação" })).toBeNull();
  expect(siaFetch).toHaveBeenCalledTimes(1);
  unmount();
  vi.mocked(siaFetch).mockResolvedValueOnce(Response.json({ avaliacao: { resultado: "BLOQUEIO", motivos: [{ codigo: "QUANTIDADE_ESTRUTURAL_EXCEDIDA", categoria: "BLOQUEIO", mensagem: "Quantidade estrutural excedida" }] } }, { status: 400 }));
  render(<EncounterTeamInviteActions invite={invite} refresh={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Iniciar trabalho" }));
  expect(await screen.findByText(/função proposta está sem vagas/)).toBeTruthy();
  expect(screen.getByText(/Confirmado sem trabalho/)).toBeTruthy();
});
