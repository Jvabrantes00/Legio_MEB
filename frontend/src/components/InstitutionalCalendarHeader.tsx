"use client";

import { CalendarDays, ChevronLeft, ChevronRight, Download, Plus } from "lucide-react";

import { MONTH_LABELS, type CalendarFilter, type CalendarView } from "../lib/institutional-calendar";

interface InstitutionalCalendarHeaderProps {
  cursor: { year: number; month: number };
  view: CalendarView;
  filter: CalendarFilter;
  canManage: boolean;
  onMove: (delta: number) => void;
  onToday: () => void;
  onView: (view: CalendarView) => void;
  onFilter: (filter: CalendarFilter) => void;
  onCreate: () => void;
}

export function InstitutionalCalendarHeader({
  cursor, view, filter, canManage, onMove, onToday, onView, onFilter, onCreate,
}: InstitutionalCalendarHeaderProps) {
  return (
    <header className="rounded-3xl border border-[var(--calendar-border)] bg-white p-5 shadow-sm sm:p-7">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-blue-700"><CalendarDays size={16} />Calendário</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-[var(--calendar-ink)] sm:text-4xl">Calendário do Movimento</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-500">Agenda do ano</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => onMove(-1)} aria-label={view === "month" ? "Mês anterior" : "Ano anterior"} className="calendar-control"><ChevronLeft size={18} /></button>
          <div className="min-w-40 text-center font-black text-[var(--calendar-ink)]">{view === "month" ? `${MONTH_LABELS[cursor.month]} ${cursor.year}` : cursor.year}</div>
          <button type="button" onClick={() => onMove(1)} aria-label={view === "month" ? "Próximo mês" : "Próximo ano"} className="calendar-control"><ChevronRight size={18} /></button>
          <button type="button" onClick={onToday} className="calendar-control px-3 text-sm font-bold">Hoje</button>
          <div className="flex rounded-xl bg-slate-100 p-1" aria-label="Modo de visualização">
            {(["month", "year"] as const).map((mode) => <button key={mode} type="button" aria-pressed={view === mode} onClick={() => onView(mode)} className={`rounded-lg px-3 py-1.5 text-sm font-bold transition ${view === mode ? "bg-white text-blue-700 shadow-sm" : "text-slate-500"}`}>{mode === "month" ? "Mês" : "Ano"}</button>)}
          </div>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-4 border-t border-slate-100 pt-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2" aria-label="Filtros de categoria">
          <button type="button" aria-pressed={filter === "all"} onClick={() => onFilter("all")} className={`calendar-filter ${filter === "all" ? "calendar-filter-active" : ""}`}>Todos</button>
          <button type="button" aria-pressed={filter === "encounter"} onClick={() => onFilter("encounter")} className={`calendar-filter ${filter === "encounter" ? "calendar-filter-active" : ""}`}>Encontros</button>
          <button type="button" disabled className="calendar-filter" title="Disponível quando o domínio de Eventos for implementado">Eventos</button>
          <button type="button" disabled className="calendar-filter" title="Disponível quando outros compromissos forem implementados">Outros</button>
        </div>
        {canManage ? <div className="flex flex-wrap gap-2">
          <button type="button" disabled aria-disabled="true" title="Exportação será disponibilizada na D.6G" className="calendar-control cursor-not-allowed gap-2 px-3 text-sm font-bold opacity-50"><Download size={16} />Exportar</button>
          <button type="button" onClick={onCreate} className="inline-flex items-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-blue-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"><Plus size={17} />Novo compromisso</button>
        </div> : null}
      </div>
    </header>
  );
}
