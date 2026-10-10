"use client";

import { useEffect, useRef, useState } from "react";

import {
  submitPublicInvitation,
  type PublicInvitation as Invitation,
  type PublicInvitationAction,
} from "../lib/public-invitation";

function civilDateLabel(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value;
}

function InvitationDetails({ invitation }: { invitation: Invitation }) {
  return <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
    <h2 className="text-xl font-bold text-slate-950">{invitation.titulo_encontro}</h2>
    <p className="mt-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Convite para participar</p>
    <p className="mt-3 text-slate-700">Datas: {invitation.datas_encontro.map(civilDateLabel).join(", ")}</p>
    <p className="mt-2 text-sm text-slate-600">Prazo: {new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(invitation.prazo_resposta))}</p>
  </div>;
}

export function PublicInvitation({ token }: { token: string }) {
  const [birthDate, setBirthDate] = useState("");
  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirmingRefusal, setConfirmingRefusal] = useState(false);
  const feedbackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (error) feedbackRef.current?.focus();
  }, [error]);

  async function perform(action: PublicInvitationAction) {
    if (!birthDate) {
      setError("Informe sua data de nascimento.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await submitPublicInvitation(token, birthDate, action);
      if (result.success === true) {
        setInvitation(result.convite);
        setConfirmingRefusal(false);
      } else {
        setError(result.message);
      }
    } finally {
      setLoading(false);
    }
  }

  const authenticated = invitation !== null;
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
    <section className="w-full max-w-xl rounded-3xl border border-slate-200 bg-white p-6 shadow-lg sm:p-9" aria-busy={loading}>
      <p className="text-sm font-bold uppercase tracking-widest text-blue-700">Movimento Escalada de Brasília</p>
      <h1 className="mt-2 text-3xl font-black text-slate-950">Resposta ao convite</h1>
      {!authenticated ? <form className="mt-7" onSubmit={(event) => { event.preventDefault(); void perform("validar"); }} noValidate>
        <p className="text-slate-600">Para acessar o convite, confirme sua data de nascimento.</p>
        <label htmlFor="birth-date" className="mt-5 block font-semibold text-slate-800">Data de nascimento</label>
        <input id="birth-date" type="date" required value={birthDate} onChange={(event) => { setBirthDate(event.target.value); setError(""); }} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-4 text-slate-950" />
        <button type="submit" disabled={loading} className="mt-5 min-h-12 w-full rounded-xl bg-blue-800 px-6 font-bold text-white disabled:bg-slate-400">{loading ? "Validando…" : "Acessar convite"}</button>
      </form> : <>
        <InvitationDetails invitation={invitation} />
        <div role="status" className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4 text-blue-950">{invitation.mensagem}</div>
        {invitation.pode_responder ? <>
          <p className="mt-5 text-sm text-slate-600">Confirmar registra sua resposta ao convite. A presença efetiva no Encontro será registrada separadamente.</p>
          {!confirmingRefusal ? <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
            <button type="button" disabled={loading} onClick={() => setConfirmingRefusal(true)} className="min-h-12 rounded-xl border border-red-700 px-6 font-bold text-red-700">Recusar</button>
            <button type="button" disabled={loading} onClick={() => void perform("confirmar")} className="min-h-12 rounded-xl bg-blue-800 px-6 font-bold text-white disabled:bg-slate-400">{loading ? "Registrando…" : "Confirmar convite"}</button>
          </div> : <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-5">
            <p className="font-bold text-red-900">Você confirma que deseja recusar este convite?</p>
            <p className="mt-2 text-sm text-red-800">A recusa é final para esta oportunidade.</p>
            <div className="mt-4 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button type="button" onClick={() => setConfirmingRefusal(false)} className="min-h-11 rounded-xl border border-slate-400 px-5 font-semibold">Voltar</button>
              <button type="button" disabled={loading} onClick={() => void perform("recusar")} className="min-h-11 rounded-xl bg-red-700 px-5 font-bold text-white disabled:bg-slate-400">{loading ? "Registrando…" : "Sim, recusar convite"}</button>
            </div>
          </div>}
        </> : null}
      </>}
      {error ? <div ref={feedbackRef} tabIndex={-1} role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-red-900">{error}</div> : null}
    </section>
  </main>;
}
