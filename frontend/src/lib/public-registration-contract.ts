import { ensureCsrfToken } from "./sia-api";

export type EncounterType = "Escalada" | "Esppa";

export interface PublicRegistrationEncounter {
  titulo: string;
  tipo: EncounterType;
  inscricoes_abrem_em: string;
  inscricoes_encerram_em: string;
  inscricoes_abertas: boolean;
  primeiro_dia_oficial: string;
}

export interface PublicRegistrationValues {
  nome_completo: string;
  apelido: string;
  data_nascimento: string;
  cpf: string;
  email: string;
  telefone_whatsapp: string;
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  uf: string;
  como_conheceu: string;
  como_conheceu_outro: string;
  batismo: string;
  primeira_comunhao: string;
  crisma: string;
  responsavel_nome: string;
  responsavel_cpf: string;
  responsavel_parentesco: string;
  responsavel_telefone: string;
  responsavel_email: string;
  possui_alergias: string;
  alergias: string;
  possui_restricoes_intolerancias: string;
  restricoes_intolerancias: string;
  usa_medicamentos: string;
  medicamentos: string;
  horarios_medicamentos: string;
  observacoes_medicamentos: string;
  neurodivergencia_apoio: string;
  neurodivergencia_condicao: string;
  necessidades_apoio: string;
  sensibilidades_desconfortos: string;
  o_que_ajuda: string;
  outras_informacoes: string;
  estado_civil: string;
  nome_conjuge: string;
  telefone_conjuge: string;
  nome_referencia: string;
  relacao_referencia: string;
  telefone_referencia: string;
}

export type PublicRegistrationErrors = Partial<Record<keyof PublicRegistrationValues, string>>;

export type PublicRegistrationPayload = {
  dados_declarados: Record<string, string>;
  responsavel?: Record<string, string>;
  dados_cuidado: Record<string, string>;
  dados_esppa?: Record<string, string>;
};

export function emptyPublicRegistrationValues(): PublicRegistrationValues {
  return {
    nome_completo: "", apelido: "", data_nascimento: "", cpf: "", email: "",
    telefone_whatsapp: "", cep: "", logradouro: "", numero: "", complemento: "",
    bairro: "", cidade: "", uf: "", como_conheceu: "", como_conheceu_outro: "",
    batismo: "", primeira_comunhao: "", crisma: "",
    responsavel_nome: "", responsavel_cpf: "", responsavel_parentesco: "",
    responsavel_telefone: "", responsavel_email: "", possui_alergias: "",
    alergias: "", possui_restricoes_intolerancias: "", restricoes_intolerancias: "",
    usa_medicamentos: "", medicamentos: "", horarios_medicamentos: "",
    observacoes_medicamentos: "", neurodivergencia_apoio: "",
    neurodivergencia_condicao: "", necessidades_apoio: "", sensibilidades_desconfortos: "",
    o_que_ajuda: "", outras_informacoes: "", estado_civil: "", nome_conjuge: "",
    telefone_conjuge: "", nome_referencia: "", relacao_referencia: "",
    telefone_referencia: "",
  };
}

type CivilDate = { year: number; month: number; day: number };

export function parseCivilDate(value: string): CivilDate | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const civil = { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) };
  const leap = civil.year % 4 === 0 && (civil.year % 100 !== 0 || civil.year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (civil.month < 1 || civil.month > 12 || civil.day < 1 || civil.day > days[civil.month - 1]) {
    return null;
  }
  return civil;
}

export function ageOnCivilDate(birthDate: string, referenceDate: string): number | null {
  const birth = parseCivilDate(birthDate);
  const reference = parseCivilDate(referenceDate);
  if (!birth || !reference) return null;
  let age = reference.year - birth.year;
  if (reference.month < birth.month || (reference.month === birth.month && reference.day < birth.day)) age -= 1;
  return age >= 0 ? age : null;
}

export function isMinorOnFirstOfficialDay(
  birthDate: string,
  encounter: Pick<PublicRegistrationEncounter, "primeiro_dia_oficial">,
): boolean | null {
  const age = ageOnCivilDate(birthDate, encounter.primeiro_dia_oficial);
  return age === null ? null : age < 18;
}

function required(errors: PublicRegistrationErrors, key: keyof PublicRegistrationValues, value: string, message = "Campo obrigatório.") {
  if (!value.trim()) errors[key] = message;
}

function hasResponsibleContact(values: PublicRegistrationValues) {
  return [values.responsavel_nome, values.responsavel_cpf, values.responsavel_parentesco,
    values.responsavel_telefone, values.responsavel_email].some((value) => value.trim());
}

export function isValidCpf(value: string): boolean {
  const trimmed = value.trim();
  if (!/^(?:\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2})$/.test(trimmed)) return false;
  const digits = trimmed.replace(/\D/g, "");
  if (new Set(digits).size === 1) return false;
  for (const digitIndex of [9, 10]) {
    const weight = digitIndex + 1;
    const total = digits.slice(0, digitIndex).split("").reduce(
      (sum, digit, index) => sum + Number(digit) * (weight - index),
      0,
    );
    const remainder = (total * 10) % 11;
    const expected = remainder === 10 ? 0 : remainder;
    if (expected !== Number(digits[digitIndex])) return false;
  }
  return true;
}

export function normalizeCep(value: string): string | null {
  const trimmed = value.trim();
  if (!/^(?:\d{8}|\d{5}-\d{3})$/.test(trimmed)) return null;
  const digits = trimmed.replace("-", "");
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

export function formatCepInput(value: string): string {
  if (/[^\d-]/.test(value)) return value;
  const digits = value.replace(/-/g, "");
  if (digits.length > 8) return value;
  return digits.length > 5 ? `${digits.slice(0, 5)}-${digits.slice(5)}` : digits;
}

export function validatePublicRegistration(
  values: PublicRegistrationValues,
  encounter: PublicRegistrationEncounter,
): PublicRegistrationErrors {
  const errors: PublicRegistrationErrors = {};
  required(errors, "nome_completo", values.nome_completo);
  required(errors, "data_nascimento", values.data_nascimento);
  const minor = isMinorOnFirstOfficialDay(values.data_nascimento, encounter);
  if (values.data_nascimento && minor === null) errors.data_nascimento = "Informe uma data de nascimento válida.";
  if (!values.email.trim() && !values.telefone_whatsapp.trim()) {
    errors.email = "Informe pelo menos e-mail ou telefone/WhatsApp.";
    errors.telefone_whatsapp = "Informe pelo menos e-mail ou telefone/WhatsApp.";
  }
  if (values.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
    errors.email = "Informe um e-mail válido.";
  }
  if (values.cpf.trim() && !isValidCpf(values.cpf)) errors.cpf = "Informe um CPF válido, com 11 dígitos.";
  required(errors, "cep", values.cep);
  if (values.cep.trim() && normalizeCep(values.cep) === null) {
    errors.cep = "Informe um CEP com 8 dígitos.";
  }
  required(errors, "logradouro", values.logradouro);
  required(errors, "numero", values.numero);
  required(errors, "bairro", values.bairro);
  required(errors, "cidade", values.cidade);
  required(errors, "uf", values.uf);
  if (values.uf.trim() && !/^[A-Za-z]{2}$/.test(values.uf.trim())) errors.uf = "Informe a UF com duas letras.";
  required(errors, "como_conheceu", values.como_conheceu);
  if (values.como_conheceu === "outro") required(errors, "como_conheceu_outro", values.como_conheceu_outro);
  required(errors, "batismo", values.batismo);
  required(errors, "primeira_comunhao", values.primeira_comunhao);
  required(errors, "crisma", values.crisma);

  if (minor === true || (minor === false && hasResponsibleContact(values))) {
    required(errors, "responsavel_nome", values.responsavel_nome);
    required(errors, "responsavel_parentesco", values.responsavel_parentesco);
    required(errors, "responsavel_telefone", values.responsavel_telefone);
    if (minor) required(errors, "responsavel_cpf", values.responsavel_cpf);
    if (values.responsavel_cpf.trim() && !isValidCpf(values.responsavel_cpf)) {
      errors.responsavel_cpf = "Informe um CPF válido, com 11 dígitos.";
    }
    if (values.responsavel_email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.responsavel_email.trim())) {
      errors.responsavel_email = "Informe um e-mail válido.";
    }
  }

  required(errors, "possui_alergias", values.possui_alergias);
  if (values.possui_alergias === "sim") required(errors, "alergias", values.alergias);
  required(errors, "possui_restricoes_intolerancias", values.possui_restricoes_intolerancias);
  if (values.possui_restricoes_intolerancias === "sim") required(errors, "restricoes_intolerancias", values.restricoes_intolerancias);
  required(errors, "usa_medicamentos", values.usa_medicamentos);
  if (values.usa_medicamentos === "sim") {
    required(errors, "medicamentos", values.medicamentos);
    required(errors, "horarios_medicamentos", values.horarios_medicamentos);
  }
  required(errors, "neurodivergencia_apoio", values.neurodivergencia_apoio);

  if (encounter.tipo === "Esppa") {
    required(errors, "estado_civil", values.estado_civil);
    if (values.estado_civil === "casado") {
      required(errors, "nome_conjuge", values.nome_conjuge);
      required(errors, "telefone_conjuge", values.telefone_conjuge);
    } else if (values.estado_civil) {
      required(errors, "nome_referencia", values.nome_referencia);
      required(errors, "relacao_referencia", values.relacao_referencia);
      required(errors, "telefone_referencia", values.telefone_referencia);
    }
  }
  return errors;
}

export function buildPublicRegistrationPayload(
  values: PublicRegistrationValues,
  encounter: PublicRegistrationEncounter,
): PublicRegistrationPayload {
  const dados_declarados = {
    nome_completo: values.nome_completo.trim(), apelido: values.apelido.trim(),
    data_nascimento: values.data_nascimento, cpf: values.cpf.trim(), email: values.email.trim(),
    telefone_whatsapp: values.telefone_whatsapp.trim(), cep: normalizeCep(values.cep) ?? values.cep.trim(),
    logradouro: values.logradouro.trim(), numero: values.numero.trim(), complemento: values.complemento.trim(),
    bairro: values.bairro.trim(), cidade: values.cidade.trim(), uf: values.uf.trim().toUpperCase(),
    como_conheceu: values.como_conheceu,
    como_conheceu_outro: values.como_conheceu === "outro" ? values.como_conheceu_outro.trim() : "",
    batismo: values.batismo, primeira_comunhao: values.primeira_comunhao, crisma: values.crisma,
  };
  const dados_cuidado = {
    possui_alergias: values.possui_alergias, alergias: values.alergias.trim(),
    possui_restricoes_intolerancias: values.possui_restricoes_intolerancias,
    restricoes_intolerancias: values.restricoes_intolerancias.trim(),
    usa_medicamentos: values.usa_medicamentos, medicamentos: values.medicamentos.trim(),
    horarios_medicamentos: values.horarios_medicamentos.trim(),
    observacoes_medicamentos: values.observacoes_medicamentos.trim(),
    neurodivergencia_apoio: values.neurodivergencia_apoio,
    neurodivergencia_condicao: values.neurodivergencia_condicao.trim(),
    necessidades_apoio: values.necessidades_apoio.trim(),
    sensibilidades_desconfortos: values.sensibilidades_desconfortos.trim(),
    o_que_ajuda: values.o_que_ajuda.trim(), outras_informacoes: values.outras_informacoes.trim(),
    observacoes: "",
  };
  const payload: PublicRegistrationPayload = { dados_declarados, dados_cuidado };
  const minor = isMinorOnFirstOfficialDay(values.data_nascimento, encounter);
  if (minor === true || hasResponsibleContact(values)) {
    payload.responsavel = {
      nome_completo: values.responsavel_nome.trim(), cpf: values.responsavel_cpf.trim(),
      parentesco: values.responsavel_parentesco.trim(), telefone_whatsapp: values.responsavel_telefone.trim(),
      email: values.responsavel_email.trim(),
    };
  }
  if (encounter.tipo === "Esppa") {
    payload.dados_esppa = {
      estado_civil: values.estado_civil, nome_conjuge: values.nome_conjuge.trim(),
      telefone_conjuge: values.telefone_conjuge.trim(), nome_referencia: values.nome_referencia.trim(),
      relacao_referencia: values.relacao_referencia, telefone_referencia: values.telefone_referencia.trim(),
    };
  }
  return payload;
}

function isEncounter(value: unknown): value is PublicRegistrationEncounter {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return typeof item.titulo === "string" && (item.tipo === "Escalada" || item.tipo === "Esppa")
    && typeof item.inscricoes_abrem_em === "string" && typeof item.inscricoes_encerram_em === "string"
    && typeof item.inscricoes_abertas === "boolean" && typeof item.primeiro_dia_oficial === "string"
    && parseCivilDate(item.primeiro_dia_oficial) !== null;
}

export async function loadPublicRegistration(publicId: string, signal?: AbortSignal) {
  const response = await fetch(`/api/public/encontros/${encodeURIComponent(publicId)}/inscricao/`, {
    method: "GET", cache: "no-store", credentials: "same-origin", signal,
  });
  if (!response.ok) return { response, encounter: null };
  const body: unknown = await response.json();
  return { response, encounter: isEncounter(body) ? body : null };
}

export async function submitPublicRegistration(
  publicId: string,
  payload: PublicRegistrationPayload,
): Promise<Response> {
  const csrf = await ensureCsrfToken();
  return fetch(`/api/public/encontros/${encodeURIComponent(publicId)}/inscricao/`, {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
}

export function publicSubmissionErrorMessage(status: number): string {
  if (status === 400) return "Revise os dados informados. Se necessário, volte e corrija a ficha.";
  if (status === 404) return "Esta ficha não está mais disponível para inscrição.";
  if (status === 429) return "Muitas tentativas. Aguarde um pouco antes de tentar novamente.";
  return "Não foi possível enviar agora. Tente novamente em alguns instantes.";
}

export type PublicSubmissionResult =
  | { success: true; message: string }
  | { success: false; message: string; status: number | null };

export async function finalizePublicRegistration(
  publicId: string,
  values: PublicRegistrationValues,
  encounter: PublicRegistrationEncounter,
): Promise<PublicSubmissionResult> {
  const response = await submitPublicRegistration(
    publicId,
    buildPublicRegistrationPayload(values, encounter),
  );
  if (!response.ok) {
    return { success: false, message: publicSubmissionErrorMessage(response.status), status: response.status };
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return { success: false, message: publicSubmissionErrorMessage(502), status: 502 };
  }
  if (
    !body
    || typeof body !== "object"
    || typeof (body as Record<string, unknown>).mensagem !== "string"
  ) {
    return { success: false, message: publicSubmissionErrorMessage(502), status: 502 };
  }
  return {
    success: true,
    message: (body as { mensagem: string }).mensagem,
  };
}
