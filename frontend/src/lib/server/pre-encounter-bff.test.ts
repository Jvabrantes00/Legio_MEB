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
    ["GET", [...base, "fotos", "atendimentos"]],
    ["GET", [...base, "atendimentos"]],
    ["GET", [...base, "capabilities"]],
    ["GET", [...base, "lookups", "inscricoes"]],
    ["GET", [...base, "lookups", "pessoas"]],
    ["GET", [...base, "atendimentos", "busca"]],
    ["GET", [...base, "atendimentos", "34"]],
    ["POST", [...base, "check-in"]],
    ["POST", [...base, "configurar"]],
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

  it("limita a localização para fotografia ao path exato e às queries page/q", () => {
    const path = [...base, "fotos", "atendimentos"];
    for (const query of ["", "page=2", "q=Pessoa", "page=2&q=Pessoa"]) {
      const params = new URLSearchParams(query);
      expect(isAllowedPreEncounterRequest("GET", path, params)).toBe(true);
      expect(() => validateProxyPath(path, params, "GET")).not.toThrow();
    }
    for (const query of ["page=0", "page=-1", "cpf=123", "pagamento=pago", "q=A&q=B"]) {
      const params = new URLSearchParams(query);
      expect(isAllowedPreEncounterRequest("GET", path, params)).toBe(false);
      expect(() => validateProxyPath(path, params, "GET")).toThrow();
    }
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      expect(isAllowedPreEncounterRequest(method, path)).toBe(false);
    }
    expect(isAllowedPreEncounterRequest("GET", [...path, "extra"])).toBe(false);
    expect(isAllowedPreEncounterRequest(
      "GET",
      ["encontros", "../12", "pre-encontro", "fotos", "atendimentos"],
    )).toBe(false);
  });

  it("preserva as queries legítimas da listagem operacional existente", () => {
    const path = [...base, "atendimentos"];
    const params = new URLSearchParams(
      "page=2&presente=true&pagamento=pago&aptidao=apto&situacao_vaga=aprovado",
    );

    expect(isAllowedPreEncounterRequest("GET", path, params)).toBe(true);
    expect(() => validateProxyPath(path, params, "GET")).not.toThrow();
  });

  it("preserva a busca operacional existente com q", () => {
    const path = [...base, "atendimentos", "busca"];
    const params = new URLSearchParams("q=Pessoa");

    expect(isAllowedPreEncounterRequest("GET", path, params)).toBe(true);
    expect(() => validateProxyPath(path, params, "GET")).not.toThrow();
  });

  it.each(["url", "target", "host", "URL", "Target", "HOST"])(
    "mantém o bloqueio global do parâmetro de destino %s nas rotas existentes",
    (key) => {
      const params = new URLSearchParams({ [key]: "https://evil.example" });

      expect(() => validateProxyPath(
        [...base, "atendimentos"],
        params,
        "GET",
      )).toThrow("Parâmetro de destino não permitido.");
    },
  );

  it.each(["POST", "PUT", "PATCH", "DELETE"])(
    "nega %s no endpoint contextual de capabilities",
    (method) => {
      const path = [...base, "capabilities"];
      expect(isAllowedPreEncounterRequest(method, path)).toBe(false);
      expect(() => validateProxyPath(path, new URLSearchParams(), method)).toThrow();
    },
  );

  it.each(["GET", "PUT", "PATCH", "DELETE"])(
    "nega %s no command de configuração inicial",
    (method) => {
      const path = [...base, "configurar"];
      expect(isAllowedPreEncounterRequest(method, path)).toBe(false);
      expect(() => validateProxyPath(path, new URLSearchParams(), method)).toThrow();
    },
  );

  it("nega segmentos extras no command de configuração", () => {
    expect(isAllowedPreEncounterRequest("POST", [...base, "configurar", "extra"])).toBe(false);
  });

  it("valida os dois contratos de capabilities sem expor identidade", () => {
    const contexto = parsePreEncounterContextCapabilities({
      pre_encontro_configurado: false,
      localizar_atendimento_foto: true,
      consultar_operacao: true,
      baixar_pdf_operacional: true,
      consultar_cuidados: true,
      registrar_checkin: false,
      aumentar_capacidade: false,
      configurar_pre_encontro: true,
    });
    const atendimento = parsePreEncounterItemCapabilities({
      regularizar: true,
      registrar_pagamento: false,
      consultar_cuidados: false,
      conferir_cuidados: false,
      visualizar_foto: true,
      alterar_foto: true,
      associar_foto_pessoa: true,
      decidir_vaga: false,
    });

    expect(contexto.consultar_operacao).toBe(true);
    expect(contexto.localizar_atendimento_foto).toBe(true);
    expect(contexto.baixar_pdf_operacional).toBe(true);
    expect(contexto.configurar_pre_encontro).toBe(true);
    expect(atendimento.alterar_foto).toBe(true);
    expect("roles" in contexto).toBe(false);
  });

  it("rejeita capability ausente ou não booleana", () => {
    expect(() => parsePreEncounterContextCapabilities({
      pre_encontro_configurado: false,
      localizar_atendimento_foto: true,
      consultar_operacao: true,
      baixar_pdf_operacional: true,
      consultar_cuidados: true,
      registrar_checkin: "sim",
      aumentar_capacidade: false,
      configurar_pre_encontro: true,
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
