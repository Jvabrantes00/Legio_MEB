"use client";

import { useEffect, useRef, useState } from "react";
import { buildWorkActionBody, buildWorkActionPath, parseEligibilityError, type EncounterTeam, type WorkAction } from "../../lib/encounter-team/encounter-team-contract";
import { siaFetch } from "../../lib/sia-api";

export function EncounterTeamWorkActions({ trabalhoId, teams, currentRoleId, disabled, onBusy, refresh }: { trabalhoId: number; teams: EncounterTeam[]; currentRoleId?: number; disabled?: boolean; onBusy?: (busy: boolean) => boolean; refresh?: () => void }) {
  const [action, setAction] = useState<WorkAction | null>(null);
  const [roleId, setRoleId] = useState("");
  const [assessment, setAssessment] = useState<ReturnType<typeof parseEligibilityError> | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const busy = useRef(false);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const confirm = useRef<HTMLButtonElement | null>(null);
  const roles = teams.flatMap((team) => team.roles.map((role) => ({ ...role, team: team.nome })));
  const current = roles.find((role) => role.id === currentRoleId);
  const selected = roles.find((role) => String(role.id) === roleId);
  const blocked = assessment?.resultado === "BLOQUEIO" || assessment?.motivos.some((reason) => reason.categoria === "BLOQUEIO");
  useEffect(() => { if (action) confirm.current?.focus(); else if (trigger.current) { trigger.current.focus(); trigger.current = null; } }, [action]);
  function close() { if (!busy.current) { setAction(null); setAssessment(null); setConfirmed(false); setMessage(""); setRoleId(""); } }
  async function submit() {
    if (!action || busy.current || disabled || blocked || (action !== "desalocar" && !selected) || (assessment && !confirmed)) return;
    if (onBusy?.(true) === false) return;
    busy.current = true; setSaving(true); setMessage("");
    try {
      const response = await siaFetch(buildWorkActionPath(trabalhoId, action), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(buildWorkActionBody(action, selected?.id, !!assessment)) });
      const data: unknown = await response.json();
      if (!response.ok) {
        if (response.status === 403) { setMessage("Você não tem permissão para alterar este trabalho."); return; }
        if (response.status === 400) {
          try { setAssessment(parseEligibilityError(data)); setConfirmed(false); return; } catch { /* Erro simples de domínio. */ }
          const errors = data && typeof data === "object" ? (data as Record<string, unknown>).non_field_errors : null;
          if (Array.isArray(errors) && errors.every((item) => typeof item === "string")) { setMessage(errors.join(" ")); return; }
        }
        setMessage("Não foi possível concluir a operação."); return;
      }
      setAction(null); setAssessment(null); setConfirmed(false); setRoleId(""); setMessage("Operação concluída.");
    } catch { setMessage("Não foi possível contatar o servidor."); }
    finally { refresh?.(); busy.current = false; onBusy?.(false); setSaving(false); }
  }
  return <div className="mt-2 space-y-2">
    {(currentRoleId === undefined ? [["alocar", "Alocar"]] : [["realocar", "Realocar"], ["desalocar", "Desalocar"]]).map(([kind, label]) => <button key={kind} type="button" disabled={disabled || saving || action !== null} className="mr-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold disabled:opacity-50" onClick={(event) => { trigger.current = event.currentTarget; setAction(kind as WorkAction); setMessage(""); }}>{label}</button>)}
    {action && <div role="dialog" aria-label={`Confirmar ${action}`} className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm" onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); close(); } }}>
      {action !== "desalocar" && <label>Função <select value={roleId} disabled={saving || !!assessment} onChange={(event) => setRoleId(event.target.value)}><option value="">Selecione</option>{roles.filter((role) => role.id !== currentRoleId).map((role) => { const occupied = role.trabalhos.filter((work) => work.status === "alocado").length; return <option key={role.id} value={role.id}>{role.team} — {role.nome} (ocupação: {occupied} / vagas estruturais: {role.quantidade_estrutural ?? "não definidas"})</option>; })}</select></label>}
      {action === "realocar" && <p>De {current ? `${current.team} — ${current.nome}` : "função atual"} para {selected ? `${selected.team} — ${selected.nome}` : "a função selecionada"}.</p>}
      {action === "desalocar" && <p>O trabalho permanecerá existente e voltará a aguardando alocação. Esta operação não é a retirada definitiva do trabalhador.</p>}
      {assessment && <div role="alert"><strong>{blocked ? "Bloqueios" : "Avisos"}</strong>{assessment.motivos.some((reason) => reason.codigo === "QUANTIDADE_ESTRUTURAL_EXCEDIDA") && <p>A função está sem vagas e nada foi alterado.</p>}<ul>{assessment.motivos.map((reason, index) => <li key={index}>{reason.mensagem}</li>)}</ul>{!blocked && <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> Confirmo os avisos</label>}</div>}
      {message && <p role="alert">{message}</p>}
      {!blocked && <button ref={confirm} type="button" disabled={disabled || saving || (!!assessment && !confirmed)} onClick={() => void submit()}>Confirmar</button>}
      <button type="button" disabled={saving} onClick={close}>Cancelar</button>
    </div>}
    {!action && message && <p role="status">{message}</p>}
  </div>;
}
