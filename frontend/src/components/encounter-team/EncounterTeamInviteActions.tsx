"use client";

import { useEffect, useRef, useState } from "react";
import { parseEligibilityError, parseInvitePage } from "../../lib/encounter-team/encounter-team-contract";
import { siaFetch } from "../../lib/sia-api";

type Invite = ReturnType<typeof parseInvitePage>["results"][number];
type Answer = "confirmado" | "recusado" | "sem_resposta";
const answerDescription: Record<Answer, string> = { confirmado: "confirmar a resposta", recusado: "registrar a recusa", sem_resposta: "registrar que não houve resposta" };
export function EncounterTeamInviteActions({ invite, refresh, onAnswered }: { invite: Invite; refresh: () => void; onAnswered?: (status: Answer) => void }) {
  const busy = useRef(false);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const confirmButton = useRef<HTMLButtonElement | null>(null);
  const [saving, setSaving] = useState(false);
  const [pendingAnswer, setPendingAnswer] = useState<Answer | null>(null);
  const [localAnswer, setLocalAnswer] = useState<Answer | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [assessment, setAssessment] = useState<ReturnType<typeof parseEligibilityError> | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (pendingAnswer) confirmButton.current?.focus();
    else if (trigger.current) { trigger.current.focus(); trigger.current = null; }
  }, [pendingAnswer]);
  const currentStatus = localAnswer ?? invite.status;
  const blocked = assessment?.resultado === "BLOQUEIO" || assessment?.motivos.some((m) => m.categoria === "BLOQUEIO");
  async function submit(kind: "confirmado" | "recusado" | "sem_resposta" | "start", confirm = false) {
    if (busy.current || (kind !== "start" && kind !== pendingAnswer) || (confirm && !confirmed)) return;
    busy.current = true; setSaving(true); setMessage("");
    try {
      const path = kind === "start" ? "/trabalhos-encontros/" : `/convites-encontros/${invite.id}/responder-trabalho/`;
      const body = kind === "start" ? { convite_id: invite.id, ...(confirm ? { confirmar_avisos: true } : {}) } : { status: kind };
      const response = await siaFetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data: unknown = await response.json();
      if (!response.ok) {
        try { setAssessment(parseEligibilityError(data)); setConfirmed(false); return; } catch { /* Outro erro de domínio. */ }
        const detail = JSON.stringify(data);
        setMessage(detail.includes("quantidade estrutural") ? "A função proposta está sem vagas. A resposta permanece confirmada e o trabalho não foi iniciado." : "Não foi possível concluir a operação. Atualize a lista e tente novamente.");
        return;
      }
      setAssessment(null); setConfirmed(false);
      if (kind !== "start") { trigger.current = null; setLocalAnswer(kind); setPendingAnswer(null); onAnswered?.(kind); }
      setMessage(kind === "start" ? "Trabalho iniciado." : "Resposta registrada.");
    } catch { setMessage("Não foi possível concluir a operação. Atualize a lista e tente novamente."); }
    finally { refresh(); busy.current = false; setSaving(false); }
  }
  return <div className="mt-3 space-y-2">
    {currentStatus === "convidado" && <><div className="flex flex-wrap gap-2">{([["confirmado", "Confirmar resposta"], ["recusado", "Registrar recusa"], ["sem_resposta", "Registrar que não houve resposta (definitivo)"]] as const).map(([answer, label]) => <button className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50" key={answer} type="button" disabled={saving || pendingAnswer !== null} onClick={(event) => { trigger.current = event.currentTarget; setPendingAnswer(answer); }}>{label}</button>)}</div>{pendingAnswer && <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="dialog" aria-label="Confirmar resposta definitiva" onKeyDown={(event) => { if (event.key === "Escape" && !busy.current) { event.preventDefault(); setPendingAnswer(null); } }}><p>Você escolheu {answerDescription[pendingAnswer]}. O registro é DEFINITIVO e não pode ser alterado pelo fluxo atual.</p><p>Esta operação não envia mensagem à pessoa.</p><button className="mr-2 rounded-lg bg-escalada-azul px-3 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50" ref={confirmButton} type="button" disabled={saving} onClick={() => void submit(pendingAnswer)}>Confirmar registro definitivo</button><button className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50" type="button" disabled={saving} onClick={() => setPendingAnswer(null)}>Cancelar</button></div>}</>}
    {currentStatus === "confirmado" && invite.trabalho_id === null && <><p>Confirmado sem trabalho. {invite.role_trabalho_proposta_id === null ? "Ao iniciar, aguardará alocação." : "Ao iniciar, a pessoa poderá ser alocada automaticamente na função proposta."}</p><button className="rounded-lg bg-escalada-azul px-3 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50" type="button" disabled={saving || !!blocked} onClick={() => void submit("start")}>Iniciar trabalho</button></>}
    {localAnswer && localAnswer !== "confirmado" && <p role="status">{localAnswer === "recusado" ? "Resposta: Recusado" : "Resposta: Sem resposta"}</p>}
    {invite.trabalho_id !== null && <p>Trabalho: {invite.trabalho_status === "aguardando_alocacao" ? "Aguardando alocação" : invite.trabalho_status === "alocado" ? "Alocado" : invite.trabalho_status}</p>}
    {assessment && <div className={blocked ? "space-y-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" : "space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"} role="alert"><strong>{blocked ? "Bloqueios" : "Avisos"}</strong>{assessment.motivos.some((m) => m.codigo === "QUANTIDADE_ESTRUTURAL_EXCEDIDA") && <p>A função proposta está sem vagas. A resposta permanece confirmada e o trabalho não foi iniciado.</p>}<ul>{assessment.motivos.map((m, i) => <li key={i}>{m.mensagem} ({m.codigo})</li>)}</ul>{!blocked && <><label><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} /> Confirmo os avisos</label><button className="ml-2 rounded-lg bg-escalada-azul px-3 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50" type="button" disabled={!confirmed || saving} onClick={() => void submit("start", true)}>Iniciar com confirmação</button></>}</div>}
    {message && <p role="status">{message}</p>}
  </div>;
}
