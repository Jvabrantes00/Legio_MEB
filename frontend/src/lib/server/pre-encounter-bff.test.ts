import { describe, expect, it } from "vitest";

import { isAllowedPreEncounterRequest } from "./pre-encounter-bff";
import { validateProxyPath } from "./sia-proxy";
import {
  parsePreEncounterContextCapabilities,
  parsePreEncounterItemCapabilities,
} from "../pre-encounter-contract";

const base = ["encontros", "12", "pre-encontro"] as const;

describe("allowlist BFF do Pré-Encontro", () => {
  it.each([
    ["GET", [...base, "atendimentos"]],
    ["GET", [...base, "capabilities"]],
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

  it.each(["POST", "PUT", "PATCH", "DELETE"])(
    "nega %s no endpoint contextual de capabilities",
    (method) => {
      const path = [...base, "capabilities"];
      expect(isAllowedPreEncounterRequest(method, path)).toBe(false);
      expect(() => validateProxyPath(path, new URLSearchParams(), method)).toThrow();
    },
  );

  it("valida os dois contratos de capabilities sem expor identidade", () => {
    const contexto = parsePreEncounterContextCapabilities({
      consultar_operacao: true,
      registrar_checkin: false,
      aumentar_capacidade: false,
    });
    const atendimento = parsePreEncounterItemCapabilities({
      regularizar: true,
      registrar_pagamento: false,
      consultar_cuidados: false,
      conferir_cuidados: false,
      visualizar_foto: true,
      alterar_foto: true,
      decidir_vaga: false,
    });

    expect(contexto.consultar_operacao).toBe(true);
    expect(atendimento.alterar_foto).toBe(true);
    expect("roles" in contexto).toBe(false);
  });

  it("rejeita capability ausente ou não booleana", () => {
    expect(() => parsePreEncounterContextCapabilities({
      consultar_operacao: true,
      registrar_checkin: "sim",
      aumentar_capacidade: false,
    })).toThrow();
    expect(() => parsePreEncounterItemCapabilities({})).toThrow();
  });
});
