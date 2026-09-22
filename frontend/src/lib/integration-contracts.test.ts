import { describe, expect, it } from "vitest";

import {
  appendUniqueById,
  buildAlpinistaCreatePayload,
  buildAlpinistaUpdatePayload,
  buildPaginatedPath,
  paginationControls,
  readUnpaginatedCollection,
  startPaginatedSearch,
  type AlpinistaFormValues,
  type PaginatedResponse,
} from "./integration-contracts";

describe("queries aceitas pela API de Alpinistas", () => {
  it("não adiciona cache-buster à listagem", () => {
    expect(buildPaginatedPath("/alpinistas/", {}, 1)).toBe("/alpinistas/");
  });

  it("preserva search e uma página legítima", () => {
    const path = buildPaginatedPath("/alpinistas/", { search: "Ana Maria" }, 2);
    expect(path).toBe("/alpinistas/?search=Ana+Maria&page=2");
    expect(path).not.toContain("t=");
  });

  it("preserva o filtro pendente ao alcançar a página 2", () => {
    expect(buildPaginatedPath("/alpinistas/", { status: "pendente" }, 2))
      .toBe("/alpinistas/?status=pendente&page=2");
  });

  it("preserva busca ativa da equipe ao trocar de página", () => {
    expect(buildPaginatedPath(
      "/alpinistas/",
      { search: "João", status: "ativo" },
      3,
    )).toBe("/alpinistas/?search=Jo%C3%A3o&status=ativo&page=3");
  });

  it("reinicia na página 1 quando uma nova busca começa", () => {
    expect(startPaginatedSearch("novo termo")).toEqual({
      search: "novo termo",
      page: 1,
    });
  });
});

describe("payload de Alpinista", () => {
  const values: AlpinistaFormValues = {
    nome: "Pessoa de teste",
    email: "pessoa@example.test",
    telefone: "61999999999",
    cpf: "",
    dataNascimento: "",
    endereco: "",
    nomePai: "",
    telefonePai: "",
    nomeMae: "",
    telefoneMae: "",
    restricaoSaude: "",
    medicacao: "",
    conheciaEscalada: "",
    grupo: "",
    status: "ativo",
    is_neurodivergente: false,
    tipo_neurodivergente: "",
    batizado: "",
    primeira_comunhao: "",
    crismado: "",
  };

  it("omite status e CPF vazio no create sem remover os demais campos", () => {
    const payload = buildAlpinistaCreatePayload(values);
    expect(payload).toEqual({
      nome: "Pessoa de teste",
      email: "pessoa@example.test",
      telefone: "61999999999",
      is_neurodivergente: false,
    });
    expect(payload.status).toBeUndefined();
  });

  it("não envia e-mail ou telefone vazios na criação", () => {
    expect(() => buildAlpinistaCreatePayload({ ...values, email: " " })).toThrow(/e-mail/);
    expect(() => buildAlpinistaCreatePayload({ ...values, telefone: "" })).toThrow(/telefone/);
  });

  it("preserva o status no update existente", () => {
    const payload = buildAlpinistaUpdatePayload(values);
    expect(payload.status).toBe("ativo");
  });

  it("envia CPF formatado ao backend sem duplicar sua validação", () => {
    expect(buildAlpinistaCreatePayload({ ...values, cpf: "123.456.789-09" }).cpf)
      .toBe("123.456.789-09");
  });

  it("remove CPF, data e textos opcionais com null explícito no PATCH", () => {
    const payload = buildAlpinistaUpdatePayload(values);
    expect(payload.cpf).toBeNull();
    expect(payload.dataNascimento).toBeNull();
    expect(payload.endereco).toBeNull();
    expect(payload.nomePai).toBeNull();
    expect(payload.restricaoSaude).toBeNull();
  });

  it("mantém data ISO sem construir Date e salva campos preenchidos", () => {
    const payload = buildAlpinistaUpdatePayload({
      ...values,
      dataNascimento: "2004-05-06",
      endereco: "Rua de teste",
    });
    expect(payload.dataNascimento).toBe("2004-05-06");
    expect(payload.endereco).toBe("Rua de teste");
  });

  it("desmarcar neurodivergência limpa o tipo antigo", () => {
    const payload = buildAlpinistaUpdatePayload({
      ...values,
      is_neurodivergente: false,
      tipo_neurodivergente: "Valor antigo",
    });
    expect(payload.is_neurodivergente).toBe(false);
    expect(payload.tipo_neurodivergente).toBeNull();
  });

  it("preserva sacramentos false e não confunde não informado com não", () => {
    const payload = buildAlpinistaUpdatePayload({
      ...values,
      batizado: "false",
      crismado: "",
    });
    expect(payload.batizado).toBe(false);
    expect(payload.crismado).toBeNull();
  });

  it("não copia campos read-only ou desconhecidos para o payload", () => {
    const source = { ...values, id: 9, idade_atual: 20, uiOnly: "x" };
    const payload = buildAlpinistaCreatePayload(source);
    expect(payload.id).toBeUndefined();
    expect(payload.idade_atual).toBeUndefined();
    expect(payload.uiOnly).toBeUndefined();
  });
});

describe("paginação DRF", () => {
  const page: PaginatedResponse<{ id: number }> = {
    count: 25,
    next: "/encontros/?page=2",
    previous: null,
    results: [{ id: 1 }, { id: 2 }],
  };

  it("não confunde count com o tamanho da página", () => {
    expect(paginationControls(page)).toEqual({
      total: 25,
      hasNext: true,
      hasPrevious: false,
    });
    expect(page.results).toHaveLength(2);
  });

  it("constrói explicitamente as páginas 1 e 2 de Encontros", () => {
    expect(buildPaginatedPath("/encontros/", {}, 1)).toBe("/encontros/");
    expect(buildPaginatedPath("/encontros/", {}, 2)).toBe("/encontros/?page=2");
  });

  it("representa página intermediária com anterior e próxima", () => {
    expect(paginationControls({
      ...page,
      next: "/encontros/?page=3",
      previous: "/encontros/",
    })).toMatchObject({ hasNext: true, hasPrevious: true });
  });

  it("acrescenta página 2 sem duplicar itens existentes", () => {
    const selectedIds = [1];
    const results = appendUniqueById(
      [{ id: 1 }, { id: 2 }],
      [{ id: 2 }, { id: 3 }],
    );
    expect(results).toEqual([{ id: 1 }, { id: 2 }, { id: 3 }]);
    expect(selectedIds).toEqual([1]);
  });
});

describe("coleções não paginadas do DRF", () => {
  it("consome funções e participações como lista direta", async () => {
    const items = [{ id: 1 }, { id: 2 }];
    await expect(readUnpaginatedCollection<{ id: number }>(
      Response.json(items),
    )).resolves.toEqual(items);
  });

  it("rejeita envelope paginado em endpoint não paginado", async () => {
    await expect(readUnpaginatedCollection(
      Response.json({ count: 1, next: null, previous: null, results: [{ id: 1 }] }),
    )).rejects.toThrow(/lista direta/);
  });
});
