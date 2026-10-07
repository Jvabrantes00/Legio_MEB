"use client";

import { Plus } from "lucide-react";

import {
  MONTH_LABELS,
  WEEKDAY_LABELS,
  agendaItemDisplayTitle,
  formatDateOnly,
  monthGrid,
  occurrencesByDate,
  type CalendarOccurrence,
} from "../lib/institutional-calendar";
import { EncounterCategoryIcon } from "./icons/EncounterCategoryIcon";

interface OccurrenceCardProps {
  item: CalendarOccurrence;
  compact?: boolean;
  onOpen: (item: CalendarOccurrence) => void;
}

export function OccurrenceCard({ item, compact = false, onOpen }: OccurrenceCardProps) {
  const provisional = item.confirmacao === "PROVISORIA";
  const secondary = item.origem === "DIA_ENCONTRO"
    ? (item.subtitulo ? item.titulo : "Dia do Encontro")
    : agendaItemDisplayTitle(item);
  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      className={`calendar-event-card group/event w-full text-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${compact ? "px-1.5 py-1" : "px-2 py-1.5"}`}
      aria-label={`${item.encontro_titulo}${provisional ? ", data sujeita a confirmação" : ""}; ${secondary}; ${formatDateOnly(item.data)}`}
    >
      <span className="flex items-center justify-center gap-1 truncate text-[11px] font-bold text-slate-900">
        <EncounterCategoryIcon className="h-3.5 w-3.5 shrink-0 text-blue-700" />
        <span className="truncate">{item.encontro_titulo}{provisional ? <span aria-hidden="true"> *</span> : null}</span>
        {provisional ? <span className="sr-only"> Data ainda sujeita a confirmação.</span> : null}
      </span>
      {!compact ? <span className="mt-0.5 block truncate text-[10px] font-medium text-blue-800">{secondary}</span> : null}
      {!compact && item.origem === "REUNIAO_PREPARATORIA" && item.subtitulo ? <span className="block truncate text-[9px] text-slate-500">{item.subtitulo}</span> : null}
    </button>
  );
}

interface MonthViewProps {
  year: number;
  month: number;
  occurrences: CalendarOccurrence[];
  canManage: boolean;
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
  onOpenEncounter: (item: CalendarOccurrence) => void;
  onCreateAt: (date: string) => void;
}

export function MonthView({
  year, month, occurrences, canManage, selectedDate,
  onSelectDate, onOpenEncounter, onCreateAt,
}: MonthViewProps) {
  const cells = monthGrid(year, month);
  const byDate = occurrencesByDate(occurrences);
  const selectedItems = selectedDate ? (byDate.get(selectedDate) ?? []) : [];

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-2xl border border-[var(--calendar-border)] bg-white shadow-sm">
        <div className="grid grid-cols-7 border-b border-[var(--calendar-border)] bg-[var(--calendar-surface-soft)]">
          {WEEKDAY_LABELS.map((label) => <div key={label} className="px-1 py-3 text-center text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500 sm:text-xs">{label}</div>)}
        </div>
        <div className="grid grid-cols-7">
          {cells.map((cell) => {
            const items = byDate.get(cell.key) ?? [];
            const visible = items.slice(0, 2);
            const hidden = items.length - visible.length;
            return (
              <div key={cell.key} className={`calendar-day group/day relative min-h-20 border-b border-r border-[var(--calendar-border)] p-1 sm:min-h-36 sm:p-2 ${cell.inCurrentMonth ? "bg-white" : "bg-slate-50/70 text-slate-400"} ${selectedDate === cell.key ? "ring-2 ring-inset ring-blue-500" : ""}`}>
                <button type="button" onClick={() => onSelectDate(cell.key)} className="rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700" aria-label={`Selecionar ${formatDateOnly(cell.key)}`}>
                  <span className={`flex h-6 w-6 items-center justify-center text-xs font-bold ${cell.isToday ? "rounded-full bg-blue-700 text-white" : "text-current"}`}>{cell.day}</span>
                </button>
                {canManage ? <button type="button" onClick={() => onCreateAt(cell.key)} aria-label={`Criar compromisso em ${formatDateOnly(cell.key)}`} className="absolute right-1 top-1 rounded-full p-1 text-blue-700 opacity-0 transition group-hover/day:opacity-100 focus:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700 max-sm:hidden"><Plus size={14} /></button> : null}
                <div className="mt-1 hidden space-y-1 sm:block">
                  {visible.map((item) => <OccurrenceCard key={item.id} item={item} onOpen={onOpenEncounter} />)}
                  {hidden > 0 ? <button type="button" onClick={() => onSelectDate(cell.key)} className="w-full rounded-md py-1 text-center text-[10px] font-bold text-blue-700 hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700" aria-label={`Ver mais ${hidden} compromissos de ${formatDateOnly(cell.key)}`}>+{hidden}</button> : null}
                </div>
                {items.length > 0 ? <span className="mx-auto mt-2 block h-1.5 w-1.5 rounded-full bg-blue-600 sm:hidden" aria-label={`${items.length} compromisso(s)`} /> : null}
              </div>
            );
          })}
        </div>
      </div>

      {selectedDate ? (
        <section className="rounded-2xl border border-[var(--calendar-border)] bg-white p-4 shadow-sm" aria-labelledby="selected-day-title">
          <div className="flex items-center justify-between gap-3">
            <div><p className="text-xs font-bold uppercase tracking-[0.15em] text-blue-700">Dia selecionado</p><h2 id="selected-day-title" className="text-lg font-bold text-slate-950">{formatDateOnly(selectedDate, { weekday: "long", day: "2-digit", month: "long" })}</h2></div>
            {canManage ? <button type="button" onClick={() => onCreateAt(selectedDate)} className="inline-flex items-center gap-1 rounded-lg border border-blue-200 px-3 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50"><Plus size={16} />Novo</button> : null}
          </div>
          {selectedItems.length ? <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{selectedItems.map((item) => <OccurrenceCard key={item.id} item={item} onOpen={onOpenEncounter} />)}</div> : <p className="mt-3 text-sm text-slate-500">Nenhum compromisso nesta data.</p>}
        </section>
      ) : null}
    </div>
  );
}

interface YearViewProps {
  year: number;
  occurrences: CalendarOccurrence[];
  current: { year: number; month: number };
  onOpenMonth: (month: number) => void;
}

export function YearView({ year, occurrences, current, onOpenMonth }: YearViewProps) {
  const byDate = occurrencesByDate(occurrences);
  return (
    <div className="calendar-year-grid grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {MONTH_LABELS.map((label, month) => {
        const cells = monthGrid(year, month);
        const count = cells.filter((cell) => cell.inCurrentMonth).reduce((total, cell) => total + (byDate.get(cell.key)?.length ?? 0), 0);
        const isCurrent = current.year === year && current.month === month;
        return (
          <button key={label} type="button" onClick={() => onOpenMonth(month)} className={`rounded-2xl border bg-white p-4 text-left shadow-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700 ${isCurrent ? "border-blue-500 ring-2 ring-blue-100" : "border-[var(--calendar-border)] hover:-translate-y-0.5 hover:shadow-md"}`} aria-label={`Abrir ${label} de ${year}${count ? `, ${count} compromissos` : ""}`}>
            <div className="mb-3 flex items-center justify-between"><h2 className="font-bold text-slate-950">{label}</h2><span className="text-xs font-semibold text-slate-500">{count ? `${count} item(ns)` : "Livre"}</span></div>
            <div className="grid grid-cols-7 gap-y-1 text-center">
              {WEEKDAY_LABELS.map((weekday) => <span key={weekday} className="text-[9px] font-bold text-slate-400">{weekday.slice(0, 1)}</span>)}
              {cells.map((cell) => {
                const hasItems = (byDate.get(cell.key)?.length ?? 0) > 0;
                return <span key={cell.key} className={`relative flex h-5 items-center justify-center text-[9px] ${cell.inCurrentMonth ? "text-slate-600" : "text-slate-200"} ${cell.isToday ? "rounded-full bg-blue-700 font-bold text-white" : ""}`}>{cell.day}{hasItems && cell.inCurrentMonth ? <span className="absolute bottom-0 h-1 w-1 rounded-full bg-blue-600" /> : null}</span>;
              })}
            </div>
          </button>
        );
      })}
    </div>
  );
}
