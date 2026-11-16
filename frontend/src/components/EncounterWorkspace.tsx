"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Briefcase,
  LayoutDashboard,
  ShieldCheck,
  Users,
} from "lucide-react";

import {
  parseEncounterWorkspaceCapabilities,
  parseEncounterWorkspaceSummary,
  type EncounterWorkspaceCapabilities,
  type EncounterWorkspaceSummary,
} from "../lib/encounter-workspace-contract";
import { errorMessage, readApiError } from "../lib/form-api-error";
import { siaFetch } from "../lib/sia-api";
import { EncounterAgendaSection } from "./EncounterAgendaSection";

export type EncounterWorkspaceTab =
  | "visao-geral"
  | "encontristas"
  | "pre-encontro"
  | "equipe";

type EncounterWorkspaceProps = {
  encontroId: string;
  activeTab: EncounterWorkspaceTab;
  onTabChange: (tab: EncounterWorkspaceTab) => void;
  renderEncontristas?: (capabilities: EncounterWorkspaceCapabilities) => ReactNode;
  renderPreEncounter?: () => ReactNode;
  renderTeam?: (capabilities: EncounterWorkspaceCapabilities, equipes: EncounterWorkspaceSummary["equipes"] | null) => ReactNode;
};

type WorkspaceTabDefinition = {
  id: EncounterWorkspaceTab;
  label: string;
  icon: typeof LayoutDashboard;
};

function formatDateOnly(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("pt-BR").format(new Date(year, month - 1, day));
}

function lifecycleLabel(value: string): string {
  return value.replaceAll("_", " ").toLocaleLowerCase("pt-BR");
}

async function responseError(response: Response, fallback: string): Promise<string> {
  if (response.status === 403) return "Você não tem permissão para acessar esta área do Encontro.";
  if (response.status === 404) return "Encontro não encontrado.";
  if (response.status >= 500) return "O Workspace está temporariamente indisponível.";
  return readApiError(response, fallback);
}

export function EncounterWorkspaceOverview({
  summary,
  capabilities,
}: {
  summary: EncounterWorkspaceSummary;
  capabilities: EncounterWorkspaceCapabilities;
}) {
  const dates = summary.agenda.datas_principais;
  return (
    <div className="space-y-5" data-testid="workspace-overview">
      {summary.alertas.length ? (
        <section aria-labelledby="workspace-alerts-title" className="space-y-2">
          <h2 id="workspace-alerts-title" className="sr-only">Alertas do Encontro</h2>
          {summary.alertas.map((alert) => (
            <div key={alert.codigo} role="alert" className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{alert.mensagem}</span>
            </div>
          ))}
        </section>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Indicadores do Encontro">
        <OverviewMetric label="Capacidade" value={summary.pre_encontro.capacidade ?? "Não configurada"} />
        <OverviewMetric label="Inscrições recebidas" value={summary.encontristas.inscricoes_recebidas} />
        <OverviewMetric label="Pendentes" value={summary.encontristas.pendentes} />
        <OverviewMetric label="Confirmados" value={summary.encontristas.confirmados} />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <OverviewCard title="Encontro">
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <OverviewDetail label="Tipo" value={summary.encontro.tipo} />
            <OverviewDetail label="Lifecycle" value={lifecycleLabel(summary.lifecycle)} />
            <OverviewDetail label="Local" value={summary.encontro.local || "Não informado"} />
            <OverviewDetail
              label="Datas principais"
              value={dates.length ? dates.map(formatDateOnly).join(" · ") : "Não configuradas"}
            />
          </dl>
        </OverviewCard>

        {capabilities.acessar_pre_encontro ? (
          <OverviewCard title="Pré-Encontro">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <OverviewDetail label="Data" value={summary.pre_encontro.data ? formatDateOnly(summary.pre_encontro.data) : "Não configurada"} />
              <OverviewDetail label="Check-ins" value={summary.pre_encontro.quantidade_checkins} />
              <OverviewDetail label="Aptos" value={summary.pre_encontro.quantidade_aptos} />
              <OverviewDetail label="Aguardando decisão" value={summary.pre_encontro.quantidade_aguardando_decisao} />
            </dl>
          </OverviewCard>
        ) : null}

        {capabilities.acessar_equipes ? (
          <OverviewCard title="Equipe">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <OverviewDetail label="Equipes" value={summary.equipes.quantidade_equipes} />
              <OverviewDetail label="Funções" value={summary.equipes.quantidade_funcoes} />
              <OverviewDetail label="Vagas estruturais" value={summary.equipes.vagas_estruturais ?? "Não definidas"} />
              <OverviewDetail label="Vagas preenchidas" value={summary.equipes.vagas_preenchidas} />
            </dl>
          </OverviewCard>
        ) : null}

        {capabilities.acessar_agenda ? (
          <OverviewCard title="Calendário">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <OverviewDetail label="Itens" value={summary.agenda.quantidade_itens} />
              <OverviewDetail label="Agenda" value={summary.agenda.oficializada ? "Oficializada" : summary.agenda.configurada ? "Em planejamento" : "Não configurada"} />
              <OverviewDetail label="Próximo item" value={summary.agenda.proximo_item ? formatDateOnly(summary.agenda.proximo_item) : "Nenhum próximo item"} />
            </dl>
          </OverviewCard>
        ) : null}
      </div>
    </div>
  );
}

function OverviewMetric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
    </article>
  );
}

function OverviewCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-bold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}

function OverviewDetail({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="mt-1 font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

export function EncounterWorkspace({
  encontroId,
  activeTab,
  onTabChange,
  renderEncontristas,
  renderPreEncounter,
  renderTeam,
}: EncounterWorkspaceProps) {
  const [capabilities, setCapabilities] = useState<EncounterWorkspaceCapabilities | null>(null);
  const [summary, setSummary] = useState<EncounterWorkspaceSummary | null>(null);
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const loadSummary = useCallback(async (signal?: AbortSignal) => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const response = await siaFetch(`/encontros/${encontroId}/workspace/`, { signal });
      if (!response.ok) throw new Error(await responseError(response, "Não foi possível carregar a Visão geral."));
      const body = parseEncounterWorkspaceSummary(await response.json());
      if (!signal?.aborted) setSummary(body);
    } catch (caught: unknown) {
      if (!signal?.aborted) {
        setSummary(null);
        setSummaryError(errorMessage(caught, "Não foi possível carregar a Visão geral."));
      }
    } finally {
      if (!signal?.aborted) setSummaryLoading(false);
    }
  }, [encontroId]);

  const loadWorkspace = useCallback(async (signal?: AbortSignal) => {
    setCapabilitiesLoading(true);
    setCapabilitiesError(null);
    try {
      const response = await siaFetch(`/encontros/${encontroId}/workspace/capabilities/`, { signal });
      if (!response.ok) throw new Error(await responseError(response, "Não foi possível carregar o acesso ao Workspace."));
      const parsed = parseEncounterWorkspaceCapabilities(await response.json());
      if (signal?.aborted) return;
      setCapabilities(parsed);
      if (parsed.consultar_resumo) await loadSummary(signal);
      else {
        setSummary(null);
        setSummaryLoading(false);
      }
    } catch (caught: unknown) {
      if (!signal?.aborted) {
        setCapabilities(null);
        setCapabilitiesError(errorMessage(caught, "Não foi possível carregar o acesso ao Workspace."));
      }
    } finally {
      if (!signal?.aborted) setCapabilitiesLoading(false);
    }
  }, [encontroId, loadSummary]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void loadWorkspace(controller.signal), 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [loadWorkspace]);

  const tabs = useMemo<WorkspaceTabDefinition[]>(() => {
    if (!capabilities) return [];
    return [
      capabilities.consultar_resumo
        ? { id: "visao-geral", label: "Visão geral", icon: LayoutDashboard }
        : null,
      capabilities.consultar_encontristas && renderEncontristas
        ? { id: "encontristas", label: "Encontristas", icon: Users }
        : null,
      capabilities.acessar_pre_encontro && renderPreEncounter
        ? { id: "pre-encontro", label: "Pré-Encontro", icon: ShieldCheck }
        : null,
      capabilities.acessar_equipes && renderTeam
        ? { id: "equipe", label: "Equipe", icon: Briefcase }
        : null,
    ].filter((tab): tab is WorkspaceTabDefinition => tab !== null);
  }, [capabilities, renderEncontristas, renderPreEncounter, renderTeam]);

  useEffect(() => {
    if (tabs.length && !tabs.some((tab) => tab.id === activeTab)) {
      onTabChange(tabs[0].id);
    }
  }, [activeTab, onTabChange, tabs]);

  if (capabilitiesLoading) return <p className="p-10 text-slate-500" role="status">Carregando Workspace do Encontro...</p>;
  if (capabilitiesError || !capabilities) {
    return (
      <div className="space-y-4 p-6">
        <Link href="/encontros" className="text-escalada-azul hover:underline">← Voltar aos encontros</Link>
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700" role="alert">{capabilitiesError || "Workspace indisponível."}</div>
        <button type="button" onClick={() => void loadWorkspace()} className="font-semibold text-escalada-azul underline">Tentar novamente</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex items-start gap-4">
        <Link href="/encontros" aria-label="Voltar aos encontros" className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 transition-colors hover:bg-slate-50">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Workspace do Encontro</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">{summary?.encontro.nome || "Encontro"}</h1>
          {summary ? <p className="mt-1 text-sm text-slate-500">{summary.encontro.tipo} · {lifecycleLabel(summary.lifecycle)}</p> : null}
        </div>
      </header>

      {capabilities.acessar_agenda ? <EncounterAgendaSection encontroId={encontroId} /> : null}

      {tabs.length ? (
        <nav aria-label="Áreas do Workspace" className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm" data-testid="workspace-tabs-scroll">
          <div className="flex min-w-max p-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const selected = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  onClick={() => onTabChange(tab.id)}
                  className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-3 text-sm font-semibold transition-colors ${selected ? "bg-escalada-azul text-white" : "text-slate-600 hover:bg-slate-50"}`}
                >
                  <Icon aria-hidden="true" size={17} />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </nav>
      ) : null}

      <main>
        {activeTab === "visao-geral" ? (
          summaryLoading ? <p className="rounded-xl border bg-white p-6 text-slate-500" role="status">Carregando Visão geral...</p>
            : summaryError ? (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
                <p>{summaryError}</p>
                <button type="button" onClick={() => void loadSummary()} className="mt-2 font-semibold underline">Tentar novamente</button>
              </div>
            ) : summary ? <EncounterWorkspaceOverview summary={summary} capabilities={capabilities} />
              : <p className="rounded-xl border bg-white p-6 text-slate-500">Visão geral indisponível.</p>
        ) : activeTab === "encontristas" ? renderEncontristas?.(capabilities)
          : activeTab === "pre-encontro" ? renderPreEncounter?.()
            : activeTab === "equipe" && capabilities.acessar_equipes ? renderTeam?.(capabilities, summary?.equipes ?? null)
              : null}
      </main>
    </div>
  );
}
