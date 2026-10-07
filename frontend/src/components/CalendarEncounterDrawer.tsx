"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Pencil, X } from "lucide-react";

import { errorMessage, readApiError } from "../lib/form-api-error";
import { keepFocusInsideDialog } from "../lib/dialog-focus";
import {
  type CalendarEncounterItem,
  type EncounterAgendaItem,
  type EncounterAgendaResponse,
} from "../lib/institutional-calendar";
import { siaFetch } from "../lib/sia-api";
import { AgendaItems } from "./EncounterAgendaSection";
import { CalendarEncounterEditor } from "./CalendarEncounterEditor";
import { EncounterCategoryIcon } from "./icons/EncounterCategoryIcon";

interface CalendarEncounterDrawerProps {
  encounter: CalendarEncounterItem | null;
  canManage: boolean;
  onClose: () => void;
  onChanged: () => Promise<void> | void;
}

type CalendarRequest = (path: string, init?: RequestInit) => Promise<Response>;

export function canOfficializeAgenda(encounter: CalendarEncounterItem, canManage: boolean): boolean {
  return canManage
    && encounter.pode_editar_calendario
    && encounter.status === "em_agendamento"
    && encounter.confirmacao === "PROVISORIA";
}

export async function officializeAgendaFromDrawer({
  encounterId,
  onChanged,
  reloadAgenda,
  request = siaFetch,
}: {
  encounterId: number;
  onChanged: () => Promise<void> | void;
  reloadAgenda: () => Promise<void>;
  request?: CalendarRequest;
}): Promise<number> {
  const response = await request(`/calendario-institucional/encontros/${encounterId}/oficializar/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) throw new Error(await readApiError(response, "Não foi possível oficializar a Agenda."));
  const body: { avisos_conflito?: unknown[] } = await response.json();
  await Promise.all([Promise.resolve(onChanged()), reloadAgenda()]);
  return body.avisos_conflito?.length ?? 0;
}

export function CalendarEncounterDrawer({ encounter, canManage, onClose, onChanged }: CalendarEncounterDrawerProps) {
  const [agenda, setAgenda] = useState<EncounterAgendaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [officializing, setOfficializing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionWarnings, setActionWarnings] = useState(0);
  const closeButton = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLElement>(null);

  const load = useCallback(async () => {
    if (!encounter) return;
    setLoading(true);
    setLoadError(null);
    try {
      const response = await siaFetch(`/calendario-institucional/encontros/${encounter.encontro_id}/agenda/`);
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível carregar a Agenda."));
      const body: EncounterAgendaResponse = await response.json();
      setAgenda(body.itens);
    } catch (error: unknown) {
      setLoadError(errorMessage(error, "Não foi possível carregar a Agenda."));
    } finally {
      setLoading(false);
    }
  }, [encounter]);

  useEffect(() => {
    if (!encounter) return;
    const timer = window.setTimeout(() => void load(), 0);
    const previous = document.activeElement as HTMLElement | null;
    const focusTimer = window.setTimeout(() => closeButton.current?.focus(), 0);
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      keepFocusInsideDialog(event, dialog.current);
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      window.clearTimeout(timer);
      window.clearTimeout(focusTimer);
      previous?.focus();
    };
  }, [encounter, load, onClose]);

  if (!encounter) return null;

  const changed = async () => {
    await Promise.all([Promise.resolve(onChanged()), load()]);
  };

  const officialize = async () => {
    setOfficializing(true);
    setActionError(null);
    setActionWarnings(0);
    try {
      const warnings = await officializeAgendaFromDrawer({
        encounterId: encounter.encontro_id,
        onChanged,
        reloadAgenda: load,
      });
      setActionWarnings(warnings);
    } catch (error: unknown) {
      setActionError(errorMessage(error, "Não foi possível oficializar a Agenda."));
    } finally {
      setOfficializing(false);
    }
  };

  const showOfficialize = canOfficializeAgenda(encounter, canManage);

  return (
    <div className="fixed inset-0 z-[60] flex justify-end bg-slate-950/40" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <aside ref={dialog} role="dialog" aria-modal="true" aria-labelledby="calendar-drawer-title" tabIndex={-1} className="h-full w-full overflow-y-auto bg-white p-5 shadow-2xl sm:max-w-3xl sm:p-7 xl:max-w-4xl xl:p-9">
        <header className="flex items-start justify-between gap-4">
          <div className="flex gap-3">
            <span className="mt-1 rounded-xl bg-blue-50 p-2 text-blue-700"><EncounterCategoryIcon label="Categoria Encontro" /></span>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-700">Encontro · {encounter.tipo}</p>
              <h2 id="calendar-drawer-title" className="mt-1 text-2xl font-bold text-slate-950">{encounter.titulo}</h2>
            </div>
          </div>
          <button ref={closeButton} type="button" onClick={onClose} aria-label="Fechar detalhes" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"><X /></button>
        </header>

        <div className="mt-8">
          {loading ? <p role="status" className="text-sm text-slate-500">Carregando Agenda...</p> : null}
          {loadError ? <div role="alert" className="text-sm text-red-700">{loadError} <button type="button" onClick={() => void load()} className="font-semibold underline">Tentar novamente</button></div> : null}
          {!loading && !loadError && agenda.length > 0 ? <AgendaItems items={agenda} /> : null}
          {!loading && !loadError && agenda.length === 0 ? <p className="text-sm text-slate-500">Nenhum item na Agenda.</p> : null}
        </div>

        <div className="mt-9 space-y-3">
          {actionError ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{actionError}</p> : null}
          {actionWarnings > 0 ? <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">Existe outro compromisso em {actionWarnings} data(s). O aviso não bloqueou a oficialização.</p> : null}
          <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-center">
            {showOfficialize ? <button type="button" disabled={officializing} onClick={() => void officialize()} className="inline-flex items-center justify-center justify-self-stretch rounded-lg border border-blue-300 px-4 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50 disabled:opacity-60 sm:justify-self-start">{officializing ? "Oficializando..." : "Oficializar agenda"}</button> : null}
            <div className="flex flex-col gap-3 sm:col-start-2 sm:flex-row sm:justify-self-end">
              {canManage ? <button type="button" onClick={() => setEditing((current) => !current)} className="order-2 inline-flex items-center justify-center gap-2 rounded-lg border border-blue-200 px-4 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50 sm:order-1"><Pencil size={16} />Editar calendário</button> : null}
              <Link href={`/encontros/${encounter.encontro_id}`} className="order-1 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-700 px-4 py-2 text-sm font-bold text-white hover:bg-blue-800 sm:order-2">Abrir Encontro completo <ArrowRight size={16} /></Link>
            </div>
          </div>
        </div>

        {editing && canManage ? <CalendarEncounterEditor key={agenda.map((item) => `${item.id}:${item.data}:${item.subtitulo ?? ""}`).join("|")} encounter={encounter} agenda={agenda} onChanged={changed} /> : null}
      </aside>
    </div>
  );
}
