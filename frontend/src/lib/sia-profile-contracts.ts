export type AlpinistaStatus = "ativo" | "pendente" | "confirmado" | "inativo";
import type { EncontroStatus, EncontroTipo } from "./encontro-form-contract";
export type FuncaoTipo = "encontrista" | "equipe";

interface AlpinistaIdentity {
  id: number;
  nome: string;
  foto: string | null;
}

export interface AlpinistaSummary extends AlpinistaIdentity {
  idade: number | null;
  grupo: string | null;
  whatsapp: string;
  batizado: boolean | null;
  primeira_comunhao: boolean | null;
  crismado: boolean | null;
  musica: { violeiro: boolean; canta: boolean };
  responsaveis?: Array<{ nome: string | null; telefone: string | null }>;
}

export interface AlpinistaFull extends AlpinistaIdentity {
  cpf: string | null;
  email: string;
  telefone: string;
  dataNascimento: string | null;
  endereco: string | null;
  nomePai: string | null;
  telefonePai: string | null;
  nomeMae: string | null;
  telefoneMae: string | null;
  restricaoSaude: string | null;
  medicacao: string | null;
  conheciaEscalada: string | null;
  grupo: string | null;
  status: AlpinistaStatus;
  batizado: boolean | null;
  primeira_comunhao: boolean | null;
  crismado: boolean | null;
  eh_violeiro: boolean;
  canta: boolean;
  is_neurodivergente: boolean;
  tipo_neurodivergente: string | null;
  idade_atual: number | null;
  encontros_realizados: Array<{ tipo: string; nome_encontro: string; data: string | null; cor_grupo: string | null }>;
  historico_equipes: Array<{ nome_encontro: string; equipe: string; tipo_encontro: string; data: string | null; cor_grupo: string | null }>;
  historico_eventos: Array<{ nome_evento: string; data: string | null }>;
}

export type AlpinistaProfile = AlpinistaSummary | AlpinistaFull;

export function isAlpinistaFull(value: unknown): value is AlpinistaFull {
  if (typeof value !== "object" || value === null) return false;
  return "status" in value && typeof value.status === "string" &&
    "email" in value && typeof value.email === "string" &&
    "telefone" in value && typeof value.telefone === "string";
}

export interface EncontroSummary {
  id: number;
  encontro: string;
  tipo: EncontroTipo;
  data_referencia: string;
}

export interface EncontroFull extends EncontroSummary {
  data_exato: string;
  local: string;
  status: EncontroStatus;
  status_encontro: string;
  criado_em: string;
}

export type EncontroProfile = EncontroSummary | EncontroFull;

export function isEncontroFull(value: unknown): value is EncontroFull {
  if (typeof value !== "object" || value === null) return false;
  return "data_exato" in value && typeof value.data_exato === "string" &&
    "local" in value && typeof value.local === "string" &&
    "status" in value && typeof value.status === "string";
}

export interface ConfirmedAlpinista {
  id: number;
  nome: string;
}

export interface FuncaoEncontro {
  id: number;
  nome: string;
  tipo: FuncaoTipo;
  descricao_faq: string;
  ordem: number;
  eh_violeiro: boolean;
}

export interface EncounterParticipation {
  id: number;
  alpinista: ConfirmedAlpinista;
  funcao: FuncaoEncontro;
  cor_grupo: string | null;
  coordenador: boolean;
}

export function confirmedAlpinistas(participacoes: EncounterParticipation[]): ConfirmedAlpinista[] {
  return participacoes
    .filter((participacao) => participacao.funcao?.tipo === "encontrista")
    .map((participacao) => ({
      id: participacao.alpinista.id,
      nome: participacao.alpinista.nome,
    }));
}
