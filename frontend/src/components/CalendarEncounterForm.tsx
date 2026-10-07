"use client";

import { useEffect, useRef, useState } from "react";
import { Plus, Trash2, X } from "lucide-react";
import toast from "react-hot-toast";

import { errorMessage, readApiError } from "../lib/form-api-error";
import { keepFocusInsideDialog } from "../lib/dialog-focus";
import {
  buildEncounterAgendaPayload,
  emptyEncounterAgendaForm,
  ESCALADA_DAY_SUGGESTIONS,
  type EncounterAgendaFormValues,
} from "../lib/institutional-calendar";
import { siaFetch } from "../lib/sia-api";

interface CalendarEncounterFormProps {
  open: boolean;
  initialDate?: string;
  onClose: () => void;
  onCreated: (warnings: number) => void;
}

const fieldClass = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-100";

export function CalendarEncounterForm({ open, initialDate = "", onClose, onCreated }: CalendarEncounterFormProps) {
  const [values, setValues] = useState<EncounterAgendaFormValues>(() => emptyEncounterAgendaForm(initialDate));
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const firstInput = useRef<HTMLInputElement>(null);
  const dialog = useRef<HTMLElement>(null);
  const savingRef = useRef(false);

  useEffect(() => {
    savingRef.current = saving;
  }, [saving]);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const focusTimer = window.setTimeout(() => firstInput.current?.focus(), 0);
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !savingRef.current) onClose();
      keepFocusInsideDialog(event, dialog.current);
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      window.clearTimeout(focusTimer);
      previous?.focus();
    };
  }, [initialDate, onClose, open]);

  if (!open) return null;

  const updateDay = (index: number, field: "data" | "rotulo", value: string) => {
    setValues((current) => ({
      ...current,
      dias: current.dias.map((day, dayIndex) => dayIndex === index ? { ...day, [field]: value } : day),
    }));
  };

  const updateMeeting = (index: number, field: "data" | "horario" | "local" | "complemento", value: string) => {
    setValues((current) => ({
      ...current,
      reunioes: current.reunioes.map((meeting, meetingIndex) => meetingIndex === index
        ? { ...meeting, [field]: value }
        : meeting),
    }));
  };

  const addDay = () => setValues((current) => ({
    ...current,
    dias: [
      ...current.dias,
      {
        data: "",
        rotulo: current.tipo === "Escalada"
          ? (ESCALADA_DAY_SUGGESTIONS[current.dias.length] ?? "")
          : "",
      },
    ],
  }));

  const addMeeting = () => setValues((current) => ({
    ...current,
    reunioes: [...current.reunioes, { data: "", horario: "19:30", local: current.local, complemento: "" }],
  }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      const response = await siaFetch("/calendario-institucional/encontros/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildEncounterAgendaPayload(values)),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível criar o Encontro."));
      const body: { avisos_conflito?: unknown[] } = await response.json();
      const warnings = body.avisos_conflito?.length ?? 0;
      toast.success("Encontro e Agenda criados.");
      onCreated(warnings);
      onClose();
    } catch (error: unknown) {
      setFormError(errorMessage(error, "Não foi possível criar o Encontro."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-stretch justify-end bg-slate-950/45" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !saving) onClose();
    }}>
      <section ref={dialog} role="dialog" aria-modal="true" aria-labelledby="new-calendar-encounter" tabIndex={-1} className="h-full w-full max-w-2xl overflow-y-auto bg-white shadow-2xl">
        <form onSubmit={submit} className="min-h-full">
          <header className="sticky top-0 z-10 flex items-start justify-between border-b border-slate-200 bg-white/95 px-5 py-4 backdrop-blur">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-700">Novo compromisso</p>
              <h2 id="new-calendar-encounter" className="mt-1 text-2xl font-bold text-slate-950">Encontro com Agenda completa</h2>
            </div>
            <button type="button" onClick={onClose} disabled={saving} aria-label="Fechar formulário" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"><X /></button>
          </header>

          <div className="space-y-8 p-5 sm:p-7">
            {formError ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{formError}</p> : null}

            <fieldset className="space-y-4">
              <legend className="text-sm font-bold uppercase tracking-[0.16em] text-slate-500">Dados do Encontro</legend>
              <div>
                <label htmlFor="calendar-encounter-name" className="mb-1 block text-sm font-semibold text-slate-700">Nome</label>
                <input ref={firstInput} id="calendar-encounter-name" required value={values.encontro} onChange={(event) => setValues({ ...values, encontro: event.target.value })} className={fieldClass} placeholder="Ex.: Escalada 2027" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="calendar-encounter-type" className="mb-1 block text-sm font-semibold text-slate-700">Tipo</label>
                  <select id="calendar-encounter-type" value={values.tipo} onChange={(event) => setValues({ ...values, tipo: event.target.value as EncounterAgendaFormValues["tipo"] })} className={fieldClass}>
                    <option>Escalada</option><option>AVC</option><option>Esppa</option><option>Acampamento</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="calendar-encounter-location" className="mb-1 block text-sm font-semibold text-slate-700">Local</label>
                  <input id="calendar-encounter-location" required value={values.local} onChange={(event) => setValues({ ...values, local: event.target.value })} className={fieldClass} />
                </div>
              </div>
            </fieldset>

            <fieldset className="space-y-3">
              <legend className="text-sm font-bold uppercase tracking-[0.16em] text-slate-500">Dias do Encontro</legend>
              <p className="text-sm text-slate-500">Os rótulos são sugestões editáveis.</p>
              {values.dias.map((day, index) => (
                <div key={index} className="grid gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-[1fr_1.2fr_auto]">
                  <label className="text-xs font-semibold text-slate-600">Data {index + 1}<input aria-label={`Data do Encontro ${index + 1}`} required type="date" value={day.data} onChange={(event) => updateDay(index, "data", event.target.value)} className={`${fieldClass} mt-1`} /></label>
                  <label className="text-xs font-semibold text-slate-600">Rótulo<input aria-label={`Rótulo do dia ${index + 1}`} value={day.rotulo} onChange={(event) => updateDay(index, "rotulo", event.target.value)} className={`${fieldClass} mt-1`} /></label>
                  <button type="button" aria-label={`Remover data ${index + 1}`} disabled={values.dias.length === 1} onClick={() => setValues({ ...values, dias: values.dias.filter((_, itemIndex) => itemIndex !== index) })} className="self-end rounded-lg p-2 text-red-600 hover:bg-red-50 disabled:opacity-30"><Trash2 size={18} /></button>
                </div>
              ))}
              <button type="button" onClick={addDay} className="inline-flex items-center gap-2 rounded-lg border border-blue-200 px-3 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50"><Plus size={16} />Adicionar data</button>
            </fieldset>

            <fieldset className="space-y-3">
              <legend className="text-sm font-bold uppercase tracking-[0.16em] text-slate-500">Preparatórias</legend>
              {values.reunioes.length === 0 ? <p className="text-sm text-slate-500">Nenhuma preparatória.</p> : null}
              {values.reunioes.map((meeting, index) => (
                <div key={index} className="rounded-xl border border-slate-200 p-3">
                  <div className="mb-3 flex items-center justify-between"><h3 className="font-semibold text-slate-800">{index + 1}ª Preparatória</h3><button type="button" aria-label={`Remover preparatória ${index + 1}`} onClick={() => setValues({ ...values, reunioes: values.reunioes.filter((_, itemIndex) => itemIndex !== index) })} className="rounded-lg p-2 text-red-600 hover:bg-red-50"><Trash2 size={18} /></button></div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="text-xs font-semibold text-slate-600">Data<input required aria-label={`Data da preparatória ${index + 1}`} type="date" value={meeting.data} onChange={(event) => updateMeeting(index, "data", event.target.value)} className={`${fieldClass} mt-1`} /></label>
                    <label className="text-xs font-semibold text-slate-600">Horário<input required aria-label={`Horário da preparatória ${index + 1}`} type="time" value={meeting.horario} onChange={(event) => updateMeeting(index, "horario", event.target.value)} className={`${fieldClass} mt-1`} /></label>
                    <label className="text-xs font-semibold text-slate-600">Local<input required aria-label={`Local da preparatória ${index + 1}`} value={meeting.local} onChange={(event) => updateMeeting(index, "local", event.target.value)} className={`${fieldClass} mt-1`} /></label>
                    <label className="text-xs font-semibold text-slate-600">Complemento opcional<input aria-label={`Complemento da preparatória ${index + 1}`} value={meeting.complemento} onChange={(event) => updateMeeting(index, "complemento", event.target.value)} className={`${fieldClass} mt-1`} placeholder="Ex.: Missa de Entrega" /></label>
                  </div>
                </div>
              ))}
              <button type="button" onClick={addMeeting} className="inline-flex items-center gap-2 rounded-lg border border-blue-200 px-3 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50"><Plus size={16} />Adicionar preparatória</button>
            </fieldset>

            <fieldset>
              <legend className="text-sm font-bold uppercase tracking-[0.16em] text-slate-500">Pós-Encontro</legend>
              <label className="mt-3 block text-sm font-semibold text-slate-700">Avaliação opcional<input type="date" value={values.avaliacaoData} onChange={(event) => setValues({ ...values, avaliacaoData: event.target.value })} className={`${fieldClass} mt-1 max-w-xs`} /></label>
            </fieldset>
          </div>

          <footer className="sticky bottom-0 flex justify-end gap-3 border-t border-slate-200 bg-white px-5 py-4">
            <button type="button" onClick={onClose} disabled={saving} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-blue-700 px-5 py-2 text-sm font-bold text-white hover:bg-blue-800 disabled:opacity-60">{saving ? "Criando..." : "Criar Encontro"}</button>
          </footer>
        </form>
      </section>
    </div>
  );
}
