"use client";

import { useEffect, useRef, useState, type Ref } from "react";
import {
  emptyPublicRegistrationValues,
  finalizePublicRegistration,
  formatCepInput,
  loadPublicRegistration,
  validatePublicRegistration,
  type PublicRegistrationEncounter,
  type PublicRegistrationErrors,
  type PublicRegistrationValues,
} from "../lib/public-registration-contract";
import { CareSection, ContactAddressSection, EsppaSection, IdentificationSection, OriginSacramentsSection, ResponsibleSection } from "./public-registration/PublicRegistrationSections";
import { PublicRegistrationReview } from "./public-registration/PublicRegistrationReview";

type LoadState = "loading" | "ready" | "not-found" | "not-open" | "closed" | "temporary";

export function createSingleSubmissionGuard() {
  let inFlight = false;
  return async function run<T>(operation: () => Promise<T>): Promise<T | undefined> {
    if (inFlight) return undefined;
    inFlight = true;
    try {
      return await operation();
    } finally {
      inFlight = false;
    }
  };
}

function closedState(encounter: PublicRegistrationEncounter): LoadState {
  if (encounter.inscricoes_abertas) return "ready";
  const opensAt = Date.parse(encounter.inscricoes_abrem_em);
  return Number.isFinite(opensAt) && Date.now() < opensAt ? "not-open" : "closed";
}

export function PublicRegistrationStatusCard({ state }: { state: Exclude<LoadState, "ready"> }) {
  const content = {
    loading: ["Carregando ficha", "Estamos consultando a disponibilidade das inscrições."],
    "not-found": ["Ficha indisponível", "Este Encontro não está disponível para inscrição por este endereço."],
    "not-open": ["Inscrições ainda não abertas", "A ficha estará disponível quando o período de inscrições começar."],
    closed: ["Inscrições encerradas", "O período público de inscrições para este Encontro terminou."],
    temporary: ["Serviço temporariamente indisponível", "Tente novamente em alguns instantes."],
  }[state];
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4"><section role="status" className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-lg"><div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-blue-700 text-xl font-black text-white">MEB</div><h1 className="text-2xl font-bold text-slate-950">{content[0]}</h1><p className="mt-3 text-slate-600">{content[1]}</p></section></main>;
}

export function PublicRegistrationSuccess() {
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4"><section role="status" className="w-full max-w-xl rounded-3xl border border-emerald-200 bg-white p-8 text-center shadow-lg"><div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-600 text-2xl text-white">✓</div><h1 className="text-2xl font-bold text-slate-950">Inscrição recebida com sucesso.</h1><p className="mt-3 text-slate-600">Agora aguarde o contato ou convite do Movimento Escalada.</p></section></main>;
}

export function PublicSubmissionFeedback({ message, feedbackRef }: { message: string; feedbackRef?: Ref<HTMLDivElement> }) {
  return <div ref={feedbackRef} tabIndex={-1} role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{message}</div>;
}

export function PublicRegistrationForm({ publicId }: { publicId: string }) {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [encounter, setEncounter] = useState<PublicRegistrationEncounter | null>(null);
  const [values, setValues] = useState(emptyPublicRegistrationValues);
  const [errors, setErrors] = useState<PublicRegistrationErrors>({});
  const [reviewing, setReviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const errorSummaryRef = useRef<HTMLDivElement>(null);
  const submitFeedbackRef = useRef<HTMLDivElement>(null);
  const submissionGuardRef = useRef(createSingleSubmissionGuard());

  useEffect(() => {
    const controller = new AbortController();
    void loadPublicRegistration(publicId, controller.signal).then(({ response, encounter: loaded }) => {
      if (response.status === 404) return setLoadState("not-found");
      if (!response.ok || !loaded) return setLoadState("temporary");
      setEncounter(loaded);
      setLoadState(closedState(loaded));
    }).catch((error: unknown) => {
      if (!(error instanceof DOMException && error.name === "AbortError")) setLoadState("temporary");
    });
    return () => controller.abort();
  }, [publicId]);

  useEffect(() => {
    if (submitError) submitFeedbackRef.current?.focus();
  }, [submitError]);

  function change(key: keyof PublicRegistrationValues, value: string) {
    const nextValue = key === "cep" ? formatCepInput(value) : value;
    setValues((current) => {
      const next = { ...current, [key]: nextValue };
      if (key === "possui_alergias" && nextValue === "nao") next.alergias = "";
      if (key === "possui_restricoes_intolerancias" && nextValue === "nao") next.restricoes_intolerancias = "";
      if (key === "usa_medicamentos" && nextValue === "nao") {
        next.medicamentos = ""; next.horarios_medicamentos = ""; next.observacoes_medicamentos = "";
      }
      if (key === "neurodivergencia_apoio" && nextValue !== "sim") {
        next.neurodivergencia_condicao = ""; next.necessidades_apoio = "";
        next.sensibilidades_desconfortos = ""; next.o_que_ajuda = ""; next.outras_informacoes = "";
      }
      if (key === "como_conheceu" && nextValue !== "outro") next.como_conheceu_outro = "";
      if (key === "estado_civil") {
        if (nextValue === "casado") { next.nome_referencia = ""; next.relacao_referencia = ""; next.telefone_referencia = ""; }
        else { next.nome_conjuge = ""; next.telefone_conjuge = ""; }
      }
      return next;
    });
    setErrors((current) => ({ ...current, [key]: undefined }));
  }

  function openReview(event: React.FormEvent) {
    event.preventDefault();
    if (!encounter) return;
    const nextErrors = validatePublicRegistration(values, encounter);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      const firstField = Object.keys(nextErrors)[0];
      requestAnimationFrame(() => {
        const target = document.getElementById(firstField);
        if (target instanceof HTMLElement) target.focus();
        else errorSummaryRef.current?.focus();
      });
      return;
    }
    setSubmitError("");
    setReviewing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function finalize() {
    if (!encounter || submitted) return;
    const latestErrors = validatePublicRegistration(values, encounter);
    if (Object.keys(latestErrors).length) {
      const firstField = Object.keys(latestErrors)[0];
      setErrors(latestErrors);
      setSubmitError("Corrija os campos destacados antes de finalizar a inscrição.");
      setReviewing(false);
      requestAnimationFrame(() => requestAnimationFrame(() => {
        const target = document.getElementById(firstField);
        if (target instanceof HTMLElement) target.focus();
        else errorSummaryRef.current?.focus();
      }));
      return;
    }
    await submissionGuardRef.current(async () => {
      setSubmitting(true);
      setSubmitError("");
      try {
        const result = await finalizePublicRegistration(publicId, values, encounter);
        if (result.success === true) {
          setSubmitted(true);
        } else {
          setSubmitError(result.message);
          if (result.status === 400) setReviewing(false);
        }
      } catch {
        setSubmitError("Não foi possível enviar agora. Verifique sua conexão e tente novamente.");
      } finally {
        setSubmitting(false);
      }
    });
  }

  if (loadState !== "ready" || !encounter) return <PublicRegistrationStatusCard state={loadState === "ready" ? "temporary" : loadState} />;
  if (submitted) return <PublicRegistrationSuccess />;

  return <main className="min-h-screen bg-slate-50 pb-16">
    <header className="border-b-4 border-red-600 bg-blue-800 text-white"><div className="mx-auto max-w-4xl px-4 py-8 sm:px-6"><p className="text-sm font-bold uppercase tracking-widest text-blue-100">Movimento Escalada de Brasília</p><h1 className="mt-2 text-3xl font-black sm:text-4xl">{encounter.titulo}</h1><p className="mt-2 text-blue-100">Ficha de inscrição — {encounter.tipo}</p></div></header>
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {reviewing ? <>
        <PublicRegistrationReview values={values} encounter={encounter} />
        {submitError ? <PublicSubmissionFeedback message={submitError} feedbackRef={submitFeedbackRef} /> : null}
        <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
          <button type="button" onClick={() => { setReviewing(false); setSubmitError(""); }} disabled={submitting} className="min-h-12 rounded-xl border border-blue-700 px-6 font-bold text-blue-800 hover:bg-blue-50 disabled:opacity-60">Voltar e editar</button>
          <button type="button" onClick={() => void finalize()} disabled={submitting} className="min-h-12 rounded-xl bg-red-600 px-6 font-bold text-white shadow hover:bg-red-700 disabled:cursor-wait disabled:bg-slate-400">{submitting ? "Enviando…" : "Finalizar inscrição"}</button>
        </div>
      </> : <form onSubmit={openReview} noValidate className="space-y-6">
        {submitError ? <PublicSubmissionFeedback message={submitError} feedbackRef={submitFeedbackRef} /> : null}
        {Object.keys(errors).length ? <div ref={errorSummaryRef} tabIndex={-1} role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"><p className="font-bold">Revise os campos destacados.</p><p className="mt-1 text-sm">Há informações obrigatórias ou condicionais que precisam ser preenchidas.</p></div> : null}
        <IdentificationSection values={values} errors={errors} encounter={encounter} change={change} />
        <ContactAddressSection values={values} errors={errors} encounter={encounter} change={change} />
        <ResponsibleSection values={values} errors={errors} encounter={encounter} change={change} />
        <OriginSacramentsSection values={values} errors={errors} encounter={encounter} change={change} />
        <CareSection values={values} errors={errors} encounter={encounter} change={change} />
        <EsppaSection values={values} errors={errors} encounter={encounter} change={change} />
        <div className="rounded-2xl bg-slate-900 p-5 text-white sm:flex sm:items-center sm:justify-between"><p className="mb-4 text-sm text-slate-300 sm:mb-0">Você poderá revisar tudo antes do envio.</p><button type="submit" className="min-h-12 w-full rounded-xl bg-red-600 px-7 font-bold hover:bg-red-700 sm:w-auto">Revisar inscrição</button></div>
      </form>}
    </div>
  </main>;
}
