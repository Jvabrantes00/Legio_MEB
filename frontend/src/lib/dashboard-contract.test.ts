import { describe, expect, it } from "vitest";
import { dashboardCards, type DashboardStats } from "./dashboard-contract";

const base: DashboardStats = {
  usuarioLogado: "teste", coordenacoes: [], totalAlpinistas: 123,
  proximosEncontros: [],
};

describe("dashboard usa somente agregados do servidor", () => {
  it("total global não é a primeira página de Alpinistas", () => {
    expect(dashboardCards(base)).toEqual([{ label: "Total de Alpinistas", value: 123 }]);
  });

  it("Diretoria usa as contagens reais da visaoGeral", () => {
    expect(dashboardCards({ ...base, visaoGeral: { ativos: 87, pendentes: 30, inativos: 6 } }))
      .toHaveLength(4);
  });

  it("Fichas usa a contagem do módulo sem estimar a partir de lista", () => {
    expect(dashboardCards({ ...base, moduloFichas: { fichasPendentes: 30, alertaFichas: "Aguardando" } }))
      .toContainEqual({ label: "Fichas pendentes", value: 30 });
  });

  it("propriedades ausentes ou inválidas não viram NaN/undefined", () => {
    expect(dashboardCards({ ...base, visaoGeral: { ativos: Number.NaN, pendentes: 2, inativos: 1 } }))
      .not.toContainEqual({ label: "Membros ativos", value: Number.NaN });
    expect(dashboardCards(base).every((card) => Number.isFinite(card.value))).toBe(true);
  });
});
