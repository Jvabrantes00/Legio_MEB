export const ENCONTRO_STATUS_CHOICES = [
  { value: "em_agendamento", label: "Em agendamento" },
  { value: "agendado", label: "Agendado" },
] as const;

export const ENCONTRO_TIPO_CHOICES = [
  { value: "Escalada", label: "Escalada" },
  { value: "AVC", label: "AVC" },
  { value: "Esppa", label: "Esppa" },
  { value: "Acampamento", label: "Acampamento" },
] as const;

export type EncontroStatus = typeof ENCONTRO_STATUS_CHOICES[number]["value"];
export type EncontroTipo = typeof ENCONTRO_TIPO_CHOICES[number]["value"];

export interface EncontroFormValues {
  encontro: string;
  tipo: EncontroTipo;
  data_referencia: string;
  data_exato: string;
  local: string;
  status: EncontroStatus;
}

export function buildEncontroCreatePayload(values: EncontroFormValues) {
  return {
    encontro: values.encontro.trim(),
    tipo: values.tipo,
    data_referencia: values.data_referencia,
    data_exato: values.data_exato.trim(),
    local: values.local.trim(),
    status: values.status,
  };
}
