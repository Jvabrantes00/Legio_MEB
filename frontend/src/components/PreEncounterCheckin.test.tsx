// @vitest-environment jsdom

import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { siaFetchMock, toastSuccess, toastError } = vi.hoisted(() => ({
  siaFetchMock: vi.fn(), toastSuccess: vi.fn(), toastError: vi.fn(),
}));

vi.mock("../lib/sia-api", () => ({ siaFetch: siaFetchMock }));
vi.mock("react-hot-toast", () => ({ default: { success: toastSuccess, error: toastError } }));

import { PreEncounterCheckin } from "./PreEncounterCheckin";

const contextCapabilities = {
  pre_encontro_configurado: true,
  consultar_operacao: true,
  registrar_checkin: true,
  aumentar_capacidade: false,
  configurar_pre_encontro: false,
};
const item = {
  id: 7, identificacao: "Pessoa Exemplo", origem: "inscricao", presente: true,
  registrado_em: "2030-06-01T12:00:00-03:00", pagamento: "pendente",
  aptidao: { situacao: "apto", motivo: "Apto conforme projeção do servidor" },
  situacao_vaga: null, possui_foto: false, possui_dados_cuidado: true, cuidado_conferido: false,
};
const fullCapabilities = {
  regularizar: true, registrar_pagamento: true, consultar_cuidados: true,
  conferir_cuidados: true, visualizar_foto: true, alterar_foto: true, associar_foto_pessoa: false, decidir_vaga: true,
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function page(results = [item], next: string | null = null, previous: string | null = null) {
  return { count: results.length, next, previous, results };
}

function detail(overrides: Record<string, unknown> = {}) {
  return { ...item, pessoa_id: null, inscricao_id: 3, capabilities: fullCapabilities, ...overrides };
}

function defaultApi(path: string, init?: RequestInit) {
  if (path.endsWith("/atendimentos/?page=1")) return Promise.resolve(json(page()));
  if (path.endsWith("/atendimentos/7/")) return Promise.resolve(json(detail()));
  throw new Error(`Request inesperado: ${init?.method ?? "GET"} ${path}`);
}

beforeEach(() => {
  siaFetchMock.mockImplementation(defaultApi);
  vi.stubGlobal("confirm", vi.fn(() => true));
  Object.defineProperty(URL, "createObjectURL", { value: vi.fn(() => "blob:foto"), configurable: true });
  Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
});

afterEach(() => {
  cleanup(); vi.clearAllMocks(); vi.unstubAllGlobals();
});

describe("workspace operacional do Pré-Encontro", () => {
  it("renderiza lista, indicadores discretos e paginação real", async () => {
    siaFetchMock.mockResolvedValueOnce(json(page([item], "?page=2")));
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    expect((await screen.findAllByText("Pessoa Exemplo")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pendente").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "Próxima página" }));
    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledWith(expect.stringContaining("page=2")));
  });

  it("busca e aplica filtros sem confundir busca com primeira página", async () => {
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await screen.findAllByText("Pessoa Exemplo");
    await user.type(screen.getByLabelText("Buscar atendimento"), "Pessoa");
    siaFetchMock.mockResolvedValueOnce(json(page()));
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledWith(expect.stringContaining("atendimentos/busca/?page=1&q=Pessoa")));
    expect(screen.getByText(/Limpe a busca para aplicar filtros/)).toBeTruthy();
  });

  it("envia filtros operacionais canônicos na lista paginada", async () => {
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await screen.findAllByText("Pessoa Exemplo");
    siaFetchMock.mockResolvedValueOnce(json(page()));
    await user.selectOptions(screen.getByLabelText("Pagamento"), "isento");
    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledWith(expect.stringContaining("pagamento=isento")));
  });

  it("abre painel responsivo e apresenta aptidão do servidor sem transformar pendências em bloqueio", async () => {
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await user.click((await screen.findAllByText("Pessoa Exemplo"))[0]);
    const panel = await screen.findByRole("complementary", { name: "Painel do atendimento" });
    expect(within(panel).getByText("Apto")).toBeTruthy();
    expect(within(panel).getByText(/Pagamento, foto e conferência de cuidados não são impeditivos/)).toBeTruthy();
    expect(within(panel).getByRole("button", { name: "Voltar à lista" })).toBeTruthy();
  });

  it("guia explicitamente as três origens e valida avulso sem exigir CPF", async () => {
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await user.click(screen.getByRole("button", { name: /Novo atendimento/ }));
    expect(screen.getByRole("button", { name: "1. Com inscrição" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "2. Pessoa já cadastrada" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "3. Atendimento avulso" }));
    await user.click(screen.getByRole("button", { name: "Registrar presença" }));
    expect(screen.getByRole("alert").textContent).toContain("nome, data de nascimento e telefone");
    await user.type(screen.getByLabelText("Nome"), "Pessoa Avulsa");
    await user.type(screen.getByLabelText("Data de nascimento"), "2000-01-01");
    await user.type(screen.getByLabelText("Telefone"), "61999999999");
    siaFetchMock.mockResolvedValueOnce(json(detail({ identificacao: "Pessoa Avulsa", inscricao_id: null }), 201));
    siaFetchMock.mockResolvedValueOnce(json(page()));
    await user.click(screen.getByRole("button", { name: "Registrar presença" }));
    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledWith(expect.stringContaining("/check-in/"), expect.objectContaining({ body: expect.stringContaining('"cpf_informado":null') })));
  });

  it("usa somente capabilities para uma experiência restrita a foto", async () => {
    const photoOnly = detail({ inscricao_id: null, possui_dados_cuidado: false, capabilities: {
      regularizar: false, registrar_pagamento: false, consultar_cuidados: false,
      conferir_cuidados: false, visualizar_foto: true, alterar_foto: true, associar_foto_pessoa: false, decidir_vaga: false,
    } });
    siaFetchMock.mockImplementation((path: string) => {
      if (path.endsWith("/atendimentos/?page=1")) return Promise.resolve(json(page()));
      if (path.endsWith("/atendimentos/7/")) return Promise.resolve(json(photoOnly));
      throw new Error(`Request inesperado: ${path}`);
    });
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={{ ...contextCapabilities, registrar_checkin: false }} />);
    await user.click((await screen.findAllByText("Pessoa Exemplo"))[0]);
    expect(await screen.findByText("Foto ainda não adicionada")).toBeTruthy();
    expect(screen.queryByText("Pagamento", { selector: "h4" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ver cuidados" })).toBeNull();
    expect(screen.queryByText("Regularizar atendimento")).toBeNull();
    expect(siaFetchMock.mock.calls.some(([path]) => String(path).endsWith("/cuidados/"))).toBe(false);
  });

  it("destaca disputa e mostra decisões somente quando a capability permite", async () => {
    const pending = { ...item, aptidao: { situacao: "aguardando_decisao_diretoria", motivo: "Disputa excepcional" }, situacao_vaga: "aguardando_decisao_diretoria" };
    siaFetchMock.mockImplementation((path: string, init?: RequestInit) => {
      if (path.endsWith("/atendimentos/?page=1")) return Promise.resolve(json(page([pending])));
      if (path.endsWith("/atendimentos/7/")) return Promise.resolve(json(detail({ ...pending })));
      if (path.endsWith("/decisao-vaga/") && init?.method === "POST") return Promise.resolve(json({ status: "aprovado" }));
      throw new Error(`Request inesperado: ${path}`);
    });
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await user.click((await screen.findAllByText("Pessoa Exemplo"))[0]);
    expect((await screen.findAllByText("Aguardando decisão da Diretoria")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Aprovar" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Não aprovar" })).toBeTruthy();
  });

  it("carrega cuidados sob demanda e registra conferência pelo command específico", async () => {
    const care = {
      possui_alergias: "sim", alergias: "Declarado", possui_restricoes_intolerancias: "nao", restricoes_intolerancias: "",
      usa_medicamentos: "nao", medicamentos: "", horarios_medicamentos: "", observacoes_medicamentos: "",
      neurodivergencia_apoio: "nao", neurodivergencia_condicao: "", necessidades_apoio: "", sensibilidades_desconfortos: "",
      o_que_ajuda: "", outras_informacoes: "", observacoes: "", atualizado_em: "2030-01-01T10:00:00-03:00",
    };
    siaFetchMock.mockImplementation((path: string, init?: RequestInit) => {
      if (path.endsWith("/atendimentos/?page=1")) return Promise.resolve(json(page()));
      if (path.endsWith("/atendimentos/7/")) return Promise.resolve(json(detail()));
      if (path.endsWith("/cuidados/") && !init?.method) return Promise.resolve(json(care));
      if (path.endsWith("/cuidados/conferir/")) return Promise.resolve(json({ conferido: true, conferido_em: "2030-01-01T11:00:00-03:00", ator: "operador", dados_alterados_apos_conferencia: true }));
      throw new Error(`Request inesperado: ${init?.method ?? "GET"} ${path}`);
    });
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await user.click((await screen.findAllByText("Pessoa Exemplo"))[0]);
    await user.click(await screen.findByRole("button", { name: "Ver cuidados" }));
    expect(await screen.findByText(/Informações declaradas/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Marcar como conferido" }));
    expect(await screen.findByText("Dados alterados após a última conferência")).toBeTruthy();
  });

  it("trata conflito sem simular sucesso e mantém lifecycle bloqueado fora da UI", async () => {
    siaFetchMock.mockImplementation((path: string, init?: RequestInit) => {
      if (path.endsWith("/atendimentos/?page=1")) return Promise.resolve(json(page()));
      if (path.endsWith("/atendimentos/7/")) return Promise.resolve(json(detail()));
      if (path.endsWith("/pagamento/") && init?.method === "PUT") return Promise.resolve(json({ detail: "Conflito operacional." }, 409));
      if (path.endsWith("/capabilities/")) return Promise.resolve(json({ ...contextCapabilities, registrar_checkin: false }));
      throw new Error(`Request inesperado: ${path}`);
    });
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await user.click((await screen.findAllByText("Pessoa Exemplo"))[0]);
    await user.click(await screen.findByRole("button", { name: "Isento" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledWith("Conflito operacional."));
    expect(toastSuccess).not.toHaveBeenCalledWith("Pagamento atualizado");
  });

  it("faz preview privado e confirma upload multipart sem usar path de mídia", async () => {
    const withPhoto = detail({ possui_foto: true });
    siaFetchMock.mockImplementation((path: string, init?: RequestInit) => {
      if (path.endsWith("/atendimentos/?page=1")) return Promise.resolve(json(page([{ ...item, possui_foto: true }])));
      if (path.endsWith("/atendimentos/7/")) return Promise.resolve(json(withPhoto));
      if (path.endsWith("/foto/") && !init?.method) return Promise.resolve(new Response("imagem", { headers: { "Content-Type": "image/jpeg" } }));
      if (path.endsWith("/foto/") && init?.method === "PUT") return Promise.resolve(json({ possui_foto: true }));
      throw new Error(`Request inesperado: ${path}`);
    });
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await user.click((await screen.findAllByText("Pessoa Exemplo"))[0]);
    await user.click(await screen.findByRole("button", { name: "Abrir preview privado" }));
    expect(await screen.findByAltText("Foto de Pessoa Exemplo")).toBeTruthy();
    const file = new File(["nova"], "foto.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText("Selecionar ou capturar foto"), file);
    await user.click(screen.getByRole("button", { name: "Substituir foto" }));
    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledWith(
      "/encontros/12/pre-encontro/atendimentos/7/foto/",
      expect.objectContaining({ method: "PUT", body: expect.any(FormData) }),
    ));
    expect(siaFetchMock.mock.calls.some(([path]) => String(path).includes("/media"))).toBe(false);
  });

  it("associa a foto à Pessoa somente pela capability e pelo command explícito", async () => {
    const associavel = detail({
      pessoa_id: 19,
      possui_foto: true,
      capabilities: {
        ...fullCapabilities,
        associar_foto_pessoa: true,
      },
    });
    siaFetchMock.mockImplementation((path: string, init?: RequestInit) => {
      if (path.endsWith("/atendimentos/?page=1")) {
        return Promise.resolve(json(page([{ ...item, possui_foto: true }])));
      }
      if (path.endsWith("/atendimentos/7/")) return Promise.resolve(json(associavel));
      if (path.endsWith("/foto/usar-na-pessoa/") && init?.method === "POST") {
        return Promise.resolve(json({ foto_pessoa_atualizada: true }));
      }
      throw new Error(`Request inesperado: ${init?.method ?? "GET"} ${path}`);
    });
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await user.click((await screen.findAllByText("Pessoa Exemplo"))[0]);
    await user.click(await screen.findByRole("button", { name: "Usar esta como foto da Pessoa" }));

    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledWith(
      "/encontros/12/pre-encontro/atendimentos/7/foto/usar-na-pessoa/",
      expect.objectContaining({ method: "POST", body: "{}" }),
    ));
    expect(toastSuccess).toHaveBeenCalledWith("Foto da Pessoa atualizada");
  });

  it("regulariza Pessoa sem ficha pelo lookup aninhado e preserva linguagem operacional", async () => {
    siaFetchMock.mockImplementation((path: string, init?: RequestInit) => {
      if (path.endsWith("/atendimentos/?page=1")) return Promise.resolve(json(page()));
      if (path.endsWith("/atendimentos/7/")) return Promise.resolve(json(detail({ inscricao_id: null })));
      if (path.includes("/regularizacao/pessoas/")) return Promise.resolve(json({ count: 1, next: null, previous: null, results: [{ pessoa_id: 19, nome: "Pessoa Localizada", data_nascimento: null, cpf_mascarado: null, telefone_mascarado: "*******9999" }] }));
      if (path.endsWith("/regularizar/") && init?.method === "POST") return Promise.resolve(json(detail({ pessoa_id: 19, inscricao_id: null })));
      throw new Error(`Request inesperado: ${path}`);
    });
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    await user.click((await screen.findAllByText("Pessoa Exemplo"))[0]);
    expect(await screen.findByText("Sem inscrição vinculada")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Regularizar atendimento" }));
    await user.click(screen.getByRole("button", { name: "Pessoa" }));
    await user.type(screen.getByLabelText("Buscar vínculo para regularização"), "Pe");
    await user.click(screen.getAllByRole("button", { name: "Buscar" }).at(-1)!);
    await user.click(await screen.findByRole("button", { name: /Pessoa Localizada/ }));
    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith("Atendimento regularizado"));
  });

  it.each([
    [400, "Revise"], [403, "operação"], [404, "não encontrado"], [502, "Falha"],
  ])("apresenta falha HTTP %s sem resultado falso", async (status) => {
    siaFetchMock.mockResolvedValueOnce(json({ detail: `Falha ${status}` }, status));
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={contextCapabilities} />);
    expect(await screen.findByText(`Falha ${status}`)).toBeTruthy();
    expect(toastSuccess).not.toHaveBeenCalled();
  });

  it("apresenta lifecycle/capability bloqueado e não busca dados operacionais", () => {
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={{ ...contextCapabilities, consultar_operacao: false, registrar_checkin: false }} />);
    expect(screen.getByText("A operação não está disponível neste contexto.")).toBeTruthy();
    expect(siaFetchMock).not.toHaveBeenCalled();
  });

  it("mostra empty state e configuração apenas pela capability sem buscar atendimentos", async () => {
    const user = userEvent.setup();
    const emptyCapabilities = {
      ...contextCapabilities,
      pre_encontro_configurado: false,
      registrar_checkin: false,
      configurar_pre_encontro: true,
    };
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={emptyCapabilities} />);
    expect(screen.getByText("Nenhum Pré-Encontro configurado para este Encontro.")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Configurar Pré-Encontro" }));
    expect(screen.queryByLabelText("Data")).toBeNull();
    expect(screen.getByLabelText("Horário")).toBeTruthy();
    expect(screen.getByLabelText("Local")).toBeTruthy();
    expect(screen.getByLabelText("Observações (opcional)")).toBeTruthy();
    expect(siaFetchMock).not.toHaveBeenCalled();
  });

  it("não mostra configuração sem capability e continua sem request operacional", () => {
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={{
      ...contextCapabilities,
      pre_encontro_configurado: false,
      registrar_checkin: false,
      configurar_pre_encontro: false,
    }} />);
    expect(screen.getByText("Nenhum Pré-Encontro configurado para este Encontro.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Configurar Pré-Encontro" })).toBeNull();
    expect(siaFetchMock).not.toHaveBeenCalled();
  });

  it("configura pelo command, recarrega capabilities e monta a operação somente após sucesso", async () => {
    function Harness() {
      const [caps, setCaps] = useState({
        ...contextCapabilities,
        pre_encontro_configurado: false,
        registrar_checkin: false,
        configurar_pre_encontro: true,
      });
      return <PreEncounterCheckin
        encontroId="12"
        initialCapabilities={caps}
        onReloadCapabilities={async () => setCaps(contextCapabilities)}
      />;
    }
    siaFetchMock.mockImplementation((path: string, init?: RequestInit) => {
      if (path.endsWith("/configurar/") && init?.method === "POST") return Promise.resolve(json({ id: 9 }, 201));
      if (path.endsWith("/atendimentos/?page=1")) return Promise.resolve(json(page()));
      throw new Error(`Request inesperado: ${path}`);
    });
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "Configurar Pré-Encontro" }));
    await user.type(screen.getByLabelText("Horário"), "14:30");
    await user.type(screen.getByLabelText("Local"), "Local do Pré");
    await user.type(screen.getByLabelText("Observações (opcional)"), "Organização");
    await user.click(screen.getByRole("button", { name: "Confirmar configuração" }));
    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledWith(
      "/encontros/12/pre-encontro/configurar/",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"local":"Local do Pré"'),
      }),
    ));
    const commandBody = siaFetchMock.mock.calls.find(
      ([path]) => path === "/encontros/12/pre-encontro/configurar/",
    )?.[1]?.body;
    expect(commandBody).not.toContain('"data"');
    expect(await screen.findByRole("button", { name: /Novo atendimento/ })).toBeTruthy();
    await waitFor(() => expect(siaFetchMock).toHaveBeenCalledWith(
      "/encontros/12/pre-encontro/atendimentos/?page=1",
    ));
  });

  it("mostra erro quando a data canônica ainda não foi definida no Calendário", async () => {
    siaFetchMock.mockResolvedValueOnce(json({
      non_field_errors: ["A data do Pré-Encontro ainda não foi definida no Calendário."],
    }, 400));
    const user = userEvent.setup();
    render(<PreEncounterCheckin encontroId="12" initialCapabilities={{
      ...contextCapabilities,
      pre_encontro_configurado: false,
      registrar_checkin: false,
      configurar_pre_encontro: true,
    }} />);
    await user.click(screen.getByRole("button", { name: "Configurar Pré-Encontro" }));
    await user.type(screen.getByLabelText("Horário"), "14:30");
    await user.type(screen.getByLabelText("Local"), "Local do Pré");
    await user.click(screen.getByRole("button", { name: "Confirmar configuração" }));
    expect(await screen.findByText(
      "A data do Pré-Encontro ainda não foi definida no Calendário.",
    )).toBeTruthy();
  });

  it("distingue falha de capabilities de ausência de autorização e permite tentar novamente", async () => {
    const retry = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<PreEncounterCheckin
      encontroId="12"
      initialCapabilities={null}
      capabilitiesError="Não foi possível carregar o acesso ao Pré-Encontro."
      onReloadCapabilities={retry}
    />);
    expect(screen.getByText("Não foi possível carregar o acesso ao Pré-Encontro.")).toBeTruthy();
    expect(screen.queryByText("A operação não está disponível neste contexto.")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(retry).toHaveBeenCalledOnce();
    expect(siaFetchMock).not.toHaveBeenCalled();
  });
});
