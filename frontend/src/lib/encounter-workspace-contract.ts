export type EncounterWorkspaceCandidateOrigin = "INSCRICAO" | "PESSOA" | "AVULSO";
export type EncounterWorkspaceCandidateStatus =
  | "INSCRITO"
  | "CANCELADO"
  | "AGUARDANDO_DECISAO"
  | "APTO"
  | "NAO_APTO"
  | "CONFIRMADO";
export type EncounterWorkspaceAptitude =
  | "apto"
  | "nao_apto"
  | "aguardando_decisao_diretoria"
  | null;

export type EncounterWorkspaceCapabilities = {
  consultar_resumo: boolean;
  consultar_encontristas: boolean;
  consultar_contato: boolean;
  acessar_pre_encontro: boolean;
  acessar_equipes: boolean;
  acessar_formacao: boolean;
  acessar_agenda: boolean;
  consultar_inscricoes: boolean;
  configurar_inscricoes: boolean;
};

export type EncounterRegistrationWindowStatus =
  | "ainda_nao_abriu"
  | "abertas"
  | "encerradas";

export type EncounterRegistrationConfig =
  | {
      configurado: false;
      capacidade: null;
      idade_minima: null;
      idade_maxima: null;
      inscricoes_abrem_em: null;
      inscricoes_encerram_em: null;
      public_id: null;
      status_janela: null;
    }
  | {
      configurado: true;
      capacidade: number;
      idade_minima: number;
      idade_maxima: number;
      inscricoes_abrem_em: string;
      inscricoes_encerram_em: string;
      public_id: string;
      status_janela: EncounterRegistrationWindowStatus;
    };

export type EncounterRegistrationConfigDraft = {
  capacidade: string;
  idade_minima: string;
  idade_maxima: string;
  inscricoes_abrem_em: string;
  inscricoes_encerram_em: string;
};

export type EncounterCandidateSummary = {
  ref: { origem_tipo: EncounterWorkspaceCandidateOrigin; origem_id: string };
  nome: string;
  origem: { codigo: EncounterWorkspaceCandidateOrigin; label: string };
  situacao: { codigo: EncounterWorkspaceCandidateStatus; label: string };
  presenca_pre: boolean;
  aptidao: EncounterWorkspaceAptitude;
  pessoa_id: number | null;
};

export type EncounterCandidateFull = EncounterCandidateSummary & {
  telefone: string;
};

export type EncounterCandidatePage<T extends EncounterCandidateSummary = EncounterCandidateSummary> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type EncounterWorkspaceSummary = {
  encontro: { id: number; nome: string; tipo: string; local: string };
  lifecycle: string;
  agenda: {
    configurada: boolean;
    oficializada: boolean;
    quantidade_itens: number;
    proximo_item: string | null;
    datas_principais: string[];
    pre_encontro_data: string | null;
  };
  encontristas: {
    inscricoes_recebidas: number;
    pendentes: number;
    confirmados: number;
    total_funil: number;
    por_situacao: Record<EncounterWorkspaceCandidateStatus, number>;
  };
  pre_encontro: {
    configurado: boolean;
    data: string | null;
    capacidade: number | null;
    quantidade_checkins: number;
    quantidade_aptos: number;
    quantidade_aguardando_decisao: number;
  };
  equipes: {
    modelo_equipes: "LEGADO" | "CANONICO";
    quantidade_equipes: number;
    quantidade_funcoes: number;
    vagas_estruturais: number | null;
    vagas_preenchidas: number;
  };
  formacao: {
    total_sessoes: number;
    planejadas: number;
    realizadas: number;
    canceladas: number;
  };
  alertas: { codigo: string; mensagem: string }[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(record: Record<string, unknown>, key: string): string {
  if (typeof record[key] !== "string") throw new Error(`Campo inválido: ${key}.`);
  return record[key];
}

function integer(record: Record<string, unknown>, key: string, nullable = false): number | null {
  if (nullable && record[key] === null) return null;
  const value = record[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`Campo inválido: ${key}.`);
  }
  return value;
}

function bool(record: Record<string, unknown>, key: string): boolean {
  if (typeof record[key] !== "boolean") throw new Error(`Campo inválido: ${key}.`);
  return record[key];
}

function nullableText(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  if (value === null) return null;
  if (typeof value === "string") return value;
  throw new Error(`Campo inválido: ${key}.`);
}

const ORIGINS = ["INSCRICAO", "PESSOA", "AVULSO"] as const;
const STATUSES = ["INSCRITO", "CANCELADO", "AGUARDANDO_DECISAO", "APTO", "NAO_APTO", "CONFIRMADO"] as const;
const APTITUDES = ["apto", "nao_apto", "aguardando_decisao_diretoria"] as const;
const REGISTRATION_WINDOW_STATUSES = ["ainda_nao_abriu", "abertas", "encerradas"] as const;

function record(value: unknown, key: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`Campo inválido: ${key}.`);
  return value;
}

function textList(value: unknown, key: string): string[] {
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    throw new Error(`Campo inválido: ${key}.`);
  }
  return value;
}

function enumValue<T extends string>(value: unknown, values: readonly T[], key: string): T {
  if (typeof value !== "string" || !values.includes(value as T)) {
    throw new Error(`Campo inválido: ${key}.`);
  }
  return value as T;
}

export function parseEncounterWorkspaceCapabilities(value: unknown): EncounterWorkspaceCapabilities {
  if (!isRecord(value)) throw new Error("Capabilities do Workspace inválidas.");
  return {
    consultar_resumo: bool(value, "consultar_resumo"),
    consultar_encontristas: bool(value, "consultar_encontristas"),
    consultar_contato: bool(value, "consultar_contato"),
    acessar_pre_encontro: bool(value, "acessar_pre_encontro"),
    acessar_equipes: bool(value, "acessar_equipes"),
    acessar_formacao: bool(value, "acessar_formacao"),
    acessar_agenda: bool(value, "acessar_agenda"),
    consultar_inscricoes: bool(value, "consultar_inscricoes"),
    configurar_inscricoes: bool(value, "configurar_inscricoes"),
  };
}

export function parseEncounterWorkspaceSummary(value: unknown): EncounterWorkspaceSummary {
  const root = record(value, "summary");
  const encontro = record(root.encontro, "encontro");
  const agenda = record(root.agenda, "agenda");
  const encontristas = record(root.encontristas, "encontristas");
  const preEncontro = record(root.pre_encontro, "pre_encontro");
  const equipes = record(root.equipes, "equipes");
  const formacao = record(root.formacao, "formacao");
  const alertas = root.alertas;
  if (!Array.isArray(alertas)) throw new Error("Campo inválido: alertas.");

  const porSituacao = record(encontristas.por_situacao, "por_situacao");
  const situacoes = Object.fromEntries(
    STATUSES.map((status) => [status, integer(porSituacao, status)]),
  ) as Record<EncounterWorkspaceCandidateStatus, number>;

  return {
    encontro: {
      id: integer(encontro, "id") as number,
      nome: text(encontro, "nome"),
      tipo: text(encontro, "tipo"),
      local: text(encontro, "local"),
    },
    lifecycle: text(root, "lifecycle"),
    agenda: {
      configurada: bool(agenda, "configurada"),
      oficializada: bool(agenda, "oficializada"),
      quantidade_itens: integer(agenda, "quantidade_itens") as number,
      proximo_item: nullableText(agenda, "proximo_item"),
      datas_principais: textList(agenda.datas_principais, "datas_principais"),
      pre_encontro_data: nullableText(agenda, "pre_encontro_data"),
    },
    encontristas: {
      inscricoes_recebidas: integer(encontristas, "inscricoes_recebidas") as number,
      pendentes: integer(encontristas, "pendentes") as number,
      confirmados: integer(encontristas, "confirmados") as number,
      total_funil: integer(encontristas, "total_funil") as number,
      por_situacao: situacoes,
    },
    pre_encontro: {
      configurado: bool(preEncontro, "configurado"),
      data: nullableText(preEncontro, "data"),
      capacidade: integer(preEncontro, "capacidade", true),
      quantidade_checkins: integer(preEncontro, "quantidade_checkins") as number,
      quantidade_aptos: integer(preEncontro, "quantidade_aptos") as number,
      quantidade_aguardando_decisao: integer(
        preEncontro,
        "quantidade_aguardando_decisao",
      ) as number,
    },
    equipes: {
      modelo_equipes: enumValue(equipes.modelo_equipes, ["LEGADO", "CANONICO"] as const, "modelo_equipes"),
      quantidade_equipes: integer(equipes, "quantidade_equipes") as number,
      quantidade_funcoes: integer(equipes, "quantidade_funcoes") as number,
      vagas_estruturais: integer(equipes, "vagas_estruturais", true),
      vagas_preenchidas: integer(equipes, "vagas_preenchidas") as number,
    },
    formacao: {
      total_sessoes: integer(formacao, "total_sessoes") as number,
      planejadas: integer(formacao, "planejadas") as number,
      realizadas: integer(formacao, "realizadas") as number,
      canceladas: integer(formacao, "canceladas") as number,
    },
    alertas: alertas.map((item) => {
      const alerta = record(item, "alerta");
      return { codigo: text(alerta, "codigo"), mensagem: text(alerta, "mensagem") };
    }),
  };
}

export function parseEncounterRegistrationConfig(value: unknown): EncounterRegistrationConfig {
  if (!isRecord(value) || typeof value.configurado !== "boolean") {
    throw new Error("Configuração de inscrições inválida.");
  }
  if (!value.configurado) {
    for (const key of [
      "capacidade",
      "idade_minima",
      "idade_maxima",
      "inscricoes_abrem_em",
      "inscricoes_encerram_em",
      "public_id",
      "status_janela",
    ]) {
      if (value[key] !== null) throw new Error(`Campo inválido: ${key}.`);
    }
    return {
      configurado: false,
      capacidade: null,
      idade_minima: null,
      idade_maxima: null,
      inscricoes_abrem_em: null,
      inscricoes_encerram_em: null,
      public_id: null,
      status_janela: null,
    };
  }
  const capacidade = integer(value, "capacidade");
  const idadeMinima = integer(value, "idade_minima");
  const idadeMaxima = integer(value, "idade_maxima");
  if (capacidade === 0) throw new Error("Campo inválido: capacidade.");
  return {
    configurado: true,
    capacidade: capacidade as number,
    idade_minima: idadeMinima as number,
    idade_maxima: idadeMaxima as number,
    inscricoes_abrem_em: text(value, "inscricoes_abrem_em"),
    inscricoes_encerram_em: text(value, "inscricoes_encerram_em"),
    public_id: text(value, "public_id"),
    status_janela: enumValue(
      value.status_janela,
      REGISTRATION_WINDOW_STATUSES,
      "status_janela",
    ),
  };
}

export function parseEncounterCandidateSummary(value: unknown): EncounterCandidateSummary {
  if (!isRecord(value) || !isRecord(value.ref) || !isRecord(value.origem) || !isRecord(value.situacao)) {
    throw new Error("Encontrista inválido.");
  }
  const aptitude = value.aptidao === null
    ? null
    : enumValue(value.aptidao, APTITUDES, "aptidao");
  const pessoaId = integer(value, "pessoa_id", true);
  return {
    ref: {
      origem_tipo: enumValue(value.ref.origem_tipo, ORIGINS, "origem_tipo"),
      origem_id: text(value.ref, "origem_id"),
    },
    nome: text(value, "nome"),
    origem: {
      codigo: enumValue(value.origem.codigo, ORIGINS, "origem.codigo"),
      label: text(value.origem, "label"),
    },
    situacao: {
      codigo: enumValue(value.situacao.codigo, STATUSES, "situacao.codigo"),
      label: text(value.situacao, "label"),
    },
    presenca_pre: bool(value, "presenca_pre"),
    aptidao: aptitude,
    pessoa_id: pessoaId,
  };
}

export function parseEncounterCandidateFull(value: unknown): EncounterCandidateFull {
  if (!isRecord(value)) throw new Error("Encontrista completo inválido.");
  return { ...parseEncounterCandidateSummary(value), telefone: text(value, "telefone") };
}

export function parseEncounterCandidatePage<T extends EncounterCandidateSummary>(
  value: unknown,
  parseItem: (item: unknown) => T = parseEncounterCandidateSummary as (item: unknown) => T,
): EncounterCandidatePage<T> {
  if (!isRecord(value) || !Array.isArray(value.results)) throw new Error("Página inválida.");
  const count = integer(value, "count");
  const next = nullableText(value, "next");
  const previous = nullableText(value, "previous");
  return { count: count as number, next, previous, results: value.results.map(parseItem) };
}
