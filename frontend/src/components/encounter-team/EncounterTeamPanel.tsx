"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { buildEncounterTeamPath, parseEncounterTeams, type EncounterTeam } from "../../lib/encounter-team/encounter-team-contract";
import type { EncounterWorkspaceCapabilities, EncounterWorkspaceSummary } from "../../lib/encounter-workspace-contract";
import { errorMessage, readApiError } from "../../lib/form-api-error";
import { siaFetch } from "../../lib/sia-api";

export function EncounterTeamPanel({ encontroId, capabilities, equipes, resumoErro }: { encontroId: number; capabilities: EncounterWorkspaceCapabilities | null | undefined; equipes: Pick<EncounterWorkspaceSummary["equipes"], "modelo_equipes" | "quantidade_equipes"> | null; resumoErro?: string | null }) {
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
  return <section aria-label="Equipes" className="space-y-4">
    <h2 className="text-2xl font-bold">Equipes</h2>
    {!equipes ? resumoErro ? <p role="alert">Resumo de equipes indisponível.</p> : <p role="status">Carregando resumo de equipes...</p> : <>
    {equipes.modelo_equipes === "LEGADO" ? <p>O modelo canônico de Equipes não está ativo neste Encontro (modelo legado).</p> : <p>Visão canônica somente leitura. Não substitui a montagem de equipes.</p>}
    {allowed && equipes.modelo_equipes === "LEGADO" && equipes.quantidade_equipes > 0 ? <p>Canônicos preexistentes — não ativos no modelo LEGADO</p> : null}
    {!allowed ? <p>A consulta de equipes não está disponível neste contexto.</p> : !shouldLoad ? null : !current ? <p role="status">Carregando equipes...</p> : current.error ? <div role="alert"><p>{current.error}</p><button type="button" onClick={() => setRetry((value) => value + 1)}>Tentar novamente</button></div> : current.data?.length === 0 ? equipes.modelo_equipes === "CANONICO" ? <p>Equipes ainda não preparadas</p> : null : current.data?.slice().sort((a, b) => a.ordem - b.ordem).map((team) => <article key={team.id} className="rounded-xl border p-4">
      <h3 className="font-bold">{team.nome}</h3>
      <p>Capacidade mínima: {team.capacidade_minima_recomendada ?? "não definida"} · máxima: {team.capacidade_maxima_recomendada ?? "não definida"}</p>
      {([["Capacidade", team.capacidade], ["Composição", team.composicao]] as const).map(([label, assessment]) => <div key={label}><p>{label}: {assessment.resultado}</p><ul>{assessment.motivos.map((reason, index) => <li key={index}>{reason.mensagem}</li>)}</ul></div>)}
      {team.roles.slice().sort((a, b) => a.ordem - b.ordem).map((role) => <div key={role.id}><h4 className="font-semibold">{role.nome}</h4><p>Vagas estruturais: {role.quantidade_estrutural ?? "não definida"}</p><ul>{role.trabalhos.map((person) => <li key={person.id}>{person.pessoa_nome} — {person.status}</li>)}</ul></div>)}
    </article>)}
    </>}
  </section>;
}
