"use client";

import { useMemo, useState } from "react";
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
}

const fieldClass = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100";

export function CalendarEncounterEditor({ encounter, agenda, onChanged }: CalendarEncounterEditorProps) {
  const days = useMemo(() => agenda.filter((item) => item.origem === "DIA_ENCONTRO"), [agenda]);
  const meetings = useMemo(() => agenda.filter((item) => item.origem === "REUNIAO_PREPARATORIA"), [agenda]);
  const assessment = agenda.find((item) => item.origem === "AVALIACAO") ?? null;
  const [title, setTitle] = useState(encounter.titulo);
  const [location, setLocation] = useState("");
  const [dayDrafts, setDayDrafts] = useState(() => days.map((item) => ({ data: item.data, rotulo: item.subtitulo ? item.titulo : "" })));
  const [meetingDrafts, setMeetingDrafts] = useState(() => meetings.map((item) => ({ id: item.origem_id, data: item.data, complemento: item.subtitulo ?? "" })));
  const [newMeeting, setNewMeeting] = useState({ data: "", horario: "19:30", local: "", complemento: "" });
  const [assessmentDate, setAssessmentDate] = useState(assessment?.data ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<number>(0);

  const command = async (key: string, path: string, method: string, body?: unknown) => {
    setBusy(key);
    setError(null);
    try {
      const response = await siaFetch(path, {
        method,
        headers: body === undefined ? undefined : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível alterar o calendário."));
      if (response.status !== 204) {
        const responseBody: { avisos_conflito?: unknown[] } = await response.json();
        setWarnings(responseBody.avisos_conflito?.length ?? 0);
      } else setWarnings(0);
      await onChanged();
      return true;
    } catch (caught: unknown) {
      setError(errorMessage(caught, "Não foi possível alterar o calendário."));
      return false;
    } finally {
      setBusy(null);
    }
  };

  const base = `/calendario-institucional/encontros/${encounter.encontro_id}`;
  const saveBasic = () => command("basic", `${base}/dados-basicos/`, "PATCH", {
    ...(title.trim() !== encounter.titulo ? { encontro: title.trim() } : {}),
    ...(location.trim() ? { local: location.trim() } : {}),
  });
  const saveDays = () => command(
    "days",
    encounter.status === "em_agendamento" ? `${base}/planejamento/` : `${base}/reprogramar/`,
    encounter.status === "em_agendamento" ? "PATCH" : "POST",
    { dias: dayDrafts.map((item, index) => ({ ordem: index + 1, data: item.data, rotulo: item.rotulo.trim() })) },
  );

  return (
    <div className="space-y-6 border-t border-slate-200 pt-5">
      <div>
        <h3 className="font-bold text-slate-900">Editar calendário</h3>
        <p className="mt-1 text-sm text-slate-500">Comandos canônicos respeitam o lifecycle do Encontro.</p>
      </div>
      {error ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {warnings > 0 ? <p className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><AlertTriangle size={17} className="shrink-0" />Existe outro compromisso em {warnings} data(s). O aviso não bloqueou a alteração.</p> : null}

      <section className="space-y-3" aria-labelledby="edit-basic-title">
        <h4 id="edit-basic-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Dados básicos</h4>
        <label className="block text-xs font-semibold text-slate-600">Nome<input value={title} onChange={(event) => setTitle(event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <label className="block text-xs font-semibold text-slate-600">Novo local (opcional)<input value={location} onChange={(event) => setLocation(event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <button type="button" disabled={busy !== null || (!location.trim() && title.trim() === encounter.titulo)} onClick={() => void saveBasic()} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40">Salvar dados</button>
      </section>

      {(encounter.status === "em_agendamento" || encounter.status === "agendado" || encounter.status === "adiado") ? (
        <section className="space-y-3" aria-labelledby="edit-days-title">
          <h4 id="edit-days-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Dias do Encontro</h4>
          {dayDrafts.map((day, index) => (
            <div key={index} className="grid grid-cols-[1fr_1fr_auto] gap-2">
              <input aria-label={`Data ${index + 1}`} type="date" value={day.data} onChange={(event) => setDayDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, data: event.target.value } : item))} className={fieldClass} />
              <input aria-label={`Rótulo ${index + 1}`} value={day.rotulo} onChange={(event) => setDayDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, rotulo: event.target.value } : item))} className={fieldClass} />
              <button type="button" aria-label={`Remover dia ${index + 1}`} disabled={dayDrafts.length === 1} onClick={() => setDayDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="rounded-lg p-2 text-red-600 hover:bg-red-50 disabled:opacity-30"><Trash2 size={17} /></button>
            </div>
          ))}
          <button type="button" onClick={() => setDayDrafts((current) => [...current, { data: "", rotulo: "" }])} className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700"><Plus size={15} />Adicionar data</button>
          <div><button type="button" disabled={busy !== null || dayDrafts.length === 0} onClick={() => void saveDays()} className="rounded-lg bg-blue-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40">{encounter.status === "em_agendamento" ? "Salvar planejamento" : "Reprogramar agenda"}</button></div>
        </section>
      ) : null}

      <section className="space-y-3" aria-labelledby="edit-meetings-title">
        <h4 id="edit-meetings-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Preparação</h4>
        {meetingDrafts.map((meeting, index) => (
          <div key={meeting.id} className="space-y-2 rounded-lg border border-slate-200 p-3">
            <p className="text-sm font-semibold">{index + 1}ª Preparatória</p>
            <div className="grid grid-cols-2 gap-2"><input aria-label={`Data da preparatória ${index + 1}`} type="date" value={meeting.data} onChange={(event) => setMeetingDrafts((current) => current.map((item) => item.id === meeting.id ? { ...item, data: event.target.value } : item))} className={fieldClass} /><input aria-label={`Complemento da preparatória ${index + 1}`} value={meeting.complemento} onChange={(event) => setMeetingDrafts((current) => current.map((item) => item.id === meeting.id ? { ...item, complemento: event.target.value } : item))} className={fieldClass} /></div>
            <button type="button" disabled={busy !== null || meeting.id === null} onClick={() => void command(`meeting-${meeting.id}`, `${base}/reunioes/${meeting.id}/`, "PATCH", { data: meeting.data, complemento: meeting.complemento.trim() })} className="text-sm font-semibold text-blue-700 disabled:opacity-40">Salvar preparatória</button>
          </div>
        ))}
        <div className="space-y-2 rounded-lg border border-dashed border-slate-300 p-3">
          <p className="text-sm font-semibold">Nova preparatória</p>
          <div className="grid grid-cols-2 gap-2"><input aria-label="Data da nova preparatória" type="date" value={newMeeting.data} onChange={(event) => setNewMeeting({ ...newMeeting, data: event.target.value })} className={fieldClass} /><input aria-label="Horário da nova preparatória" type="time" value={newMeeting.horario} onChange={(event) => setNewMeeting({ ...newMeeting, horario: event.target.value })} className={fieldClass} /><input aria-label="Local da nova preparatória" placeholder="Local" value={newMeeting.local} onChange={(event) => setNewMeeting({ ...newMeeting, local: event.target.value })} className={fieldClass} /><input aria-label="Complemento da nova preparatória" placeholder="Complemento" value={newMeeting.complemento} onChange={(event) => setNewMeeting({ ...newMeeting, complemento: event.target.value })} className={fieldClass} /></div>
          <button type="button" disabled={busy !== null || !newMeeting.data || !newMeeting.local} onClick={async () => {
            const nextOrder = Math.max(0, ...meetings.map((item) => Number.parseInt(item.titulo, 10) || 0)) + 1;
            const created = await command("new-meeting", `${base}/reunioes/`, "POST", { ordem: nextOrder, ...newMeeting });
            if (created) setNewMeeting({ data: "", horario: "19:30", local: "", complemento: "" });
          }} className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 disabled:opacity-40"><Plus size={15} />Criar preparatória</button>
        </div>
      </section>

      <section className="space-y-3" aria-labelledby="edit-assessment-title">
        <h4 id="edit-assessment-title" className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Pós-Encontro</h4>
        <input aria-label="Data da avaliação" type="date" value={assessmentDate} onChange={(event) => setAssessmentDate(event.target.value)} className={fieldClass} />
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={busy !== null || !assessmentDate} onClick={() => void command("assessment", `${base}/avaliacao/`, assessment ? "PATCH" : "POST", { data: assessmentDate })} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40">{assessment ? "Salvar avaliação" : "Criar avaliação"}</button>
          {assessment ? <button type="button" disabled={busy !== null} onClick={async () => {
            const removed = await command("assessment-delete", `${base}/avaliacao/`, "DELETE");
            if (removed) setAssessmentDate("");
          }} className="rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50">Remover avaliação</button> : null}
        </div>
      </section>

      <section className="flex flex-wrap gap-2 border-t border-slate-200 pt-4" aria-label="Lifecycle do Encontro">
        {encounter.status === "em_agendamento" ? <button type="button" disabled={busy !== null} onClick={() => void command("officialize", `${base}/oficializar/`, "POST", {})} className="rounded-lg bg-blue-700 px-3 py-2 text-sm font-semibold text-white">Oficializar agenda</button> : null}
        {(encounter.status === "agendado" || encounter.status === "em_preparacao") ? <button type="button" disabled={busy !== null} onClick={() => void command("postpone", `${base}/adiar/`, "POST", {})} className="rounded-lg border border-amber-300 px-3 py-2 text-sm font-semibold text-amber-800">Adiar</button> : null}
        {!["finalizado", "cancelado"].includes(encounter.status) ? <button type="button" disabled={busy !== null} onClick={() => void command("cancel", `${base}/cancelar/`, "POST", {})} className="rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700">Cancelar Encontro</button> : null}
      </section>
    </div>
  );
}
