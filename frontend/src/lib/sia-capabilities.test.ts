import { describe, expect, it } from "vitest";
import {
  canManageAlpinistas, canManageEncontroParticipacoes, canManageEncontros,
  canViewAlpinistas, canViewDashboard, canViewEncontros,
  canViewFullAlpinista, canViewFullEncontro, isSiaSession,
  type SiaSession,
} from "./sia-capabilities";

function session(...roles: string[]): SiaSession {
  return { id: 1, username: "teste", roles, superuser: false };
}

describe("capacidades visuais alinhadas às permissões backend", () => {
  it.each(["Suporte", "Diretoria", "Fichas"])("%s recebe contratos completos e administração", (role) => {
    const current = session(role);
    expect(canViewAlpinistas(current)).toBe(true);
    expect(canManageAlpinistas(current)).toBe(true);
    expect(canViewFullAlpinista(current)).toBe(true);
    expect(canViewEncontros(current)).toBe(true);
    expect(canManageEncontros(current)).toBe(true);
    expect(canViewFullEncontro(current)).toBe(true);
    expect(canManageEncontroParticipacoes(current)).toBe(true);
    expect(canViewDashboard(current)).toBe(true);
  });

  it("Comunicação lê os dois resumos sem controles de Fichas", () => {
    const current = session("Comunicação");
    expect(canViewAlpinistas(current)).toBe(true);
    expect(canViewEncontros(current)).toBe(true);
    expect(canViewFullAlpinista(current)).toBe(false);
    expect(canViewFullEncontro(current)).toBe(false);
    expect(canManageEncontros(current)).toBe(false);
    expect(canManageEncontroParticipacoes(current)).toBe(false);
    expect(canViewDashboard(current)).toBe(false);
  });

  it.each(["MME", "Formação", "Eventos", "Secretaria", "Ação Social", "Liturgia"])(
    "%s lê resumo de Alpinista sem escrita ou Encontro", (role) => {
      const current = session(role);
      expect(canViewAlpinistas(current)).toBe(true);
      expect(canManageAlpinistas(current)).toBe(false);
      expect(canViewEncontros(current)).toBe(false);
      expect(canViewDashboard(current)).toBe(false);
    },
  );

  it("múltiplos papéis unem capacidades sem criar novo papel", () => {
    expect(canManageEncontros(session("MME", "Fichas"))).toBe(true);
  });

  it("sessão válida sem papel não recebe módulos de negócio", () => {
    const current = session();
    expect(isSiaSession(current)).toBe(true);
    expect(canViewAlpinistas(current)).toBe(false);
    expect(canViewEncontros(current)).toBe(false);
    expect(canViewDashboard(current)).toBe(false);
  });

  it("superuser usa bypass técnico sem fingir papel Suporte", () => {
    const current = { ...session(), superuser: true };
    expect(current.roles).toEqual([]);
    expect(canManageAlpinistas(current)).toBe(true);
    expect(canManageEncontros(current)).toBe(true);
    expect(canViewDashboard(current)).toBe(true);
  });

  it("sessão incompleta não é aceita", () => {
    expect(isSiaSession({ id: 1, roles: [] })).toBe(false);
  });
});
