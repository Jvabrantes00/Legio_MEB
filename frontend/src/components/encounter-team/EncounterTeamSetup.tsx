"use client";

import { useEffect, useState } from "react";
import { parseActivation, parsePreparation, parseReadiness } from "../../lib/encounter-team/encounter-team-contract";
import { siaFetch } from "../../lib/sia-api";
import { readApiError } from "../../lib/form-api-error";

type Props = { encontroId: number; modelo: "LEGADO" | "CANONICO"; canActivate: boolean; canPrepare: boolean; onChange: () => void };
const motivos: Record<string, string> = {
  modelo_ja_canonico: "O modelo canônico já está ativo.",
  encontro_encerrado: "O Encontro está finalizado ou cancelado.",
  vinculos_legados_equipe: "Existem vínculos legados de equipe incompatíveis.",
  vinculos_tipo_indefinido: "Existem vínculos legados com tipo indefinido.",
};
export function EncounterTeamSetup({ encontroId, modelo, canActivate, canPrepare, onChange }: Props) {
  const [readiness, setReadiness] = useState<ReturnType<typeof parseReadiness> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [justificativa, setJustificativa] = useState("");
  const [confirmado, setConfirmado] = useState(false);
  useEffect(() => {
    if (modelo !== "LEGADO" || !canActivate) return;
    const controller = new AbortController();
    async function load() {
      try {
        const response = await siaFetch(`/encontros/${encontroId}/modelo-equipes/`, { signal: controller.signal });
        if (!response.ok) throw new Error(await readApiError(response, "Não foi possível consultar a prontidão."));
        const data = parseReadiness(await response.json());
        if (!controller.signal.aborted) setReadiness(data);
      } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Falha ao consultar prontidão."); }
    }
    void load();
    return () => controller.abort();
  }, [encontroId, modelo, canActivate]);
  async function send(action: "modelo-equipes" | "preparar-equipes") {
    if (action === "modelo-equipes" && (!confirmado || !justificativa.trim())) return;
    setLoading(true); setError(""); setSuccess("");
    try {
      const response = await siaFetch(`/encontros/${encontroId}/${action}/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(action === "modelo-equipes" ? { justificativa: justificativa.trim(), confirmacao: true } : {}) });
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível realizar a operação."));
      const data: unknown = await response.json();
      if (action === "modelo-equipes") { parseActivation(data); setSuccess("Modelo canônico ativado."); onChange(); }
      else { const teams = parsePreparation(data); setSuccess(teams.length ? "Equipes preparadas." : "Nenhum template ativo para este tipo de Encontro"); onChange(); }
    } catch (e) { setError(e instanceof Error ? e.message : "Falha na operação."); }
    finally { setLoading(false); }
  }
  return <section aria-label="Preparação de equipes" className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-5">
    {modelo === "LEGADO" && canActivate && <>
      {!readiness && !error && <p role="status">Carregando prontidão...</p>}
      {readiness && <><p className="font-semibold text-slate-800">{readiness.elegivel ? "Encontro apto à ativação." : "Encontro inapto à ativação."}</p><ul className="space-y-1 text-sm text-amber-900">{readiness.motivos.map((m) => <li key={m}>{motivos[m] ?? m}</li>)}</ul>
        {readiness.elegivel && <div className="space-y-4"><label className="block text-sm font-medium text-slate-700">Justificativa <input className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600" value={justificativa} onChange={(e) => setJustificativa(e.target.value)} /></label><label className="flex items-start gap-2 text-sm text-slate-700"><input className="mt-1" type="checkbox" checked={confirmado} onChange={(e) => setConfirmado(e.target.checked)} /> Confirmo a ativação do modelo canônico</label><button className="rounded-lg bg-escalada-azul px-4 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50" type="button" disabled={loading || !confirmado || !justificativa.trim()} onClick={() => void send("modelo-equipes")}>Ativar modelo canônico</button></div>}</>}
    </>}
    {modelo === "CANONICO" && canPrepare && <button className="rounded-lg bg-escalada-azul px-4 py-2 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50" type="button" disabled={loading} onClick={() => void send("preparar-equipes")}>Preparar equipes</button>}
    {loading && <p role="status" className="text-sm text-slate-600">Processando...</p>}{error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}{success && <p role="status" className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">{success}</p>}
  </section>;
}
