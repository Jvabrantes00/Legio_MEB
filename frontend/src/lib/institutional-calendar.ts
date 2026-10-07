export type CalendarView = "month" | "year";
export type CalendarFilter = "all" | "encounter";
export type AgendaOrigin = "DIA_ENCONTRO" | "REUNIAO_PREPARATORIA" | "AVALIACAO";
export type AgendaConfirmation = "PROVISORIA" | "OFICIAL" | "INDETERMINADA" | null;

export interface CalendarConflict {
  data: string;
  encontro_ids: number[];
  quantidade: number;
}

export interface EncounterAgendaItem {
  id: string;
  origem_id: number | null;
  origem: AgendaOrigin;
  data: string;
  titulo: string;
  subtitulo: string | null;
  confirmacao: AgendaConfirmation;
  publicavel_externamente: boolean;
  encontro_id: number;
  conflito: CalendarConflict | null;
}

export interface CalendarEncounterItem {
  categoria: "ENCONTRO";
  encontro_id: number;
  titulo: string;
  tipo: string;
  status: string;
  calendario_id: number | null;
  calendario_versao: number | null;
  origem_agenda: "CANONICA" | "LEGADO";
  confirmacao: Exclude<AgendaConfirmation, null>;
  dias: Array<{
    id: number | null;
    data: string;
    ordem: number;
    rotulo: string;
    conflito: CalendarConflict | null;
  }>;
  agenda: EncounterAgendaItem[];
  pode_editar_calendario: boolean;
}

export interface InstitutionalCalendarResponse {
  periodo: { inicio: string; fim: string };
  itens: CalendarEncounterItem[];
  conflitos: CalendarConflict[];
  capabilities: {
    pode_visualizar: boolean;
    pode_gerir_calendario: boolean;
    pode_criar_encontro: boolean;
    pode_publicar: boolean;
  };
}

export interface EncounterAgendaResponse {
  encontro_id: number;
  itens: EncounterAgendaItem[];
}

export interface CalendarOccurrence extends EncounterAgendaItem {
  encontro_titulo: string;
  encontro_tipo: string;
  encontro_status: string;
  pode_editar_calendario: boolean;
}

export interface DateParts {
  year: number;
  month: number;
  day: number;
}

export interface CalendarCell extends DateParts {
  key: string;
  inCurrentMonth: boolean;
  isToday: boolean;
}

export interface EncounterDayInput {
  data: string;
  rotulo: string;
}

export interface PreparatoryMeetingInput {
  data: string;
  horario: string;
  local: string;
  complemento: string;
}

export interface EncounterAgendaFormValues {
  encontro: string;
  tipo: "Escalada" | "AVC" | "Esppa" | "Acampamento";
  local: string;
  dias: EncounterDayInput[];
  reunioes: PreparatoryMeetingInput[];
  avaliacaoData: string;
}

export const WEEKDAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"] as const;
export const MONTH_LABELS = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
] as const;
export const ESCALADA_DAY_SUGGESTIONS = [
  "Pré-Escalada", "Sexta-feira", "Sábado", "Domingo",
] as const;

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function dateKey(parts: DateParts): string {
  return `${parts.year}-${pad(parts.month + 1)}-${pad(parts.day)}`;
}

export function parseDateOnly(value: string): DateParts {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) throw new Error("Data civil inválida.");
  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  const day = Number(match[3]);
  const probe = new Date(Date.UTC(year, month, day));
  if (
    probe.getUTCFullYear() !== year
    || probe.getUTCMonth() !== month
    || probe.getUTCDate() !== day
  ) throw new Error("Data civil inválida.");
  return { year, month, day };
}

export function formatDateOnly(value: string, options?: Intl.DateTimeFormatOptions): string {
  const parts = parseDateOnly(value);
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
    ...options,
  }).format(new Date(Date.UTC(parts.year, parts.month, parts.day)));
}

export function todayParts(now = new Date()): DateParts {
  return { year: now.getFullYear(), month: now.getMonth(), day: now.getDate() };
}

export function monthGrid(year: number, month: number, today = todayParts()): CalendarCell[] {
  const firstWeekdaySundayZero = new Date(Date.UTC(year, month, 1)).getUTCDay();
  const mondayOffset = (firstWeekdaySundayZero + 6) % 7;
  const gridStart = new Date(Date.UTC(year, month, 1 - mondayOffset));
  return Array.from({ length: 42 }, (_, index) => {
    const current = new Date(gridStart);
    current.setUTCDate(gridStart.getUTCDate() + index);
    const parts = {
      year: current.getUTCFullYear(),
      month: current.getUTCMonth(),
      day: current.getUTCDate(),
    };
    return {
      ...parts,
      key: dateKey(parts),
      inCurrentMonth: parts.year === year && parts.month === month,
      isToday: parts.year === today.year && parts.month === today.month && parts.day === today.day,
    };
  });
}

export function monthInterval(year: number, month: number): { inicio: string; fim: string } {
  const grid = monthGrid(year, month);
  return { inicio: grid[0].key, fim: grid[grid.length - 1].key };
}

export function yearInterval(year: number): { inicio: string; fim: string } {
  return { inicio: `${year}-01-01`, fim: `${year}-12-31` };
}

export function shiftMonth(year: number, month: number, delta: number): { year: number; month: number } {
  const shifted = new Date(Date.UTC(year, month + delta, 1));
  return { year: shifted.getUTCFullYear(), month: shifted.getUTCMonth() };
}

export function calendarOccurrences(response: InstitutionalCalendarResponse): CalendarOccurrence[] {
  return response.itens.flatMap((encounter) => encounter.agenda.map((item) => ({
    ...item,
    encontro_titulo: encounter.titulo,
    encontro_tipo: encounter.tipo,
    encontro_status: encounter.status,
    pode_editar_calendario: encounter.pode_editar_calendario,
  })));
}

export function occurrencesByDate(items: CalendarOccurrence[]): Map<string, CalendarOccurrence[]> {
  const grouped = new Map<string, CalendarOccurrence[]>();
  for (const item of items) {
    const current = grouped.get(item.data) ?? [];
    current.push(item);
    grouped.set(item.data, current);
  }
  return grouped;
}

export function agendaGroup(origin: AgendaOrigin): "Dias do Encontro" | "Preparação" | "Pós-Encontro" {
  if (origin === "DIA_ENCONTRO") return "Dias do Encontro";
  if (origin === "REUNIAO_PREPARATORIA") return "Preparação";
  return "Pós-Encontro";
}

export function agendaItemDisplayTitle(item: EncounterAgendaItem): string {
  if (item.origem !== "REUNIAO_PREPARATORIA") return item.titulo;
  return item.titulo.replace(/^(\d+)ª Reunião$/, "$1ª Preparatória");
}

export function sortAgendaItemsChronologically(items: EncounterAgendaItem[]): EncounterAgendaItem[] {
  return [...items].sort((first, second) => first.data.localeCompare(second.data));
}

export function buildEncounterAgendaPayload(values: EncounterAgendaFormValues) {
  return {
    encontro: values.encontro.trim(),
    tipo: values.tipo,
    local: values.local.trim(),
    dias: values.dias.map((item, index) => ({
      ordem: index + 1,
      data: item.data,
      rotulo: item.rotulo.trim(),
    })),
    reunioes: values.reunioes.map((item, index) => ({
      ordem: index + 1,
      data: item.data,
      horario: item.horario,
      local: item.local.trim(),
      complemento: item.complemento.trim(),
    })),
    ...(values.avaliacaoData ? { avaliacao: { data: values.avaliacaoData } } : {}),
  };
}

export function emptyEncounterAgendaForm(initialDate = ""): EncounterAgendaFormValues {
  return {
    encontro: "",
    tipo: "Escalada",
    local: "Nova Betânia",
    dias: [{ data: initialDate, rotulo: initialDate ? ESCALADA_DAY_SUGGESTIONS[0] : "" }],
    reunioes: [],
    avaliacaoData: "",
  };
}
