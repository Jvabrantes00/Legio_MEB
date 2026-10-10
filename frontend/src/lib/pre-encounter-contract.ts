export type PreEncounterContextCapabilities = {
  consultar_operacao: boolean;
  registrar_checkin: boolean;
  aumentar_capacidade: boolean;
};

export type PreEncounterItemCapabilities = {
  regularizar: boolean;
  registrar_pagamento: boolean;
  consultar_cuidados: boolean;
  conferir_cuidados: boolean;
  visualizar_foto: boolean;
  alterar_foto: boolean;
  decidir_vaga: boolean;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireBoolean(record: Record<string, unknown>, key: string): boolean {
  const value = record[key];
  if (typeof value !== "boolean") {
    throw new Error(`Capability inválida: ${key}.`);
  }
  return value;
}

export function parsePreEncounterContextCapabilities(
  value: unknown,
): PreEncounterContextCapabilities {
  if (!isRecord(value)) throw new Error("Capabilities de Pré-Encontro inválidas.");
  return {
    consultar_operacao: requireBoolean(value, "consultar_operacao"),
    registrar_checkin: requireBoolean(value, "registrar_checkin"),
    aumentar_capacidade: requireBoolean(value, "aumentar_capacidade"),
  };
}

export function parsePreEncounterItemCapabilities(
  value: unknown,
): PreEncounterItemCapabilities {
  if (!isRecord(value)) throw new Error("Capabilities do atendimento inválidas.");
  return {
    regularizar: requireBoolean(value, "regularizar"),
    registrar_pagamento: requireBoolean(value, "registrar_pagamento"),
    consultar_cuidados: requireBoolean(value, "consultar_cuidados"),
    conferir_cuidados: requireBoolean(value, "conferir_cuidados"),
    visualizar_foto: requireBoolean(value, "visualizar_foto"),
    alterar_foto: requireBoolean(value, "alterar_foto"),
    decidir_vaga: requireBoolean(value, "decidir_vaga"),
  };
}
