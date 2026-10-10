import { describe, expect, it } from "vitest";

import { isAllowedPreEncounterRequest } from "./pre-encounter-bff";
import { validateProxyPath } from "./sia-proxy";

const base = ["encontros", "12", "pre-encontro"] as const;

describe("allowlist BFF do Pré-Encontro", () => {
  it.each([
    ["GET", [...base, "atendimentos"]],
    ["GET", [...base, "atendimentos", "busca"]],
    ["GET", [...base, "atendimentos", "34"]],
    ["POST", [...base, "check-in"]],
    ["POST", [...base, "atendimentos", "34", "regularizar"]],
    ["PUT", [...base, "atendimentos", "34", "pagamento"]],
    ["GET", [...base, "atendimentos", "34", "cuidados"]],
    ["POST", [...base, "atendimentos", "34", "cuidados", "conferir"]],
    ["GET", [...base, "atendimentos", "34", "foto"]],
    ["PUT", [...base, "atendimentos", "34", "foto"]],
    ["POST", [...base, "atendimentos", "34", "decisao-vaga"]],
    ["POST", [...base, "capacidade"]],
  ])("permite %s %j", (method, path) => {
    expect(isAllowedPreEncounterRequest(method, path)).toBe(true);
    expect(() => validateProxyPath(path, new URLSearchParams(), method)).not.toThrow();
  });

  it.each([
    ["DELETE", [...base, "atendimentos", "34"]],
    ["POST", [...base, "atendimentos"]],
    ["PATCH", [...base, "atendimentos", "34", "pagamento"]],
    ["GET", [...base, "atendimentos", "34", "cuidados", "extra"]],
    ["GET", [...base, "atendimentos", "../34"]],
    ["GET", ["https://evil.example"]],
  ])("nega %s %j", (method, path) => {
    expect(isAllowedPreEncounterRequest(method, path)).toBe(false);
    expect(() => validateProxyPath(path, new URLSearchParams(), method)).toThrow();
  });

  it("não transforma a raiz genérica em rota de Pré-Encontro", () => {
    expect(isAllowedPreEncounterRequest("GET", ["encontros", "12", "pre-encontro"])).toBe(false);
    expect(isAllowedPreEncounterRequest("GET", ["api", "sia", "encontros"])).toBe(false);
  });
});
