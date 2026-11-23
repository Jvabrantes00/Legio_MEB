// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { EncounterTeamSetup } from "./EncounterTeamSetup";
import { siaFetch } from "../../lib/sia-api";
vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const readiness = { elegivel: true, motivos: [], contagens: { vinculos_legados_equipe: 0, vinculos_tipo_indefinido: 0, equipes_canonicas: 0, trabalhos_canonicos: 0 } };
it("exige justificativa e confirmação para ativar", async () => {
  vi.mocked(siaFetch).mockResolvedValueOnce(Response.json(readiness)).mockResolvedValueOnce(Response.json({ modelo_equipes: "CANONICO" }));
  const changed = vi.fn(); render(<EncounterTeamSetup encontroId={1} modelo="LEGADO" canActivate canPrepare onChange={changed} />);
  const button = await screen.findByRole("button", { name: "Ativar modelo canônico" });
  expect((button as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Justificativa"), { target: { value: "  Motivo  " } });
  fireEvent.click(button);
  expect(vi.mocked(siaFetch).mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
  fireEvent.click(screen.getByLabelText("Confirmo a ativação do modelo canônico"));
  fireEvent.change(screen.getByLabelText("Justificativa"), { target: { value: "   " } });
  expect((button as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(button);
  expect(vi.mocked(siaFetch).mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
  fireEvent.change(screen.getByLabelText("Justificativa"), { target: { value: "  Motivo  " } });
  fireEvent.click(button);
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
  const [url, init] = vi.mocked(siaFetch).mock.calls[1];
  expect(url).toBe("/encontros/1/modelo-equipes/");
  expect(init?.method).toBe("POST");
  expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
  const body = JSON.parse(String(init?.body));
  expect(body).toEqual({ justificativa: "Motivo", confirmacao: true });
  expect(typeof body.justificativa).toBe("string");
  expect(body.justificativa.trim()).not.toBe("");
  expect(body.confirmacao).toBe(true);
  expect(screen.getByText("Modelo canônico ativado.")).toBeTruthy();
  expect(screen.getByText("Modelo canônico ativado.").getAttribute("role")).toBe("status");
  expect(screen.getByText("Modelo canônico ativado.").className).toContain("bg-green-50");
  expect(screen.getByLabelText("Justificativa").tagName).toBe("INPUT");
});
it("não oferece ativação sem permissão", () => { render(<EncounterTeamSetup encontroId={1} modelo="LEGADO" canActivate={false} canPrepare onChange={() => {}} />); expect(screen.queryByText("Ativar modelo canônico")).toBeNull(); });

it.each([400, 409])("mostra erro %i e permite nova tentativa", async (status) => {
  vi.mocked(siaFetch).mockResolvedValueOnce(Response.json(readiness)).mockResolvedValueOnce(Response.json({ detail: "Falha na ativação." }, { status })).mockResolvedValueOnce(Response.json({ modelo_equipes: "CANONICO" }));
  const changed = vi.fn(); render(<EncounterTeamSetup encontroId={1} modelo="LEGADO" canActivate canPrepare onChange={changed} />);
  const button = await screen.findByRole("button", { name: "Ativar modelo canônico" });
  fireEvent.change(screen.getByLabelText("Justificativa"), { target: { value: "Motivo" } });
  fireEvent.click(screen.getByLabelText("Confirmo a ativação do modelo canônico"));
  fireEvent.click(button);
  expect((await screen.findByRole("alert")).textContent).toContain("Falha na ativação.");
  expect(changed).not.toHaveBeenCalled();
  fireEvent.click(button);
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
});

it("mostra falha de rede e permite nova tentativa", async () => {
  vi.mocked(siaFetch).mockResolvedValueOnce(Response.json(readiness)).mockRejectedValueOnce(new Error("Rede indisponível")).mockResolvedValueOnce(Response.json({ modelo_equipes: "CANONICO" }));
  const changed = vi.fn(); render(<EncounterTeamSetup encontroId={1} modelo="LEGADO" canActivate canPrepare onChange={changed} />);
  const button = await screen.findByRole("button", { name: "Ativar modelo canônico" });
  fireEvent.change(screen.getByLabelText("Justificativa"), { target: { value: "Motivo" } });
  fireEvent.click(screen.getByLabelText("Confirmo a ativação do modelo canônico"));
  fireEvent.click(button);
  expect((await screen.findByRole("alert")).textContent).toContain("Rede indisponível");
  expect(changed).not.toHaveBeenCalled();
  fireEvent.click(button);
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
});

it("prepara equipes com corpo vazio", async () => {
  vi.mocked(siaFetch).mockResolvedValueOnce(Response.json([]));
  const changed = vi.fn(); render(<EncounterTeamSetup encontroId={1} modelo="CANONICO" canActivate canPrepare onChange={changed} />);
  fireEvent.click(screen.getByRole("button", { name: "Preparar equipes" }));
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
  const [url, init] = vi.mocked(siaFetch).mock.calls[0];
  expect(url).toBe("/encontros/1/preparar-equipes/");
  expect(init?.method).toBe("POST");
  expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
  expect(JSON.parse(String(init?.body))).toEqual({});
});
