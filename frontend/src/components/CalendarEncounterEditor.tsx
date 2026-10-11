"use client";

import { useMemo, useRef, useState } from "react";
import { AlertTriangle, Plus, Trash2 } from "lucide-react";

import { errorMessage, readApiError } from "../lib/form-api-error";
import {
  type CalendarEncounterItem,
  type EncounterAgendaItem,
} from "../lib/institutional-calendar";
import { siaFetch } from "../lib/sia-api";

interface CalendarEncounterEditorProps {
  encounter: CalendarEncounterItem;
  agenda: EncounterAgendaItem[];
  onChanged: () => Promise<void> | void;
  onCancel: () => void;
}

interface MeetingDraft {
  key: string;
  id: number | null;
  data: string;
  horario?: string;
  local?: string;
  complemento: string;
}

interface CalendarEditorDraft {
  title: string;
  location: string;
  days: Array<{ data: string; rotulo: string }>;
  preEncounterDate: string;
  meetings: MeetingDraft[];
  assessmentDate: string;
}

const fieldClass = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100";

function initialDraft(encounter: CalendarEncounterItem, agenda: EncounterAgendaItem[]): CalendarEditorDraft {
  const days = agenda.filter((item) => item.origem === "DIA_ENCONTRO");
  const meetings = agenda.filter((item) => item.origem === "REUNIAO_PREPARATORIA");
  const assessment = agenda.find((item) => item.origem === "AVALIACAO") ?? null;
  const preEncounter = agenda.find((item) => item.origem === "PRE_ENCONTRO") ?? null;
  return {
    title: encounter.titulo,
    location: "",
    days: days.map((item) => ({ data: item.data, rotulo: item.subtitulo ? item.titulo : "" })),
    preEncounterDate: preEncounter?.data ?? "",
    meetings: meetings.map((item) => ({
      key: `persisted-${item.origem_id}`,
      id: item.origem_id,
      data: item.data,
      complemento: item.subtitulo ?? "",
    })),
    assessmentDate: assessment?.data ?? "",
  };
}

function serializedDraft(draft: CalendarEditorDraft): string {
  return JSON.stringify(draft);
}

export function buildCalendarEditionPayload(draft: CalendarEditorDraft) {
  return {
    encontro: draft.title.trim(),
    ...(draft.location.trim() ? { local: draft.location.trim() } : {}),
    dias: draft.days.map((item, index) => ({ ordem: index + 1, data: item.data, rotulo: item.rotulo.trim() })),
    pre_encontro_data: draft.preEncounterDate || null,
    reunioes: draft.meetings.map((item, index) => ({
      ...(item.id === null ? {} : { id: item.id }),
      ordem: index + 1,
      data: item.data,
      ...(item.horario === undefined ? {} : { horario: item.horario }),
      ...(item.local === undefined ? {} : { local: item.local.trim() }),
      complemento: item.complemento.trim(),
    })),
    avaliacao: draft.assessmentDate ? { data: draft.assessmentDate } : null,
  };
}

export function CalendarEncounterEditor({ encounter, agenda, onChanged, onCancel }: CalendarEncounterEditorProps) {
  const startingDraft = useMemo(() => initialDraft(encounter, agenda), [agenda, encounter]);
  const [draft, setDraft] = useState<CalendarEditorDraft>(startingDraft);
  const [persistedDraft, setPersistedDraft] = useState<CalendarEditorDraft>(startingDraft);
  const [saving, setSaving] = useState(false);
  const [lifecycleBusy, setLifecycleBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<number>(0);
  const [saved, setSaved] = useState(false);
  const savingRef = useRef(false);
  const nextMeetingKey = useRef(1);
  const dirty = serializedDraft(draft) !== serializedDraft(persistedDraft);
  const base = `/calendario-institucional/encontros/${encounter.encontro_id}`;

  const readWarnings = async (response: Response) => {
    if (response.status === 204) return 0;
    const responseBody: { avisos_conflito?: unknown[] } = await response.json();
    return responseBody.avisos_conflito?.length ?? 0;
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!dirty || savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    setError(null);
    setSaved(false);
    const submittedDraft = structuredClone(draft);
    try {
      const response = await siaFetch(`${base}/salvar-edicao/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildCalendarEditionPayload(submittedDraft)),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível salvar as alterações."));
      setWarnings(await readWarnings(response));
      setPersistedDraft(submittedDraft);
      setDraft(submittedDraft);
      setSaved(true);
      await onChanged();
    } catch (caught: unknown) {
      setError(errorMessage(caught, "Não foi possível salvar as alterações."));
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const cancel = () => {
    if (savingRef.current) return;
    setDraft(structuredClone(persistedDraft));
    setError(null);
    setWarnings(0);
    setSaved(false);
    onCancel();
  };

  const lifecycleCommand = async (key: string, path: string) => {
    setLifecycleBusy(key);
    setError(null);
    try {
      const response = await siaFetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível alterar o calendário."));
      setWarnings(await readWarnings(response));
      await onChanged();
    } catch (caught: unknown) {
      setError(errorMessage(caught, "Não foi possível alterar o calendário."));
    } finally {
      setLifecycleBusy(null);
    }
  };

  const addMeeting = () => {
    const key = `new-${nextMeetingKey.current++}`;
    setDraft((current) => ({
      ...current,
      meetings: [...current.meetings, {
        key,
        id: null,
        data: "",
        horario: "19:30",
        local: current.location,
        complemento: "",
      }],
    }));
  };

  const isTemporalEditable = ["em_agendamento", "agendado", "adiado"].includes(encounter.status);
  const busy = saving || lifecycleBusy !== null;

  return (
    <form onSubmit={save} className="space-y-6 border-t border-slate-200 pt-5">
      <div>
        <h3 className="font-bold text-slate-900">Editar calendário</h3>
        <p className="mt-1 text-sm text-slate-500">Faça todas as alterações no rascunho e salve uma única vez.</p>
      </div>
      {error ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {saved && !dirty ? <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">Alterações salvas.</p> : null}
      {warnings > 0 ? <p className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><AlertTriangle size={17} className="shrink-0" />Existe outro compromisso em {warnings} data(s). O aviso não bloqueou a alteração.</p> : null}

      <section className="space-y-3" aria-labelledby="edit-basic-title">
        <h4 id="edit-basic-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Dados básicos</h4>
        <label className="block text-xs font-semibold text-slate-600">Nome<input required value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} className={`${fieldClass} mt-1`} /></label>
        <label className="block text-xs font-semibold text-slate-600">Novo local (opcional)<input value={draft.location} onChange={(event) => setDraft((current) => ({ ...current, location: event.target.value }))} className={`${fieldClass} mt-1`} /></label>
      </section>

      {isTemporalEditable ? (
        <section className="space-y-3" aria-labelledby="edit-days-title">
          <h4 id="edit-days-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Dias do Encontro</h4>
          {draft.days.map((day, index) => (
            <div key={index} className="grid grid-cols-[1fr_1fr_auto] gap-2">
              <input required aria-label={`Data ${index + 1}`} type="date" value={day.data} onChange={(event) => setDraft((current) => ({ ...current, days: current.days.map((item, itemIndex) => itemIndex === index ? { ...item, data: event.target.value } : item) }))} className={fieldClass} />
              <input aria-label={`Rótulo ${index + 1}`} value={day.rotulo} onChange={(event) => setDraft((current) => ({ ...current, days: current.days.map((item, itemIndex) => itemIndex === index ? { ...item, rotulo: event.target.value } : item) }))} className={fieldClass} />
              <button type="button" aria-label={`Remover dia ${index + 1}`} disabled={draft.days.length === 1 || busy} onClick={() => setDraft((current) => ({ ...current, days: current.days.filter((_, itemIndex) => itemIndex !== index) }))} className="rounded-lg p-2 text-red-600 hover:bg-red-50 disabled:opacity-30"><Trash2 size={17} /></button>
            </div>
          ))}
          <button type="button" disabled={busy} onClick={() => setDraft((current) => ({ ...current, days: [...current.days, { data: "", rotulo: "" }] }))} className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 disabled:opacity-40"><Plus size={15} />Adicionar data</button>
        </section>
      ) : null}

      <section className="space-y-3" aria-labelledby="edit-pre-encounter-title">
        <h4 id="edit-pre-encounter-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Pré-Encontro</h4>
        <label className="block text-xs font-semibold text-slate-600">Data do Pré-Encontro<input aria-label="Data do Pré-Encontro" type="date" value={draft.preEncounterDate} onChange={(event) => setDraft((current) => ({ ...current, preEncounterDate: event.target.value }))} className={`${fieldClass} mt-1 max-w-xs`} /></label>
        <p className="text-sm text-slate-500">Item canônico próprio, diferente das reuniões preparatórias.</p>
      </section>

      <section className="space-y-3" aria-labelledby="edit-meetings-title">
        <h4 id="edit-meetings-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Preparação</h4>
        {draft.meetings.length === 0 ? <p className="text-sm text-slate-500">Nenhuma preparatória.</p> : null}
        {draft.meetings.map((meeting, index) => (
          <div key={meeting.key} className="space-y-2 rounded-lg border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold">{index + 1}ª Preparatória</p>
              <button type="button" aria-label={`Remover preparatória ${index + 1}`} disabled={busy} onClick={() => setDraft((current) => ({ ...current, meetings: current.meetings.filter((item) => item.key !== meeting.key) }))} className="rounded-lg p-2 text-red-600 hover:bg-red-50 disabled:opacity-30"><Trash2 size={17} /></button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input required aria-label={`Data da preparatória ${index + 1}`} type="date" value={meeting.data} onChange={(event) => setDraft((current) => ({ ...current, meetings: current.meetings.map((item) => item.key === meeting.key ? { ...item, data: event.target.value } : item) }))} className={fieldClass} />
              {meeting.id === null ? <input required aria-label={`Horário da preparatória ${index + 1}`} type="time" value={meeting.horario} onChange={(event) => setDraft((current) => ({ ...current, meetings: current.meetings.map((item) => item.key === meeting.key ? { ...item, horario: event.target.value } : item) }))} className={fieldClass} /> : null}
              {meeting.id === null ? <input required aria-label={`Local da preparatória ${index + 1}`} placeholder="Local" value={meeting.local} onChange={(event) => setDraft((current) => ({ ...current, meetings: current.meetings.map((item) => item.key === meeting.key ? { ...item, local: event.target.value } : item) }))} className={fieldClass} /> : null}
              <input aria-label={`Complemento da preparatória ${index + 1}`} value={meeting.complemento} onChange={(event) => setDraft((current) => ({ ...current, meetings: current.meetings.map((item) => item.key === meeting.key ? { ...item, complemento: event.target.value } : item) }))} className={fieldClass} />
            </div>
          </div>
        ))}
        <button type="button" disabled={busy} onClick={addMeeting} className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 disabled:opacity-40"><Plus size={15} />Adicionar preparatória</button>
      </section>

      <section className="space-y-3" aria-labelledby="edit-assessment-title">
        <h4 id="edit-assessment-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Pós-Encontro</h4>
        <input aria-label="Data da avaliação" type="date" value={draft.assessmentDate} onChange={(event) => setDraft((current) => ({ ...current, assessmentDate: event.target.value }))} className={fieldClass} />
      </section>

      <footer className="sticky bottom-0 z-10 flex flex-wrap justify-end gap-3 border-t border-slate-200 bg-white py-4">
        <button type="button" disabled={busy} onClick={cancel} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40">Cancelar</button>
        <button type="submit" disabled={busy || !dirty} className="rounded-lg bg-blue-700 px-5 py-2 text-sm font-bold text-white hover:bg-blue-800 disabled:opacity-40">{saving ? "Salvando..." : "Salvar alterações"}</button>
      </footer>

      <section className="flex flex-wrap gap-2 border-t border-slate-200 pt-4" aria-label="Lifecycle do Encontro">
        {encounter.status === "em_agendamento" ? <button type="button" disabled={busy || dirty} onClick={() => void lifecycleCommand("officialize", `${base}/oficializar/`)} className="rounded-lg bg-blue-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40">Oficializar agenda</button> : null}
        {(encounter.status === "agendado" || encounter.status === "em_preparacao") ? <button type="button" disabled={busy || dirty} onClick={() => void lifecycleCommand("postpone", `${base}/adiar/`)} className="rounded-lg border border-amber-300 px-3 py-2 text-sm font-semibold text-amber-800 disabled:opacity-40">Adiar</button> : null}
        {!['finalizado', 'cancelado'].includes(encounter.status) ? <button type="button" disabled={busy || dirty} onClick={() => void lifecycleCommand("cancel", `${base}/cancelar/`)} className="rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 disabled:opacity-40">Cancelar Encontro</button> : null}
      </section>
    </form>
  );
}
