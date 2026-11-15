import { describe, expect, it } from "vitest";
import { isAllowedEncounterTeamRequest as allowed } from "./encounter-team-bff";

describe("BFF de equipes", () => {
  it("permite apenas consulta exata", () => {
    expect(allowed("GET", ["equipes-encontros"], new URLSearchParams("encontro=1"))).toBe(true);
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) expect(allowed(method, ["equipes-encontros"], new URLSearchParams("encontro=1"))).toBe(false);
    for (const path of [["equipes-encontros", "1"], ["equipes-encontros", "roles"], []]) expect(allowed("GET", path, new URLSearchParams("encontro=1"))).toBe(false);
    for (const query of ["", "encontro=0", "encontro=-1", "encontro=abc", "encontro=01", "encontro=1&encontro=2", "encontro=1&outro=2"]) expect(allowed("GET", ["equipes-encontros"], new URLSearchParams(query))).toBe(false);
  });
});
