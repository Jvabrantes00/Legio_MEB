export type PreEncounterContextCapabilities = {
  pre_encontro_configurado: boolean;
  localizar_atendimento_foto: boolean;
  consultar_operacao: boolean;
  baixar_pdf_operacional: boolean;
  consultar_cuidados: boolean;
  registrar_checkin: boolean;
  aumentar_capacidade: boolean;
  configurar_pre_encontro: boolean;
};

export type PreEncounterItemCapabilities = {
  regularizar: boolean;
  registrar_pagamento: boolean;
  consultar_cuidados: boolean;
  conferir_cuidados: boolean;
  visualizar_foto: boolean;
  alterar_foto: boolean;
  associar_foto_pessoa: boolean;
  decidir_vaga: boolean;
};

export type PreEncounterOrigin = "inscricao" | "pessoa" | "avulso";

export type PreEncounterPhotoCapabilities = {
  visualizar_foto: boolean;
  alterar_foto: boolean;
  associar_foto_pessoa: boolean;
};

export type PreEncounterPhotoItem = {
  id: number;
  identificacao: string;
  origem: PreEncounterOrigin;
  possui_foto: boolean;
  capabilities: PreEncounterPhotoCapabilities;
};
export type PreEncounterPaymentStatus = "pendente" | "pago" | "isento";
export type PreEncounterAptitudeStatus =
  | "apto"
  | "nao_apto"
  | "aguardando_decisao_diretoria";
export type PreEncounterVacancyStatus =
  | "aguardando_decisao_diretoria"
  | "aprovado"
  | "nao_aprovado"
  | null;

export type PreEncounterOperationalItem = {
  id: number;
  identificacao: string;
  origem: PreEncounterOrigin;
  presente: boolean;
  registrado_em: string;
  pagamento: PreEncounterPaymentStatus;
  aptidao: { situacao: PreEncounterAptitudeStatus; motivo: string };
  situacao_vaga: PreEncounterVacancyStatus;
  possui_foto: boolean;
  possui_dados_cuidado: boolean;
  cuidado_conferido: boolean;
};

export type PreEncounterDetail = PreEncounterOperationalItem & {
  pessoa_id: number | null;
  inscricao_id: number | null;
  capabilities: PreEncounterItemCapabilities;
};

export type PaginatedPreEncounterItems = PaginatedLookup<PreEncounterOperationalItem>;
export type PaginatedPreEncounterPhotoItems = PaginatedLookup<PreEncounterPhotoItem>;

export type PreEncounterPayment = {
  status: PreEncounterPaymentStatus;
  valor: string | null;
  forma: "" | "pix" | "dinheiro" | "cartao" | "outro";
  pago_em: string | null;
  observacao: string;
};

export type PreEncounterCare = {
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
  observacoes: string;
  atualizado_em: string;
};

export type PreEncounterCareConference = {
  conferido: boolean;
  conferido_em: string;
  ator: string;
  dados_alterados_apos_conferencia: boolean;
};

export type PreEncounterRegistrationLookupItem = {
  inscricao_id: number;
  identificador: string;
  nome: string;
  data_nascimento: string | null;
  cpf_mascarado: string | null;
  telefone_mascarado: string | null;
};

export type PreEncounterPersonLookupItem = {
  pessoa_id: number;
  nome: string;
  data_nascimento: string | null;
  cpf_mascarado: string | null;
  telefone_mascarado: string | null;
};

type PaginatedLookup<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type PaginatedPreEncounterRegistrationLookup =
  PaginatedLookup<PreEncounterRegistrationLookupItem>;
export type PaginatedPreEncounterPersonLookup =
  PaginatedLookup<PreEncounterPersonLookupItem>;

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

function requireNumber(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    throw new Error(`Identificador inválido: ${key}.`);
  }
  return value;
}

function requireString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string") throw new Error(`Campo inválido: ${key}.`);
  return value;
}

function nullableString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  if (value === null) return null;
  if (typeof value === "string") return value;
  throw new Error(`Campo inválido: ${key}.`);
}

function requireEnum<T extends string>(
  record: Record<string, unknown>,
  key: string,
  values: readonly T[],
): T {
  const value = record[key];
  if (typeof value !== "string" || !values.includes(value as T)) {
    throw new Error(`Campo inválido: ${key}.`);
  }
  return value as T;
}

function nullablePositiveNumber(record: Record<string, unknown>, key: string): number | null {
  if (record[key] === null) return null;
  return requireNumber(record, key);
}

function parsePage<T>(value: unknown, parseItem: (item: unknown) => T): PaginatedLookup<T> {
  if (!isRecord(value) || !Array.isArray(value.results)) {
    throw new Error("Lookup paginado inválido.");
  }
  const count = value.count;
  if (typeof count !== "number" || !Number.isInteger(count) || count < 0) {
    throw new Error("Contagem de lookup inválida.");
  }
  const next = nullableString(value, "next");
  const previous = nullableString(value, "previous");
  return { count, next, previous, results: value.results.map(parseItem) };
}

export function parsePreEncounterContextCapabilities(
  value: unknown,
): PreEncounterContextCapabilities {
  if (!isRecord(value)) throw new Error("Capabilities de Pré-Encontro inválidas.");
  return {
    pre_encontro_configurado: requireBoolean(value, "pre_encontro_configurado"),
    localizar_atendimento_foto: requireBoolean(value, "localizar_atendimento_foto"),
    consultar_operacao: requireBoolean(value, "consultar_operacao"),
    baixar_pdf_operacional: requireBoolean(value, "baixar_pdf_operacional"),
    consultar_cuidados: requireBoolean(value, "consultar_cuidados"),
    registrar_checkin: requireBoolean(value, "registrar_checkin"),
    aumentar_capacidade: requireBoolean(value, "aumentar_capacidade"),
    configurar_pre_encontro: requireBoolean(value, "configurar_pre_encontro"),
  };
}

export function parsePreEncounterPhotoCapabilities(
  value: unknown,
): PreEncounterPhotoCapabilities {
  if (!isRecord(value)) throw new Error("Capabilities de fotografia inválidas.");
  return {
    visualizar_foto: requireBoolean(value, "visualizar_foto"),
    alterar_foto: requireBoolean(value, "alterar_foto"),
    associar_foto_pessoa: requireBoolean(value, "associar_foto_pessoa"),
  };
}

export function parsePreEncounterPhotoItem(value: unknown): PreEncounterPhotoItem {
  if (!isRecord(value)) throw new Error("Atendimento para fotografia inválido.");
  return {
    id: requireNumber(value, "id"),
    identificacao: requireString(value, "identificacao"),
    origem: requireEnum(value, "origem", ["inscricao", "pessoa", "avulso"]),
    possui_foto: requireBoolean(value, "possui_foto"),
    capabilities: parsePreEncounterPhotoCapabilities(value.capabilities),
  };
}

export function parsePreEncounterPhotoItems(
  value: unknown,
): PaginatedPreEncounterPhotoItems {
  return parsePage(value, parsePreEncounterPhotoItem);
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
    associar_foto_pessoa: requireBoolean(value, "associar_foto_pessoa"),
    decidir_vaga: requireBoolean(value, "decidir_vaga"),
  };
}

export function parsePreEncounterOperationalItem(value: unknown): PreEncounterOperationalItem {
  if (!isRecord(value)) throw new Error("Atendimento de Pré-Encontro inválido.");
  if (!isRecord(value.aptidao)) throw new Error("Aptidão de Pré-Encontro inválida.");
  const vacancy = value.situacao_vaga;
  if (
    vacancy !== null
    && !["aguardando_decisao_diretoria", "aprovado", "nao_aprovado"].includes(
      String(vacancy),
    )
  ) throw new Error("Situação de vaga inválida.");
  return {
    id: requireNumber(value, "id"),
    identificacao: requireString(value, "identificacao"),
    origem: requireEnum(value, "origem", ["inscricao", "pessoa", "avulso"]),
    presente: requireBoolean(value, "presente"),
    registrado_em: requireString(value, "registrado_em"),
    pagamento: requireEnum(value, "pagamento", ["pendente", "pago", "isento"]),
    aptidao: {
      situacao: requireEnum(value.aptidao, "situacao", [
        "apto", "nao_apto", "aguardando_decisao_diretoria",
      ]),
      motivo: requireString(value.aptidao, "motivo"),
    },
    situacao_vaga: vacancy as PreEncounterVacancyStatus,
    possui_foto: requireBoolean(value, "possui_foto"),
    possui_dados_cuidado: requireBoolean(value, "possui_dados_cuidado"),
    cuidado_conferido: requireBoolean(value, "cuidado_conferido"),
  };
}

export function parsePreEncounterItems(value: unknown): PaginatedPreEncounterItems {
  return parsePage(value, parsePreEncounterOperationalItem);
}

export function parsePreEncounterDetail(value: unknown): PreEncounterDetail {
  if (!isRecord(value)) throw new Error("Detalhe de Pré-Encontro inválido.");
  return {
    ...parsePreEncounterOperationalItem(value),
    pessoa_id: nullablePositiveNumber(value, "pessoa_id"),
    inscricao_id: nullablePositiveNumber(value, "inscricao_id"),
    capabilities: parsePreEncounterItemCapabilities(value.capabilities),
  };
}

export function parsePreEncounterPayment(value: unknown): PreEncounterPayment {
  if (!isRecord(value)) throw new Error("Pagamento de Pré-Encontro inválido.");
  return {
    status: requireEnum(value, "status", ["pendente", "pago", "isento"]),
    valor: nullableString(value, "valor"),
    forma: requireEnum(value, "forma", ["", "pix", "dinheiro", "cartao", "outro"]),
    pago_em: nullableString(value, "pago_em"),
    observacao: requireString(value, "observacao"),
  };
}

export function parsePreEncounterCare(value: unknown): PreEncounterCare {
  if (!isRecord(value)) throw new Error("Dados de cuidado inválidos.");
  return {
    possui_alergias: requireString(value, "possui_alergias"),
    alergias: requireString(value, "alergias"),
    possui_restricoes_intolerancias: requireString(value, "possui_restricoes_intolerancias"),
    restricoes_intolerancias: requireString(value, "restricoes_intolerancias"),
    usa_medicamentos: requireString(value, "usa_medicamentos"),
    medicamentos: requireString(value, "medicamentos"),
    horarios_medicamentos: requireString(value, "horarios_medicamentos"),
    observacoes_medicamentos: requireString(value, "observacoes_medicamentos"),
    neurodivergencia_apoio: requireString(value, "neurodivergencia_apoio"),
    neurodivergencia_condicao: requireString(value, "neurodivergencia_condicao"),
    necessidades_apoio: requireString(value, "necessidades_apoio"),
    sensibilidades_desconfortos: requireString(value, "sensibilidades_desconfortos"),
    o_que_ajuda: requireString(value, "o_que_ajuda"),
    outras_informacoes: requireString(value, "outras_informacoes"),
    observacoes: requireString(value, "observacoes"),
    atualizado_em: requireString(value, "atualizado_em"),
  };
}

export function parsePreEncounterCareConference(value: unknown): PreEncounterCareConference {
  if (!isRecord(value)) throw new Error("Conferência de cuidado inválida.");
  return {
    conferido: requireBoolean(value, "conferido"),
    conferido_em: requireString(value, "conferido_em"),
    ator: requireString(value, "ator"),
    dados_alterados_apos_conferencia: requireBoolean(
      value,
      "dados_alterados_apos_conferencia",
    ),
  };
}

function parseRegistrationLookupItem(value: unknown): PreEncounterRegistrationLookupItem {
  if (!isRecord(value)) throw new Error("Inscrição de lookup inválida.");
  return {
    inscricao_id: requireNumber(value, "inscricao_id"),
    identificador: requireString(value, "identificador"),
    nome: requireString(value, "nome"),
    data_nascimento: nullableString(value, "data_nascimento"),
    cpf_mascarado: nullableString(value, "cpf_mascarado"),
    telefone_mascarado: nullableString(value, "telefone_mascarado"),
  };
}

function parsePersonLookupItem(value: unknown): PreEncounterPersonLookupItem {
  if (!isRecord(value)) throw new Error("Pessoa de lookup inválida.");
  return {
    pessoa_id: requireNumber(value, "pessoa_id"),
    nome: requireString(value, "nome"),
    data_nascimento: nullableString(value, "data_nascimento"),
    cpf_mascarado: nullableString(value, "cpf_mascarado"),
    telefone_mascarado: nullableString(value, "telefone_mascarado"),
  };
}

export function parsePreEncounterRegistrationLookup(
  value: unknown,
): PaginatedPreEncounterRegistrationLookup {
  return parsePage(value, parseRegistrationLookupItem);
}

export function parsePreEncounterPersonLookup(
  value: unknown,
): PaginatedPreEncounterPersonLookup {
  return parsePage(value, parsePersonLookupItem);
}
