"use client";

import { useEffect, useRef, useState } from "react";
import { parseEligibilityError, parseInvitePage, parseSelectorPage, type EncounterTeam } from "../../lib/encounter-team/encounter-team-contract";
import { readApiError } from "../../lib/form-api-error";
import { siaFetch } from "../../lib/sia-api";
import { EncounterTeamWorkActions } from "./EncounterTeamWorkActions";
import { EncounterTeamInviteActions } from "./EncounterTeamInviteActions";

type Assessment = ReturnType<typeof parseEligibilityError>;
export function EncounterTeamInvites({ encontroId, teams, enabled, refreshToken = 0, refresh, disabled = false, onBusy, onListState }: { encontroId: number; teams: EncounterTeam[]; enabled: boolean; refreshToken?: number; refresh?: () => void; disabled?: boolean; onBusy?: (busy: boolean) => boolean; onListState?: (state: "loading" | "ready" | "error", token: number) => void }) {
  const [search, setSearch] = useState(""); const [term, setTerm] = useState("");
  const [page, setPage] = useState(1); const [invitePage, setInvitePage] = useState(1);
  const [people, setPeople] = useState<ReturnType<typeof parseSelectorPage> | null>(null);
  const [invites, setInvites] = useState<ReturnType<typeof parseInvitePage> | null>(null);
  const [person, setPerson] = useState(""); const [role, setRole] = useState("");
  const [assessment, setAssessment] = useState<Assessment | null>(null); const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState(""); const [peopleError, setPeopleError] = useState(""); const [listError, setListError] = useState("");
  const [saving, setSaving] = useState(false); const [success, setSuccess] = useState(""); const [revision, setRevision] = useState(0);
  const inFlight = useRef(false);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    async function load() {
      try { const q = new URLSearchParams({ search: term, page: String(page) }); const r = await siaFetch(`/alpinistas/seletor-trabalho/?${q}`, { signal: controller.signal }); if (!r.ok) throw new Error(await readApiError(r, "Falha ao buscar alpinistas.")); const data = parseSelectorPage(await r.json()); if (!controller.signal.aborted) { setPeople(data); setPeopleError(""); } }
      catch (e) { if (!controller.signal.aborted) setPeopleError(e instanceof Error ? e.message : "Falha ao buscar alpinistas."); }
    }
    void load(); return () => controller.abort();
  }, [enabled, term, page]);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    onListState?.("loading", refreshToken);
    async function load() {
      try { const r = await siaFetch(`/convites-encontros/?encontro=${encontroId}&finalidade=trabalhar&page=${invitePage}`, { signal: controller.signal }); if (!r.ok) throw new Error(await readApiError(r, "Falha ao carregar convites.")); const data = parseInvitePage(await r.json()); if (!controller.signal.aborted) { setInvites(data); setListError(""); onListState?.("ready", refreshToken); } }
      catch (e) { if (!controller.signal.aborted) { setListError(e instanceof Error ? e.message : "Falha ao carregar convites."); onListState?.("error", refreshToken); } }
    }
    void load(); return () => controller.abort();
  }, [enabled, encontroId, invitePage, revision, refreshToken, onListState]);
  const blocked = assessment?.motivos.some((m) => m.categoria === "BLOQUEIO") || assessment?.resultado === "BLOQUEIO";
  const warning = assessment?.motivos.some((m) => m.categoria === "AVISO");
  async function send(confirmar: boolean) {
    if (disabled || inFlight.current || !person || !role || blocked || (confirmar && !confirmed)) return;
    if (onBusy?.(true) === false) return;
    inFlight.current = true;
    setSaving(true); setError(""); setSuccess("");
    try {
      const response = await siaFetch("/convites-encontros/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pessoa_id: Number(person), encontro_id: encontroId, finalidade: "trabalhar", role_trabalho_proposta_id: Number(role), ...(confirmar ? { confirmar_avisos: true } : {}) }) });
      const data: unknown = await response.json();
      if (response.status === 400) {
        try { setAssessment(parseEligibilityError(data)); setConfirmed(false); return; } catch { /* Não é erro de elegibilidade. */ }
        const body = data && typeof data === "object" ? data as Record<string, unknown> : {};
        const errors = body.non_field_errors;
        if (Array.isArray(errors) && errors.some((item) => typeof item === "string" && item.includes("devem criar um set único"))) {
          let index = 1; let exists = false;
          do {
            const listing = await siaFetch(`/convites-encontros/?encontro=${encontroId}&finalidade=trabalhar&page=${index}`);
            if (!listing.ok) throw new Error("Não foi possível verificar os convites existentes.");
            const result = parseInvitePage(await listing.json());
            exists = result.results.some((item) => item.pessoa_id === Number(person) && item.encontro_id === encontroId);
            if (exists || !result.next) break;
            index += 1;
          } while (true);
          setInvitePage(1); setRevision((n) => n + 1);
          if (exists) { setAssessment(null); setError("Já existe um convite de trabalho para esta pessoa neste Encontro."); return; }
        }
        throw new Error("Não foi possível registrar o convite. Verifique os dados informados.");
      }
      if (!response.ok) throw new Error("Não foi possível registrar o convite.");
      setAssessment(null); setConfirmed(false); setSuccess("Convite registrado no SIA. O contato com o alpinista é feito fora do SIA."); setRevision((n) => n + 1);
    } catch (e) { setError(e instanceof Error ? e.message : "Falha ao registrar convite."); }
    finally { setRevision((n) => n + 1); inFlight.current = false; onBusy?.(false); setSaving(false); }
  }
  const roles = teams.flatMap((team) => team.roles.map((r) => ({ ...r, equipe: team.nome })));
  const labels = { convidado: "Pendente (aguardando resposta)", confirmado: "Confirmado", recusado: "Recusado", sem_resposta: "Sem resposta" };
  if (!enabled) return null;
  return <section aria-label="Convites de trabalho" className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h3 className="text-lg font-bold text-slate-900">Convites de trabalho</h3>
    <fieldset disabled={disabled} className="space-y-5"><form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); setPage(1); setPeople(null); setTerm(search); }}><label className="block min-w-0 flex-1 text-sm font-medium text-slate-700">Buscar alpinista por nome <input className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600" value={search} onChange={(e) => setSearch(e.target.value)} /></label><button className="rounded-lg bg-escalada-azul px-4 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600">Buscar</button></form>
    {peopleError ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{peopleError}</p> : !people ? <p role="status" className="text-sm text-slate-600">Carregando alpinistas...</p> : <div className="space-y-3"><p className="text-sm text-slate-600">{people.count} alpinista(s)</p>{people.results.length === 0 ? <p>Nenhum alpinista encontrado.</p> : <label className="block text-sm font-medium text-slate-700">Alpinista <select className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600" value={person} onChange={(e) => { setPerson(e.target.value); setAssessment(null); setConfirmed(false); }}><option value="">Selecione</option>{people.results.map((p) => <option key={p.id} value={p.pessoa_id}>{p.nome} {p.grupo ? `— ${p.grupo}` : ""}</option>)}</select></label>}<div className="flex flex-wrap gap-2" aria-label="Paginação de alpinistas"><button type="button" className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50" disabled={!people.previous} onClick={() => { setPeople(null); setPage((p) => p - 1); }}>Anterior</button><button type="button" className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50" disabled={!people.next} onClick={() => { setPeople(null); setPage((p) => p + 1); }}>Próxima</button></div></div>}
    <label className="block text-sm font-medium text-slate-700">Função <select className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600" value={role} onChange={(e) => { setRole(e.target.value); setAssessment(null); setConfirmed(false); }}><option value="">Selecione</option>{roles.map((r) => <option key={r.id} value={r.id}>{r.equipe} — {r.nome} (vagas: {r.quantidade_estrutural ?? "não definidas"})</option>)}</select></label>
    {assessment && <div className="space-y-3">{(["AVISO", "BLOQUEIO"] as const).map((category) => { const reasons = assessment.motivos.filter((m) => m.categoria === category); return reasons.length ? <div key={category} className={category === "AVISO" ? "rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" : "rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"}><strong>{category === "AVISO" ? "Avisos" : "Bloqueios"}</strong><ul className="mt-2 list-disc space-y-1 pl-5">{reasons.map((m, i) => <li key={i}>{m.mensagem} ({m.codigo})</li>)}</ul></div> : null; })}</div>}
    {warning && !blocked ? <div className="space-y-3"><label className="flex items-start gap-2 text-sm text-slate-700"><input className="mt-1" type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} /> Confirmo os avisos e registrar convite</label><button type="button" className="rounded-lg bg-escalada-azul px-4 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50" disabled={!confirmed || saving} onClick={() => void send(true)}>Registrar convite com confirmação</button></div> : <button type="button" className="rounded-lg bg-escalada-azul px-4 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50" disabled={!person || !role || saving || !!blocked} onClick={() => void send(false)}>Registrar convite</button>}
    {saving && <p role="status" className="text-sm text-slate-600">Registrando convite...</p>}{error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}{success && <p role="status" className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">{success}</p>}
    <div className="space-y-3 border-t border-slate-200 pt-4"><h4 className="font-semibold text-slate-800">Convites registrados</h4>{listError && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{listError}</p>}{!invites ? <p role="status" className="text-sm text-slate-600">Carregando convites...</p> : <>{invites.results.length === 0 ? <p className="text-sm text-slate-600">Nenhum convite de trabalho registrado.</p> : <ul className="space-y-2" aria-label="Convites registrados">{invites.results.map((invite) => <li key={invite.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700"><p className="font-semibold text-slate-900">{invite.pessoa_nome} — {labels[invite.status]}</p>{invite.role_trabalho_proposta_id !== null && <p className="mt-1">{roles.find((r) => r.id === invite.role_trabalho_proposta_id)?.nome ?? `Função ${invite.role_trabalho_proposta_id}`}</p>}<EncounterTeamInviteActions invite={invite} disabled={disabled} onBusy={onBusy} refresh={refresh ?? (() => setRevision((n) => n + 1))} onAnswered={(status) => setInvites((current) => current ? { ...current, results: current.results.map((item) => item.id === invite.id ? { ...item, status } : item) } : current)} />{invite.trabalho_status === "aguardando_alocacao" && invite.trabalho_id !== null && <EncounterTeamWorkActions trabalhoId={invite.trabalho_id} teams={teams} disabled={disabled} onBusy={onBusy} refresh={refresh ?? (() => setRevision((n) => n + 1))} />}</li>)}</ul>}<div className="flex flex-wrap gap-2" aria-label="Paginação de convites"><button type="button" className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50" disabled={!invites.previous} onClick={() => { setInvites(null); setInvitePage((p) => p - 1); }}>Anterior</button><button type="button" className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50" disabled={!invites.next} onClick={() => { setInvites(null); setInvitePage((p) => p + 1); }}>Próxima</button></div></>}</div>
  </fieldset></section>;
}
