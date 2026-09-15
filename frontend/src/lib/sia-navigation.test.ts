import { describe, expect, it } from "vitest";
import { siaNavigation } from "./sia-navigation";
import type { SiaSession } from "./sia-capabilities";

function session(...roles: string[]): SiaSession {
  return { id: 1, username: "teste", roles, superuser: false };
}

describe("navegação para rotas existentes", () => {
  it("Fichas vê os módulos atuais", () => {
    expect(siaNavigation(session("Fichas")).map((item) => item.rota))
      .toEqual(["/", "/alpinistas", "/encontros"]);
  });

  it("Comunicação não vê dashboard nem páginas inexistentes", () => {
    expect(siaNavigation(session("Comunicação")).map((item) => item.rota))
      .toEqual(["/alpinistas", "/encontros"]);
  });

  it("usuário sem papel mantém sessão sem links de negócio", () => {
    expect(siaNavigation(session())).toEqual([]);
  });

  it("Eventos e Configurações permanecem no backlog, sem links 404", () => {
    expect(siaNavigation(session("Suporte")).map((item) => item.rota))
      .not.toContain("/eventos");
    expect(siaNavigation(session("Suporte")).map((item) => item.rota))
      .not.toContain("/configuracoes");
  });
});
