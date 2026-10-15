// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EncounterRegistrationConfigCard } from "./EncounterRegistrationConfigCard";
import { siaFetch } from "../lib/sia-api";

vi.mock("../lib/sia-api", () => ({ siaFetch: vi.fn() }));
vi.mock("react-hot-toast", () => ({ default: { success: vi.fn(), error: vi.fn() } }));

const mockedFetch = vi.mocked(siaFetch);

const capabilities = {
  consultar_resumo: true,
  consultar_encontristas: true,
  consultar_contato: true,
  acessar_pre_encontro: true,
  acessar_equipes: true,
  acessar_formacao: true,
  acessar_agenda: true,
  consultar_inscricoes: true,
  configurar_inscricoes: true,
};

const absent = {
  configurado: false,
  capacidade: null,
  idade_minima: null,
  idade_maxima: null,
  inscricoes_abrem_em: null,
  inscricoes_encerram_em: null,
  public_id: null,
  status_janela: null,
};

const configured = {
  configurado: true,
  capacidade: 30,
  idade_minima: 15,
  idade_maxima: 18,
  inscricoes_abrem_em: "2030-01-01T08:00:00-03:00",
  inscricoes_encerram_em: "2030-02-01T08:00:00-03:00",
  public_id: "2a62fca6-e0cc-4fb4-9728-8ff8be832adc",
  status_janela: "abertas",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function load(config = absent, nextCapabilities = capabilities) {
  mockedFetch
    .mockResolvedValueOnce(json(nextCapabilities))
    .mockResolvedValueOnce(json(config));
}

describe("card de configuração de inscrições", () => {
  beforeEach(() => mockedFetch.mockReset());
  afterEach(() => cleanup());

  it("mostra ausência e abre formulário estrito com cinco campos", async () => {
    load();
    const user = userEvent.setup();
    render(<EncounterRegistrationConfigCard encontroId="37" />);
    expect(await screen.findByText("Não configuradas")).toBeTruthy();
    expect(screen.getByText("Inscrições ainda não configuradas.")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Configurar inscrições" }));
    expect(screen.getByLabelText("Capacidade")).toBeTruthy();
    expect(screen.getByLabelText("Idade mínima")).toBeTruthy();
    expect(screen.getByLabelText("Idade máxima")).toBeTruthy();
    expect(screen.getByLabelText("Abertura das inscrições")).toBeTruthy();
    expect(screen.getByLabelText("Encerramento das inscrições")).toBeTruthy();
    expect(screen.queryByLabelText(/public_id/i)).toBeNull();
    expect(screen.getAllByRole("button", { name: "Salvar alterações" })).toHaveLength(1);
    expect((screen.getByRole("button", { name: "Salvar alterações" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("não oferece configuração sem capability de gestão", async () => {
    load(absent, { ...capabilities, configurar_inscricoes: false });
    render(<EncounterRegistrationConfigCard encontroId="37" />);
    expect(await screen.findByText("Não configuradas")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Configurar inscrições" })).toBeNull();
  });

  it("cria em um único submit, bloqueia repetição e atualiza o card", async () => {
    load();
    let resolveSave: ((response: Response) => void) | undefined;
    mockedFetch.mockImplementationOnce(() => new Promise((resolve) => { resolveSave = resolve; }));
    const user = userEvent.setup();
    render(<EncounterRegistrationConfigCard encontroId="37" />);
    await user.click(await screen.findByRole("button", { name: "Configurar inscrições" }));
    await user.type(screen.getByLabelText("Capacidade"), "30");
    await user.type(screen.getByLabelText("Idade mínima"), "15");
    await user.type(screen.getByLabelText("Idade máxima"), "18");
    fireEvent.change(screen.getByLabelText("Abertura das inscrições"), { target: { value: "2030-01-01T08:00" } });
    fireEvent.change(screen.getByLabelText("Encerramento das inscrições"), { target: { value: "2030-02-01T08:00" } });
    const save = screen.getByRole("button", { name: "Salvar alterações" });
    expect((save as HTMLButtonElement).disabled).toBe(false);
    await user.click(save);
    expect((screen.getByRole("button", { name: "Salvando..." }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Salvando..." }));
    expect(mockedFetch).toHaveBeenCalledTimes(3);
    resolveSave?.(json(configured, 201));
    expect(await screen.findByRole("button", { name: "Editar configuração" })).toBeTruthy();
    expect(screen.getByText("Capacidade:").parentElement?.textContent).toBe("Capacidade: 30");
    expect(mockedFetch).toHaveBeenLastCalledWith(
      "/encontros/37/workspace/inscricoes/configuracao/",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("preserva draft no erro e cancelar restaura o persistido", async () => {
    load(configured);
    const user = userEvent.setup();
    render(<EncounterRegistrationConfigCard encontroId="37" />);
    await user.click(await screen.findByRole("button", { name: "Editar configuração" }));
    const capacidade = screen.getByLabelText("Capacidade");
    await user.clear(capacidade);
    await user.type(capacidade, "31");
    mockedFetch.mockResolvedValueOnce(json({ capacidade: ["Valor inválido."] }, 400));
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect((screen.getByLabelText("Capacidade") as HTMLInputElement).value).toBe("31");
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByLabelText("Capacidade")).toBeNull();
    expect(screen.getByText("Capacidade:").parentElement?.textContent).toBe("Capacidade: 30");
  });

  it("edita por PATCH e limpa dirty após sucesso", async () => {
    load(configured);
    const user = userEvent.setup();
    render(<EncounterRegistrationConfigCard encontroId="37" />);
    await user.click(await screen.findByRole("button", { name: "Editar configuração" }));
    const capacidade = screen.getByLabelText("Capacidade");
    await user.clear(capacidade);
    await user.type(capacidade, "40");
    mockedFetch.mockResolvedValueOnce(json({ ...configured, capacidade: 40 }));
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));
    await waitFor(() => expect(screen.getByText("40")).toBeTruthy());
    expect(mockedFetch).toHaveBeenLastCalledWith(
      "/encontros/37/workspace/inscricoes/configuracao/",
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("mostra status e copia link navegável da origem atual", async () => {
    load(configured);
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    render(<EncounterRegistrationConfigCard encontroId="37" />);
    expect(await screen.findByText("Inscrições abertas")).toBeTruthy();
    expect(screen.getByText("15 a 18 anos")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Copiar link" }));
    expect(writeText).toHaveBeenCalledWith(
      `${window.location.origin}/inscricoes/${configured.public_id}`,
    );
  });
});
