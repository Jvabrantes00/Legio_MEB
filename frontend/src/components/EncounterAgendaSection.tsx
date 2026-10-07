"use client";

import { useCallback, useEffect, useState } from "react";

import { siaFetch } from "../lib/sia-api";
import { errorMessage, readApiError } from "../lib/form-api-error";
import {
  agendaGroup,
  agendaItemDisplayTitle,
  formatDateOnly,
  sortAgendaItemsChronologically,
  type EncounterAgendaItem,
  type EncounterAgendaResponse,
} from "../lib/institutional-calendar";
import { EncounterCategoryIcon } from "./icons/EncounterCategoryIcon";

const GROUPS = ["Dias do Encontro", "Preparação", "Pós-Encontro"] as const;

export function AgendaItems({ items }: { items: EncounterAgendaItem[] }) {
  return (
    <div
      className="grid gap-5 sm:gap-6"
      style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 15rem), 1fr))" }}
    >
      {GROUPS.map((group) => {
        const groupItems = sortAgendaItemsChronologically(
          items.filter((item) => agendaGroup(item.origem) === group),
        );
        return (
          <section key={group} aria-labelledby={`agenda-${group.replaceAll(" ", "-")}`} className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 sm:p-5">
            <h3 id={`agenda-${group.replaceAll(" ", "-")}`} className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">
              {group}
            </h3>
            {groupItems.length ? (
              <ul className="mt-4 space-y-4 sm:space-y-5">
                {groupItems.map((item) => {
                  const visibleSubtitle = item.origem === "DIA_ENCONTRO" ? null : item.subtitulo;
                  return (
                    <li key={item.id} className="grid gap-1 text-sm text-slate-700 sm:grid-cols-[max-content_minmax(0,1fr)] sm:gap-x-4">
                      <time dateTime={item.data} className="shrink-0 font-semibold text-slate-900">
                        {formatDateOnly(item.data, { day: "2-digit", month: "2-digit" })}
                      </time>
                      <span className="min-w-0">
                        <span className="block font-medium hyphens-none">{agendaItemDisplayTitle(item)}</span>
                        {visibleSubtitle ? <span className="mt-0.5 block text-xs text-slate-500">{visibleSubtitle}</span> : null}
                      </span>
                    </li>
                  );
                })}
              </ul>
            ) : <p className="mt-3 text-sm text-slate-400">Nenhum item.</p>}
          </section>
        );
      })}
    </div>
  );
}

export function EncounterAgendaSection({ encontroId }: { encontroId: number | string }) {
  const [agenda, setAgenda] = useState<EncounterAgendaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setLoadError(null);
    try {
      const response = await siaFetch(`/calendario-institucional/encontros/${encontroId}/agenda/`, { signal });
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível carregar a Agenda."));
      const body: EncounterAgendaResponse = await response.json();
      setAgenda(body.itens);
    } catch (error: unknown) {
      if (signal?.aborted) return;
      setLoadError(errorMessage(error, "Não foi possível carregar a Agenda."));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [encontroId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [load]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="encontro-agenda-title">
      <div className="mb-4 flex items-center gap-3">
        <span className="rounded-lg bg-blue-50 p-2 text-blue-700"><EncounterCategoryIcon /></span>
        <div>
          <h2 id="encontro-agenda-title" className="text-xl font-bold text-slate-900">Agenda</h2>
          <p className="text-sm text-slate-500">Dias, preparação e pós-Encontro na fonte canônica.</p>
        </div>
      </div>
      {loading ? <p className="text-sm text-slate-500" role="status">Carregando Agenda...</p> : null}
      {loadError ? (
        <div className="flex flex-wrap items-center gap-3 text-sm text-red-700" role="alert">
          <span>{loadError}</span>
          <button type="button" onClick={() => void load()} className="font-semibold underline">Tentar novamente</button>
        </div>
      ) : null}
      {!loading && !loadError && agenda.length === 0 ? <p className="text-sm text-slate-500">Nenhum item de Agenda cadastrado.</p> : null}
      {!loading && !loadError && agenda.length > 0 ? <AgendaItems items={agenda} /> : null}
    </section>
  );
}
