import { describe, expect, it } from "vitest";
import {
  buildEncontroCreatePayload,
  ENCONTRO_STATUS_CHOICES,
  ENCONTRO_TIPO_CHOICES,
  type EncontroFormValues,
} from "./encontro-form-contract";

const form: EncontroFormValues = {
  encontro: "Encontro de teste",
  tipo: "Escalada",
  data_referencia: "2026-10-15",
  data_exato: "15 a 18 de outubro",
  local: "Local de teste",
  status: "em_agendamento",
};

describe("formulário de Encontro", () => {
  it("oferece somente os status reais", () => {
    expect(ENCONTRO_STATUS_CHOICES.map((choice) => choice.value))
      .toEqual(["em_agendamento", "agendado"]);
  });

  it("oferece os quatro tipos reais com capitalização canônica", () => {
    expect(ENCONTRO_TIPO_CHOICES.map((choice) => choice.value))
      .toEqual(["Escalada", "AVC", "Esppa", "Acampamento"]);
  });

  it.each(["AVC", "Esppa"] as const)("envia o tipo selecionado %s", (tipo) => {
    expect(buildEncontroCreatePayload({ ...form, tipo }).tipo).toBe(tipo);
  });

  it("envia status válido e preserva a data ISO", () => {
    const payload = buildEncontroCreatePayload({ ...form, status: "agendado" });
    expect(payload.status).toBe("agendado");
    expect(payload.data_referencia).toBe("2026-10-15");
  });
});
