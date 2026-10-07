"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { CalendarEncounterDrawer } from "../../../components/CalendarEncounterDrawer";
import { CalendarEncounterForm } from "../../../components/CalendarEncounterForm";
import { CalendarExportDialog } from "../../../components/CalendarExportDialog";
import { MonthView, YearView } from "../../../components/InstitutionalCalendarViews";
import { InstitutionalCalendarHeader } from "../../../components/InstitutionalCalendarHeader";
import { useSiaSession } from "../../../components/SiaSessionProvider";
import { errorMessage, readApiError } from "../../../lib/form-api-error";
import {
  calendarOccurrences,
  monthInterval,
  shiftMonth,
  todayParts,
  yearInterval,
  type CalendarFilter,
  type CalendarOccurrence,
  type CalendarView,
  type InstitutionalCalendarResponse,
} from "../../../lib/institutional-calendar";
import { siaFetch } from "../../../lib/sia-api";
import {
  canManageInstitutionalCalendar,
  canViewInstitutionalCalendar,
} from "../../../lib/sia-capabilities";

export default function InstitutionalCalendarPage() {
  const { session, loading: sessionLoading, error: sessionError } = useSiaSession();
  const today = useMemo(() => todayParts(), []);
  const [cursor, setCursor] = useState({ year: today.year, month: today.month });
  const [view, setView] = useState<CalendarView>("month");
  const [filter, setFilter] = useState<CalendarFilter>("all");
  const [data, setData] = useState<InstitutionalCalendarResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedEncounterId, setSelectedEncounterId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [createDate, setCreateDate] = useState("");
  const [conflictNotice, setConflictNotice] = useState(0);

  const interval = useMemo(
    () => view === "month"
      ? monthInterval(cursor.year, cursor.month)
      : yearInterval(cursor.year),
    [cursor.month, cursor.year, view],
  );

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setLoadError(null);
    try {
      const params = new URLSearchParams(interval);
      const response = await siaFetch(`/calendario-institucional/?${params.toString()}`, { signal });
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível carregar o Calendário."));
      const body: InstitutionalCalendarResponse = await response.json();
      setData(body);
    } catch (error: unknown) {
      if (signal?.aborted) return;
      setLoadError(errorMessage(error, "Não foi possível carregar o Calendário."));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [interval]);

  useEffect(() => {
    if (sessionLoading || !canViewInstitutionalCalendar(session)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [load, retry, session, sessionLoading]);

  const occurrences = useMemo(() => data ? calendarOccurrences(data) : [], [data]);
  const selectedEncounter = data?.itens.find((item) => item.encontro_id === selectedEncounterId) ?? null;
  const canManage = Boolean(
    data?.capabilities.pode_gerir_calendario
    && canManageInstitutionalCalendar(session),
  );

  const move = (delta: number) => {
    setSelectedDate(null);
    if (view === "year") setCursor((current) => ({ ...current, year: current.year + delta }));
    else setCursor((current) => shiftMonth(current.year, current.month, delta));
  };

  const goToday = () => {
    setCursor({ year: today.year, month: today.month });
    setView("month");
    setSelectedDate(`${today.year}-${String(today.month + 1).padStart(2, "0")}-${String(today.day).padStart(2, "0")}`);
  };

  const openCreate = (date = "") => {
    setCreateDate(date);
    setCreateOpen(true);
  };

  const openOccurrence = (item: CalendarOccurrence) => setSelectedEncounterId(item.encontro_id);

  if (sessionLoading) return <p className="p-10 text-slate-500" role="status">Carregando sessão...</p>;
  if (sessionError) return <p className="p-10 text-red-700" role="alert">{sessionError}</p>;
  if (!canViewInstitutionalCalendar(session)) return <p className="p-10 text-slate-600">Seu papel não permite acessar o Calendário Institucional.</p>;

  return (
    <div className="institutional-calendar space-y-5">
      <InstitutionalCalendarHeader cursor={cursor} view={view} filter={filter} canManage={canManage} onMove={move} onToday={goToday} onView={setView} onFilter={setFilter} onExport={() => setExportOpen(true)} onCreate={() => openCreate()} />

      {conflictNotice > 0 ? <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="status">Existe outro compromisso em {conflictNotice} data(s). A criação foi concluída; conflitos são consultivos.</p> : null}
      <p className="text-xs font-medium text-slate-500"><span aria-hidden="true">*</span><span className="sr-only">Asterisco:</span> Data ainda sujeita a confirmação.</p>

      {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500" role="status">Carregando calendário...</div> : null}
      {loadError ? <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-red-800" role="alert"><p>{loadError}</p><button type="button" onClick={() => setRetry((value) => value + 1)} className="mt-3 font-bold underline">Tentar novamente</button></div> : null}
      {!loading && !loadError && occurrences.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">Nenhum compromisso neste período.</div> : null}

      {!loading && !loadError && view === "month" ? <MonthView year={cursor.year} month={cursor.month} occurrences={occurrences} canManage={canManage} selectedDate={selectedDate} onSelectDate={setSelectedDate} onOpenEncounter={openOccurrence} onCreateAt={openCreate} /> : null}
      {!loading && !loadError && view === "year" ? <YearView year={cursor.year} occurrences={occurrences} current={{ year: today.year, month: today.month }} onOpenMonth={(month) => { setCursor({ year: cursor.year, month }); setView("month"); setSelectedDate(null); }} /> : null}

      <CalendarEncounterDrawer key={selectedEncounterId ?? "closed"} encounter={selectedEncounter} canManage={canManage} onClose={() => setSelectedEncounterId(null)} onChanged={async () => { await load(); }} />
      {createOpen ? <CalendarEncounterForm open initialDate={createDate} onClose={() => setCreateOpen(false)} onCreated={(warnings) => { setConflictNotice(warnings); setRetry((value) => value + 1); }} /> : null}
      {exportOpen ? <CalendarExportDialog key={`${view}-${cursor.year}-${cursor.month}`} open year={cursor.year} month={cursor.month} view={view} canManage={canManage} onClose={() => setExportOpen(false)} /> : null}
    </div>
  );
}
