import { describe, expect, it } from "vitest";

import {
  appendUniqueById,
  buildAlpinistaFormEntries,
  buildPaginatedPath,
  paginationControls,
  startPaginatedSearch,
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
  const values = {
    nome: "Pessoa de teste",
    email: "pessoa@example.test",
    telefone: "61999999999",
    status: "ativo",
    is_neurodivergente: false,
    tipo_neurodivergente: "",
  };

  it("omite status no create sem remover os demais campos", () => {
    const payload = Object.fromEntries(buildAlpinistaFormEntries(values, "create"));
    expect(payload).toEqual({
      nome: "Pessoa de teste",
      email: "pessoa@example.test",
      telefone: "61999999999",
      is_neurodivergente: "false",
    });
    expect(payload.status).toBeUndefined();
  });

  it("preserva o status no update existente", () => {
    const payload = Object.fromEntries(buildAlpinistaFormEntries(values, "update"));
    expect(payload.status).toBe("ativo");
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
