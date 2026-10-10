import { describe, expect, it } from "vitest";

import { isAllowedPreEncounterRequest } from "./pre-encounter-bff";
import { validateProxyPath } from "./sia-proxy";
import {
  parsePreEncounterContextCapabilities,
  parsePreEncounterItemCapabilities,
  parsePreEncounterPersonLookup,
  parsePreEncounterRegistrationLookup,
} from "../pre-encounter-contract";

const base = ["encontros", "12", "pre-encontro"] as const;

describe("allowlist BFF do Pré-Encontro", () => {
  it.each([
    ["GET", [...base, "atendimentos"]],
    ["GET", [...base, "capabilities"]],
    ["GET", [...base, "lookups", "inscricoes"]],
    ["GET", [...base, "lookups", "pessoas"]],
    ["GET", [...base, "atendimentos", "busca"]],
    ["GET", [...base, "atendimentos", "34"]],
    ["POST", [...base, "check-in"]],
    ["POST", [...base, "atendimentos", "34", "regularizar"]],
    ["PUT", [...base, "atendimentos", "34", "pagamento"]],
    ["GET", [...base, "atendimentos", "34", "cuidados"]],
    ["POST", [...base, "atendimentos", "34", "cuidados", "conferir"]],
    ["GET", [...base, "atendimentos", "34", "foto"]],
    ["GET", [...base, "atendimentos", "34", "regularizacao", "inscricoes"]],
    ["GET", [...base, "atendimentos", "34", "regularizacao", "pessoas"]],
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

  it.each([
    [[...base, "lookups", "inscricoes"]],
    [[...base, "lookups", "pessoas"]],
    [[...base, "atendimentos", "34", "regularizacao", "inscricoes"]],
    [[...base, "atendimentos", "34", "regularizacao", "pessoas"]],
  ])("permite somente GET no lookup %j", (path) => {
    expect(isAllowedPreEncounterRequest("GET", path)).toBe(true);
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      expect(isAllowedPreEncounterRequest(method, path)).toBe(false);
    }
    expect(isAllowedPreEncounterRequest("GET", [...path, "extra"])).toBe(false);
  });

  it("preserva IDs canônicos nos lookups paginados", () => {
    const registrations = parsePreEncounterRegistrationLookup({
      count: 1,
      next: null,
      previous: null,
      results: [{
        inscricao_id: 31,
        identificador: "123e4567-e89b-12d3-a456-426614174000",
        nome: "Inscrita",
        data_nascimento: "2010-01-01",
        cpf_mascarado: "***.***.***-25",
        telefone_mascarado: "*******0000",
      }],
    });
    const people = parsePreEncounterPersonLookup({
      count: 1,
      next: null,
      previous: null,
      results: [{
        pessoa_id: 47,
        nome: "Pessoa",
        data_nascimento: null,
        cpf_mascarado: null,
        telefone_mascarado: null,
      }],
    });

    expect(registrations.results[0].inscricao_id).toBe(31);
    expect(people.results[0].pessoa_id).toBe(47);
    expect("alpinista_id" in people.results[0]).toBe(false);
  });
});
