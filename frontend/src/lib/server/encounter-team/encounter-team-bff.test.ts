import { describe, expect, it } from "vitest";
import { isAllowedEncounterTeamRequest as allowed } from "./encounter-team-bff";

describe("BFF de equipes", () => {
  it("permite somente o contrato GE-2A", () => {
    expect(allowed("POST", ["trabalhos-encontros"])).toBe(true);
    expect(allowed("POST", ["convites-encontros", "1", "responder-trabalho"])).toBe(true);
    for (const method of ["GET", "PUT", "PATCH", "DELETE"]) expect(allowed(method, ["trabalhos-encontros"])).toBe(false);
    for (const action of ["alocar", "realocar", "desalocar"]) expect(allowed("POST", ["trabalhos-encontros", "1", action])).toBe(true);
    expect(allowed("GET", ["convites-encontros"], new URLSearchParams("encontro=1&finalidade=trabalhar&page=2"))).toBe(true);
    expect(allowed("POST", ["convites-encontros"])).toBe(true);
    expect(allowed("GET", ["encontros", "1", "modelo-equipes"])).toBe(true);
    expect(allowed("POST", ["encontros", "1", "modelo-equipes"])).toBe(true);
    expect(allowed("POST", ["encontros", "1", "preparar-equipes"])).toBe(true);
    expect(allowed("GET", ["alpinistas", "seletor-trabalho"], new URLSearchParams("search=Ana&page=1&ordering=-nome"))).toBe(true);
    for (const method of ["PUT", "PATCH", "DELETE"]) expect(allowed(method, ["convites-encontros"])).toBe(false);
    for (const path of [["equipes-encontros"], ["trabalhos-encontros"], ["convites-encontros", "1", "responder"], ["encontros", "..", "modelo-equipes"]]) expect(allowed("GET", path)).toBe(false);
    for (const query of ["", "encontro=0&finalidade=trabalhar", "encontro=1&finalidade=participar", "encontro=1&finalidade=trabalhar&encontro=2", "encontro=1&finalidade=trabalhar&outro=2"]) expect(allowed("GET", ["convites-encontros"], new URLSearchParams(query))).toBe(false);
  });
});

it("restringe ids, métodos, caminhos e consultas das ações", () => {
  for (const action of ["alocar", "realocar", "desalocar"]) {
    for (const id of ["0", "-1", "abc", "1.5", ""]) expect(allowed("POST", ["trabalhos-encontros", id, action])).toBe(false);
    for (const method of ["GET", "PUT", "PATCH", "DELETE"]) expect(allowed(method, ["trabalhos-encontros", "1", action])).toBe(false);
    for (const query of ["x=1", "x=1&x=2"]) expect(allowed("POST", ["trabalhos-encontros", "1", action], new URLSearchParams(query))).toBe(false);
    expect(allowed("POST", ["trabalhos-encontros", "1", action, "extra"])).toBe(false);
  }
  for (const action of ["retirar", "substituir", "resultado"]) expect(allowed("POST", ["trabalhos-encontros", "1", action])).toBe(false);
  expect(allowed("GET", ["trabalhos-encontros", "1"])).toBe(false);
});
