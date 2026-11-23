"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { buildEncounterTeamPath, parseEncounterTeams, type EncounterTeam } from "../../lib/encounter-team/encounter-team-contract";
import type { EncounterWorkspaceCapabilities, EncounterWorkspaceSummary } from "../../lib/encounter-workspace-contract";
import { errorMessage, readApiError } from "../../lib/form-api-error";
import { siaFetch } from "../../lib/sia-api";
import { useSiaSession } from "../SiaSessionProvider";
import { canManageEncontros, canManageInstitutionalCalendar } from "../../lib/sia-capabilities";
import { EncounterTeamSetup } from "./EncounterTeamSetup";
import { EncounterTeamInvites } from "./EncounterTeamInvites";

export function EncounterTeamPanel({ encontroId, capabilities, equipes, resumoErro }: { encontroId: number; capabilities: EncounterWorkspaceCapabilities | null | undefined; equipes: Pick<EncounterWorkspaceSummary["equipes"], "modelo_equipes" | "quantidade_equipes"> | null; resumoErro?: string | null }) {
  const { session } = useSiaSession();
  const allowed = capabilities?.acessar_equipes === true && ["consultar_resumo", "consultar_encontristas", "consultar_contato", "acessar_pre_encontro", "acessar_equipes", "acessar_formacao", "acessar_agenda", "consultar_inscricoes", "configurar_inscricoes"].every((key) => typeof capabilities[key as keyof EncounterWorkspaceCapabilities] === "boolean");
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState<{ key: object; data: EncounterTeam[] | null; error: string | null } | null>(null);
  const requestId = useRef(0);
  const shouldLoad = allowed && equipes !== null && (equipes.modelo_equipes === "CANONICO" || equipes.quantidade_equipes > 0);
  const key = useMemo(() => ({ capabilities, encontroId, retry, modelo: equipes?.modelo_equipes, quantidade: equipes?.quantidade_equipes }), [capabilities, encontroId, retry, equipes?.modelo_equipes, equipes?.quantidade_equipes]);
  useEffect(() => {
    const current = ++requestId.current;
    if (!shouldLoad) return;
    const controller = new AbortController();
    async function load() {
      try {
        const response = await siaFetch(buildEncounterTeamPath(encontroId), { signal: controller.signal });
        if (!response.ok) throw new Error(response.status === 403 ? "Você não tem permissão para acessar as equipes deste Encontro." : await readApiError(response, "Não foi possível carregar as equipes."));
        const data = parseEncounterTeams(await response.json());
        if (!controller.signal.aborted && current === requestId.current) setResult({ key, data, error: null });
      } catch (error: unknown) {
        if (!controller.signal.aborted && current === requestId.current) setResult({ key, data: null, error: errorMessage(error, "Não foi possível carregar as equipes.") });
      }
    }
    void load();
    return () => controller.abort();
  }, [shouldLoad, encontroId, key]);
  const current = shouldLoad && result?.key === key ? result : null;
  return <section aria-label="Equipes" className="space-y-5">
    <h2 className="text-2xl font-bold text-slate-900">Equipes</h2>
    {!equipes ? resumoErro ? <p role="alert">Resumo de equipes indisponível.</p> : <p role="status">Carregando resumo de equipes...</p> : <>
    {equipes.modelo_equipes === "LEGADO" && <p>O modelo canônico de Equipes não está ativo neste Encontro (modelo legado).</p>}
    {allowed && <EncounterTeamSetup encontroId={encontroId} modelo={equipes.modelo_equipes} canActivate={canManageInstitutionalCalendar(session)} canPrepare={canManageEncontros(session)} onChange={() => equipes.modelo_equipes === "LEGADO" ? window.location.reload() : setRetry((value) => value + 1)} />}
    {allowed && equipes.modelo_equipes === "LEGADO" && equipes.quantidade_equipes > 0 ? <p>Canônicos preexistentes — não ativos no modelo LEGADO</p> : null}
    {!allowed ? <p>A consulta de equipes não está disponível neste contexto.</p> : !shouldLoad ? null : !current ? <p role="status">Carregando equipes...</p> : current.error ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><p>{current.error}</p><button className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-2 font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600" type="button" onClick={() => setRetry((value) => value + 1)}>Tentar novamente</button></div> : current.data?.length === 0 ? equipes.modelo_equipes === "CANONICO" ? <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">Equipes ainda não preparadas</p> : null : current.data?.slice().sort((a, b) => a.ordem - b.ordem).map((team) => <article key={team.id} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-lg font-bold text-slate-900">{team.nome}</h3>
      <p className="text-sm text-slate-600">Capacidade mínima: {team.capacidade_minima_recomendada ?? "não definida"} · máxima: {team.capacidade_maxima_recomendada ?? "não definida"}</p>
      {([["Capacidade", team.capacidade], ["Composição", team.composicao]] as const).map(([label, assessment]) => {
        const groups = assessment.motivos.reduce<Map<string, typeof assessment.motivos>>((acc, reason) => {
          const key = JSON.stringify([reason.codigo, reason.categoria, reason.mensagem]);
          acc.set(key, [...(acc.get(key) ?? []), reason]);
          return acc;
        }, new Map());
        return <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700"><p className="font-semibold">{label}: {assessment.resultado}</p><ul className="mt-2 space-y-2">{[...groups.values()].map((reasons, index) => <li key={index}><p>{reasons[0].mensagem}</p>{reasons.some((reason) => reason.contexto) && <ul className="mt-1 list-disc space-y-1 pl-5 text-slate-600">{[...new Set(reasons.filter((reason) => reason.contexto).map((reason) => JSON.stringify(reason.contexto)))].map((context) => { const values = JSON.parse(context) as Record<string, number>; const roleName = team.roles.find((role) => role.id === values.role_id)?.nome; return <li key={context}>{Object.entries(values).map(([key, value]) => key === "role_id" && roleName ? `Função: ${roleName} (id ${value})` : `${key.replaceAll("_", " ")}: ${value}`).join(" · ")}</li>; })}</ul>}</li>)}</ul></div>;
      })}
      <div className="space-y-3 border-t border-slate-200 pt-4">{team.roles.slice().sort((a, b) => a.ordem - b.ordem).map((role) => <div key={role.id} className="rounded-xl border border-slate-200 p-3"><h4 className="font-semibold text-slate-800">{role.nome}</h4><p className="mt-1 text-sm text-slate-600">Vagas estruturais: {role.quantidade_estrutural ?? "não definida"}</p><ul className="mt-2 space-y-1 text-sm text-slate-700">{role.trabalhos.map((person) => <li key={person.id}>{person.pessoa_nome} — {person.status}</li>)}</ul></div>)}</div>
    </article>)}
    {equipes.modelo_equipes === "CANONICO" && <EncounterTeamInvites encontroId={encontroId} teams={current?.data ?? []} enabled={allowed && canManageEncontros(session)} />}
    </>}
  </section>;
}
