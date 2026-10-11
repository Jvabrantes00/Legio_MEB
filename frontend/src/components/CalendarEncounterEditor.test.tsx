// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { siaFetchMock } = vi.hoisted(() => ({ siaFetchMock: vi.fn() }));
vi.mock("../lib/sia-api", () => ({ siaFetch: siaFetchMock }));

import { CalendarEncounterEditor } from "./CalendarEncounterEditor";
import type { CalendarEncounterItem, EncounterAgendaItem } from "../lib/institutional-calendar";

const encounter: CalendarEncounterItem = {
  categoria: "ENCONTRO",
  encontro_id: 7,
  titulo: "Escalada 2034",
  tipo: "Escalada",
  status: "em_agendamento",
  calendario_id: 10,
  calendario_versao: 1,
  origem_agenda: "CANONICA",
  confirmacao: "PROVISORIA",
  dias: [],
  agenda: [],
  pode_editar_calendario: true,
};

const baseItem = {
  subtitulo: null,
  confirmacao: null,
  publicavel_externamente: false,
  encontro_id: 7,
  conflito: null,
};

const agenda: EncounterAgendaItem[] = [
  { ...baseItem, id: "DIA_ENCONTRO:1", origem_id: 1, origem: "DIA_ENCONTRO", data: "2034-04-03", titulo: "Primeiro dia", subtitulo: "Escalada 2034", confirmacao: "PROVISORIA", publicavel_externamente: true },
  { ...baseItem, id: "PRE_ENCONTRO:10", origem_id: 10, origem: "PRE_ENCONTRO", data: "2034-03-30", titulo: "Pré-Encontro", confirmacao: "PROVISORIA" },
  { ...baseItem, id: "REUNIAO_PREPARATORIA:20", origem_id: 20, origem: "REUNIAO_PREPARATORIA", data: "2034-03-20", titulo: "1ª Reunião", subtitulo: "Entrega" },
  { ...baseItem, id: "AVALIACAO:30", origem_id: 30, origem: "AVALIACAO", data: "2034-04-10", titulo: "Avaliação" },
];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderEditor(overrides: { onChanged?: () => Promise<void> | void; onCancel?: () => void } = {}) {
  return render(
    <CalendarEncounterEditor
      encounter={encounter}
      agenda={agenda}
      onChanged={overrides.onChanged ?? vi.fn()}
      onCancel={overrides.onCancel ?? vi.fn()}
    />,
  );
}

beforeEach(() => {
  siaFetchMock.mockResolvedValue(json({ avisos_conflito: [] }));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("salvamento agregado do editor do Calendário", () => {
  it("mantém um único save desabilitado e remove persistências por seção", () => {
    renderEditor();
    expect(screen.getAllByRole("button", { name: "Salvar alterações" })).toHaveLength(1);
    expect((screen.getByRole("button", { name: "Salvar alterações" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByRole("button", { name: /Salvar dados|Salvar planejamento|Salvar preparatória|Salvar avaliação/ })).toBeNull();
  });

  it.each([
    ["Nome", "Escalada 2034 atualizada"],
    ["Data 1", "2034-04-04"],
    ["Data do Pré-Encontro", "2034-04-01"],
    ["Complemento da preparatória 1", "Missa"],
    ["Data da avaliação", "2034-04-11"],
  ])("habilita o save quando muda %s sem persistir imediatamente", (label, value) => {
    renderEditor();
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
    expect((screen.getByRole("button", { name: "Salvar alterações" }) as HTMLButtonElement).disabled).toBe(false);
    expect(siaFetchMock).not.toHaveBeenCalled();
  });

  it("acumula Pré-Encontro, dia e Preparatória no draft sem request e envia tudo junto", async () => {
    const user = userEvent.setup();
    renderEditor();

    fireEvent.change(screen.getByLabelText("Data do Pré-Encontro"), { target: { value: "2034-04-01" } });
    fireEvent.change(screen.getByLabelText("Data 1"), { target: { value: "2034-04-04" } });
    fireEvent.change(screen.getByLabelText("Complemento da preparatória 1"), { target: { value: "Missa" } });

    expect(siaFetchMock).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Salvar alterações" }) as HTMLButtonElement).disabled).toBe(false);
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledTimes(1));
    const [path, init] = siaFetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/calendario-institucional/encontros/7/salvar-edicao/");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body))).toMatchObject({
      encontro: "Escalada 2034",
      pre_encontro_data: "2034-04-01",
      dias: [{ ordem: 1, data: "2034-04-04", rotulo: "Primeiro dia" }],
      reunioes: [{ id: 20, ordem: 1, data: "2034-03-20", complemento: "Missa" }],
      avaliacao: { data: "2034-04-10" },
    });
    expect(await screen.findByRole("status")).toHaveProperty("textContent", "Alterações salvas.");
    await waitFor(() => expect((screen.getByRole("button", { name: "Salvar alterações" }) as HTMLButtonElement).disabled).toBe(true));
  });

  it("bloqueia duplo submit enquanto aguarda a resposta", async () => {
    let resolveRequest!: (response: Response) => void;
    siaFetchMock.mockReturnValue(new Promise<Response>((resolve) => { resolveRequest = resolve; }));
    renderEditor();
    fireEvent.change(screen.getByLabelText("Data do Pré-Encontro"), { target: { value: "2034-04-01" } });
    const save = screen.getByRole("button", { name: "Salvar alterações" });
    fireEvent.click(save);
    fireEvent.click(save);
    expect(siaFetchMock).toHaveBeenCalledTimes(1);
    expect((screen.getByRole("button", { name: "Salvando..." }) as HTMLButtonElement).disabled).toBe(true);
    resolveRequest(json({ avisos_conflito: [] }));
    await waitFor(() => expect((screen.getByRole("button", { name: "Salvar alterações" }) as HTMLButtonElement).disabled).toBe(true));
  });

  it("preserva o draft após erro para permitir nova tentativa", async () => {
    siaFetchMock.mockResolvedValueOnce(json({ detail: "Falha controlada" }, 400));
    const user = userEvent.setup();
    renderEditor();
    fireEvent.change(screen.getByLabelText("Data do Pré-Encontro"), { target: { value: "2034-04-01" } });
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Falha controlada");
    expect((screen.getByLabelText("Data do Pré-Encontro") as HTMLInputElement).value).toBe("2034-04-01");
    expect((screen.getByRole("button", { name: "Salvar alterações" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("Cancelar restaura o último estado persistido sem request", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    renderEditor({ onCancel });
    fireEvent.change(screen.getByLabelText("Data do Pré-Encontro"), { target: { value: "2034-04-01" } });
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect((screen.getByLabelText("Data do Pré-Encontro") as HTMLInputElement).value).toBe("2034-03-30");
    expect((screen.getByRole("button", { name: "Salvar alterações" }) as HTMLButtonElement).disabled).toBe(true);
    expect(siaFetchMock).not.toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
