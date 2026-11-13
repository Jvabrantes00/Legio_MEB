// @vitest-environment jsdom

import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EncounterCandidatesPanel } from "./EncounterCandidatesPanel";
import { siaFetch } from "../lib/sia-api";
import type { EncounterWorkspaceCapabilities } from "../lib/encounter-workspace-contract";

vi.mock("../lib/sia-api", () => ({ siaFetch: vi.fn() }));

const mockedFetch = vi.mocked(siaFetch);

const summaryCapabilities: EncounterWorkspaceCapabilities = {
  consultar_resumo: true,
  consultar_encontristas: true,
  consultar_contato: false,
  acessar_pre_encontro: true,
  acessar_equipes: false,
  acessar_formacao: false,
  acessar_agenda: true,
  consultar_inscricoes: false,
  configurar_inscricoes: false,
};

const fullCapabilities: EncounterWorkspaceCapabilities = {
  ...summaryCapabilities,
  consultar_contato: true,
  acessar_equipes: true,
  consultar_inscricoes: true,
  configurar_inscricoes: true,
};

const summaryCandidate = {
  ref: { origem_tipo: "INSCRICAO", origem_id: "2a62fca6-e0cc-4fb4-9728-8ff8be832adc" },
  nome: "Pessoa Exemplo",
  origem: { codigo: "INSCRICAO", label: "Inscrição" },
  situacao: { codigo: "INSCRITO", label: "Inscrito" },
  presenca_pre: false,
  aptidao: null,
  pessoa_id: null,
};

const fullCandidate = {
  ...summaryCandidate,
  telefone: "61999990000",
};

function candidate(name: string, id: string) {
  return {
    ...summaryCandidate,
    ref: { ...summaryCandidate.ref, origem_id: id },
    nome: name,
  };
}

function page(
  results: unknown[] = [summaryCandidate],
  next: string | null = null,
  previous: string | null = null,
) {
  return { count: results.length, next, previous, results };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function deferredResponse() {
  let resolve: (response: Response) => void = () => undefined;
  const promise = new Promise<Response>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
}

describe("consulta canônica de Encontristas", () => {
  beforeEach(() => {
    mockedFetch.mockReset();
  });
  afterEach(() => cleanup());

  it("aplica default deny sem capabilities válidas ou autorizadas", () => {
    const { rerender } = render(
      <EncounterCandidatesPanel encontroId="37" capabilities={null} />,
    );
    expect(screen.getByText(/não está disponível neste contexto/i)).toBeTruthy();
    expect(mockedFetch).not.toHaveBeenCalled();

    rerender(
      <EncounterCandidatesPanel
        encontroId="37"
        capabilities={{ ...summaryCapabilities, consultar_encontristas: false }}
      />,
    );
    expect(screen.getByText(/não está disponível neste contexto/i)).toBeTruthy();
    expect(mockedFetch).not.toHaveBeenCalled();
  });

  it("renderiza summary para Comunicação sem solicitar ou exibir telefone", async () => {
    mockedFetch.mockResolvedValue(json(page([{ ...summaryCandidate, telefone: "61999990000" }])));
    render(
      <EncounterCandidatesPanel encontroId="37" capabilities={summaryCapabilities} />,
    );

    expect(await screen.findByText("Pessoa Exemplo")).toBeTruthy();
    expect(screen.getByLabelText("Buscar por nome")).toBeTruthy();
    expect(screen.queryByText("61999990000")).toBeNull();
    expect(screen.queryByRole("columnheader", { name: "Telefone" })).toBeNull();
  });

  it("renderiza full com telefone somente quando a capability autoriza", async () => {
    mockedFetch.mockResolvedValue(json(page([{ ...summaryCandidate, telefone: "61999990000" }])));
    render(<EncounterCandidatesPanel encontroId="37" capabilities={fullCapabilities} />);

    expect(await screen.findByText("61999990000")).toBeTruthy();
    expect(screen.getByLabelText("Buscar por nome ou telefone")).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Telefone" })).toBeTruthy();
  });

  it("oculta dados ao revogar acesso e não reaproveita a projeção full como summary", async () => {
    mockedFetch
      .mockResolvedValueOnce(json(page([fullCandidate])))
      .mockResolvedValueOnce(json(page([summaryCandidate])));
    const { rerender } = render(
      <EncounterCandidatesPanel encontroId="37" capabilities={fullCapabilities} />,
    );

    expect(await screen.findByText("61999990000")).toBeTruthy();
    rerender(
      <EncounterCandidatesPanel
        encontroId="37"
        capabilities={{ ...fullCapabilities, consultar_encontristas: false }}
      />,
    );
    expect(screen.getByText(/não está disponível neste contexto/i)).toBeTruthy();
    expect(screen.queryByText("61999990000")).toBeNull();
    expect(mockedFetch).toHaveBeenCalledTimes(1);

    rerender(
      <EncounterCandidatesPanel encontroId="37" capabilities={summaryCapabilities} />,
    );
    expect(screen.getByRole("status").textContent).toContain("Carregando");
    expect(screen.queryByText("61999990000")).toBeNull();
    expect(await screen.findByText("Pessoa Exemplo")).toBeTruthy();
    expect(screen.queryByRole("columnheader", { name: "Telefone" })).toBeNull();
    expect(mockedFetch).toHaveBeenNthCalledWith(
      2,
      "/encontros/37/workspace/encontristas/?page=1",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("descarta campos fora da allowlist do contrato", async () => {
    mockedFetch.mockResolvedValue(json(page([{
      ...summaryCandidate,
      cpf: "00000000000",
      email: "privado@example.test",
      data_nascimento: "2000-01-01",
      cuidados: "restrito",
      foto: "/media/privada.jpg",
      storage: "private/key",
    }])));
    render(
      <EncounterCandidatesPanel encontroId="37" capabilities={summaryCapabilities} />,
    );

    expect(await screen.findByText("Pessoa Exemplo")).toBeTruthy();
    for (const forbidden of [
      "00000000000",
      "privado@example.test",
      "2000-01-01",
      "restrito",
      "/media/privada.jpg",
      "private/key",
    ]) {
      expect(screen.queryByText(forbidden)).toBeNull();
    }
  });

  it("envia somente busca e filtros canônicos e reinicia a paginação", async () => {
    mockedFetch.mockImplementation(() => Promise.resolve(json(page([fullCandidate]))));
    const user = userEvent.setup();
    render(<EncounterCandidatesPanel encontroId="37" capabilities={fullCapabilities} />);
    await screen.findByText("Pessoa Exemplo");

    await user.type(screen.getByLabelText("Buscar por nome ou telefone"), "  Pessoa  ");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    await user.selectOptions(screen.getByLabelText("Situação"), "APTO");
    await user.selectOptions(screen.getByLabelText("Origem"), "PESSOA");

    await waitFor(() => expect(mockedFetch).toHaveBeenLastCalledWith(
      "/encontros/37/workspace/encontristas/?page=1&search=Pessoa&situacao=APTO&origem=PESSOA",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    ));
    for (const [path] of mockedFetch.mock.calls) {
      expect(path).toContain("/workspace/encontristas/");
      expect(path).not.toContain("/alpinistas/");
      expect(path).not.toContain("participacoes-encontros");
    }
  });

  it("pagina usando apenas o estado local e os links canônicos como indicadores", async () => {
    mockedFetch
      .mockResolvedValueOnce(json(page([summaryCandidate], "?page=2")))
      .mockResolvedValueOnce(json(page([candidate("Segunda Pessoa", "segunda")], null, "?page=1")));
    const user = userEvent.setup();
    render(
      <EncounterCandidatesPanel encontroId="37" capabilities={summaryCapabilities} />,
    );
    await screen.findByText("Pessoa Exemplo");
    await user.click(screen.getByRole("button", { name: "Próxima página" }));

    expect(await screen.findByText("Segunda Pessoa")).toBeTruthy();
    expect(screen.getByText("Página 2")).toBeTruthy();
    expect(mockedFetch).toHaveBeenLastCalledWith(
      "/encontros/37/workspace/encontristas/?page=2",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("apresenta loading, vazio, erro e retry sem manter resultados obsoletos", async () => {
    const pending = deferredResponse();
    mockedFetch
      .mockReturnValueOnce(pending.promise)
      .mockResolvedValueOnce(json({ detail: "Consulta temporariamente indisponível." }, 502))
      .mockResolvedValueOnce(json(page([])));
    const user = userEvent.setup();
    render(
      <EncounterCandidatesPanel encontroId="37" capabilities={summaryCapabilities} />,
    );
    expect(screen.getByRole("status").textContent).toContain("Carregando");

    await act(async () => {
      pending.resolve(json(page([summaryCandidate], "?page=2")));
      await pending.promise;
    });
    await screen.findByText("Pessoa Exemplo");
    await user.click(screen.getByRole("button", { name: "Próxima página" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Consulta temporariamente indisponível.",
    );
    expect(screen.queryByText("Pessoa Exemplo")).toBeNull();
    expect(screen.queryByRole("button", { name: "Próxima página" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhum Encontrista encontrado.")).toBeTruthy();
  });

  it("ignora resposta antiga recebida depois de uma busca mais recente", async () => {
    const oldSearch = deferredResponse();
    mockedFetch
      .mockResolvedValueOnce(json(page()))
      .mockReturnValueOnce(oldSearch.promise)
      .mockResolvedValueOnce(json(page([candidate("Resultado recente", "recente")])))
      .mockImplementation((path: string) => Promise.reject(
        new Error(`Request inesperado: ${String(path)}`),
      ));
    const user = userEvent.setup();
    render(
      <EncounterCandidatesPanel encontroId="37" capabilities={summaryCapabilities} />,
    );
    await screen.findByText("Pessoa Exemplo");
    expect(mockedFetch).toHaveBeenNthCalledWith(
      1,
      "/encontros/37/workspace/encontristas/?page=1",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    const search = screen.getByLabelText("Buscar por nome");
    await user.type(search, "Primeira");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    await waitFor(() => expect(mockedFetch).toHaveBeenNthCalledWith(
      2,
      "/encontros/37/workspace/encontristas/?page=1&search=Primeira",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    ));
    await user.clear(search);
    await user.type(search, "Segunda");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    expect(await screen.findByText("Resultado recente")).toBeTruthy();
    expect(mockedFetch).toHaveBeenNthCalledWith(
      3,
      "/encontros/37/workspace/encontristas/?page=1&search=Segunda",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(mockedFetch).toHaveBeenCalledTimes(3);
    const firstSearchSignal = mockedFetch.mock.calls[1]?.[1]?.signal;
    expect(firstSearchSignal).toBeInstanceOf(AbortSignal);
    expect(firstSearchSignal?.aborted).toBe(true);

    await act(async () => {
      oldSearch.resolve(json(page([candidate("Resposta antiga", "antiga")])));
      await oldSearch.promise;
    });
    expect(screen.getByText("Resultado recente")).toBeTruthy();
    expect(screen.queryByText("Resposta antiga")).toBeNull();
  });

  it("invalida imediatamente dados e requests ao trocar de Encontro", async () => {
    const oldEncounter = deferredResponse();
    const newEncounter = deferredResponse();
    mockedFetch
      .mockReturnValueOnce(oldEncounter.promise)
      .mockReturnValueOnce(newEncounter.promise)
      .mockImplementation((path: string) => Promise.reject(
        new Error(`Request inesperado: ${String(path)}`),
      ));
    const { rerender } = render(
      <EncounterCandidatesPanel encontroId="37" capabilities={summaryCapabilities} />,
    );
    await waitFor(() => expect(mockedFetch).toHaveBeenNthCalledWith(
      1,
      "/encontros/37/workspace/encontristas/?page=1",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    ));
    rerender(
      <EncounterCandidatesPanel encontroId="38" capabilities={summaryCapabilities} />,
    );
    expect(screen.getByRole("status").textContent).toContain("Carregando");
    expect(screen.queryByText("Pessoa Exemplo")).toBeNull();
    await waitFor(() => expect(mockedFetch).toHaveBeenNthCalledWith(
      2,
      "/encontros/38/workspace/encontristas/?page=1",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    ));
    expect(mockedFetch).toHaveBeenCalledTimes(2);
    const oldEncounterSignal = mockedFetch.mock.calls[0]?.[1]?.signal;
    expect(oldEncounterSignal).toBeInstanceOf(AbortSignal);
    expect(oldEncounterSignal?.aborted).toBe(true);

    await act(async () => {
      newEncounter.resolve(json(page([candidate("Encontro atual", "atual")])));
      await newEncounter.promise;
    });
    expect(await screen.findByText("Encontro atual")).toBeTruthy();

    await act(async () => {
      oldEncounter.resolve(json(page([candidate("Encontro antigo", "antigo")])));
      await oldEncounter.promise;
    });
    expect(screen.queryByText("Encontro antigo")).toBeNull();
    expect(screen.getByText("Encontro atual")).toBeTruthy();
  });

  it("aborta a requisição pendente ao desmontar", async () => {
    const pending = deferredResponse();
    const signals: AbortSignal[] = [];
    mockedFetch.mockImplementation((_path: string, init?: RequestInit) => {
      if (init?.signal instanceof AbortSignal) signals.push(init.signal);
      return pending.promise;
    });
    const { unmount } = render(
      <EncounterCandidatesPanel encontroId="37" capabilities={summaryCapabilities} />,
    );
    await waitFor(() => expect(mockedFetch).toHaveBeenCalledTimes(1));
    unmount();
    expect(signals[0]?.aborted).toBe(true);

    await act(async () => {
      pending.resolve(json(page()));
      await pending.promise;
    });
    expect(screen.queryByText("Pessoa Exemplo")).toBeNull();
  });

  it("não oferece seleção, detalhe ou ações operacionais", async () => {
    mockedFetch.mockResolvedValue(json(page([fullCandidate])));
    render(<EncounterCandidatesPanel encontroId="37" capabilities={fullCapabilities} />);
    await screen.findByText("Pessoa Exemplo");

    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.queryByRole("button", { name: /confirmar/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /remover/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /detalhe/i })).toBeNull();
  });
});
