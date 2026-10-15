"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import {
  parseEncounterRegistrationConfig,
  parseEncounterWorkspaceCapabilities,
  type EncounterRegistrationConfig,
  type EncounterRegistrationConfigDraft,
  type EncounterWorkspaceCapabilities,
} from "../lib/encounter-workspace-contract";
import { errorMessage, readApiError } from "../lib/form-api-error";
import { siaFetch } from "../lib/sia-api";

const EMPTY_DRAFT: EncounterRegistrationConfigDraft = {
  capacidade: "",
  idade_minima: "",
  idade_maxima: "",
  inscricoes_abrem_em: "",
  inscricoes_encerram_em: "",
};

const STATUS_LABELS = {
  ainda_nao_abriu: "Ainda não abriu",
  abertas: "Inscrições abertas",
  encerradas: "Encerradas",
} as const;

function inProjectTimezone(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}`;
}

function draftFrom(config: EncounterRegistrationConfig): EncounterRegistrationConfigDraft {
  if (!config.configurado) return EMPTY_DRAFT;
  return {
    capacidade: String(config.capacidade),
    idade_minima: String(config.idade_minima),
    idade_maxima: String(config.idade_maxima),
    inscricoes_abrem_em: inProjectTimezone(config.inscricoes_abrem_em),
    inscricoes_encerram_em: inProjectTimezone(config.inscricoes_encerram_em),
  };
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function EncounterRegistrationConfigCard({ encontroId }: { encontroId: string }) {
  const [capabilities, setCapabilities] = useState<EncounterWorkspaceCapabilities | null>(null);
  const [config, setConfig] = useState<EncounterRegistrationConfig | null>(null);
  const [persistedDraft, setPersistedDraft] = useState(EMPTY_DRAFT);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const path = `/encontros/${encontroId}/workspace/inscricoes/configuracao/`;

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setLoadError(null);
      try {
        const capabilitiesResponse = await siaFetch(
          `/encontros/${encontroId}/workspace/capabilities/`,
          { signal: controller.signal },
        );
        if (!capabilitiesResponse.ok) {
          throw new Error(await readApiError(capabilitiesResponse, "Não foi possível consultar as ações de inscrições."));
        }
        const nextCapabilities = parseEncounterWorkspaceCapabilities(
          await capabilitiesResponse.json(),
        );
        if (controller.signal.aborted) return;
        setCapabilities(nextCapabilities);
        if (!nextCapabilities.consultar_inscricoes) return;

        const response = await siaFetch(path, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(await readApiError(response, "Não foi possível carregar a configuração de inscrições."));
        }
        const nextConfig = parseEncounterRegistrationConfig(await response.json());
        if (controller.signal.aborted) return;
        const nextDraft = draftFrom(nextConfig);
        setConfig(nextConfig);
        setPersistedDraft(nextDraft);
        setDraft(nextDraft);
      } catch (caught: unknown) {
        if (!controller.signal.aborted) {
          setLoadError(errorMessage(caught, "Não foi possível carregar a configuração de inscrições."));
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [encontroId, path]);

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(persistedDraft),
    [draft, persistedDraft],
  );

  function update(field: keyof EncounterRegistrationConfigDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function cancel() {
    setDraft(persistedDraft);
    setSaveError(null);
    setEditing(false);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!dirty || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const response = await siaFetch(path, {
        method: config?.configurado ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          capacidade: Number(draft.capacidade),
          idade_minima: Number(draft.idade_minima),
          idade_maxima: Number(draft.idade_maxima),
          inscricoes_abrem_em: draft.inscricoes_abrem_em,
          inscricoes_encerram_em: draft.inscricoes_encerram_em,
        }),
      });
      if (!response.ok) {
        setSaveError(await readApiError(response, "Não foi possível salvar a configuração de inscrições."));
        return;
      }
      const nextConfig = parseEncounterRegistrationConfig(await response.json());
      const nextDraft = draftFrom(nextConfig);
      setConfig(nextConfig);
      setPersistedDraft(nextDraft);
      setDraft(nextDraft);
      setEditing(false);
      toast.success("Configuração de inscrições salva");
    } catch (caught: unknown) {
      setSaveError(errorMessage(caught, "Falha ao salvar a configuração de inscrições."));
    } finally {
      setSaving(false);
    }
  }

  async function copyLink() {
    if (!config?.configurado) return;
    const link = `${window.location.origin}/inscricoes/${config.public_id}`;
    try {
      await navigator.clipboard.writeText(link);
      toast.success("Link copiado");
    } catch {
      toast.error("Não foi possível copiar o link.");
    }
  }

  if (loading) return <section className="mb-6 rounded-xl border p-5">Carregando inscrições...</section>;
  if (loadError) return <section className="mb-6 rounded-xl border border-red-200 p-5 text-red-700">{loadError}</section>;
  if (!capabilities?.consultar_inscricoes || config === null) return null;

  const showForm = editing;
  return (
    <section className="mb-6 rounded-xl border border-gray-200 bg-gray-50 p-5" aria-labelledby="registration-config-title">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 id="registration-config-title" className="text-xl font-bold text-gray-900">Inscrições</h2>
          {!config.configurado && <p className="mt-1 font-semibold text-amber-700">Não configuradas</p>}
          {!config.configurado && <p className="mt-1 text-sm text-amber-800">Inscrições ainda não configuradas.</p>}
        </div>
        {!showForm && capabilities.configurar_inscricoes && (
          <button type="button" onClick={() => setEditing(true)} className="rounded-lg border bg-white px-3 py-2 text-sm font-semibold">
            Editar configuração
          </button>
        )}
      </div>

      {config.configurado && !showForm && (
        <div className="mt-4 space-y-2 text-sm text-gray-700">
          <p><strong>Capacidade:</strong> {config.capacidade}</p>
          <p><strong>Faixa etária:</strong> {config.idade_minima} a {config.idade_maxima} anos</p>
          <p><strong>Período:</strong> {formatDateTime(config.inscricoes_abrem_em)} — {formatDateTime(config.inscricoes_encerram_em)}</p>
          <p><strong>Status:</strong> {STATUS_LABELS[config.status_janela]}</p>
          <p className="break-all"><strong>Link:</strong> /inscricoes/{config.public_id}</p>
          <button type="button" onClick={() => void copyLink()} className="rounded-lg border bg-white px-3 py-2 font-semibold">
            Copiar link
          </button>
        </div>
      )}

      {!config.configurado && !capabilities.configurar_inscricoes && (
        <p className="mt-3 text-sm text-gray-600">A configuração deve ser realizada por um usuário autorizado.</p>
      )}
      {!config.configurado && capabilities.configurar_inscricoes && !editing && (
        <button type="button" onClick={() => setEditing(true)} className="mt-4 rounded-lg bg-escalada-azul px-4 py-2 font-semibold text-white">
          Configurar inscrições
        </button>
      )}

      {showForm && capabilities.configurar_inscricoes && (
        <form onSubmit={save} className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium">Capacidade<input required min="1" type="number" value={draft.capacidade} onChange={(event) => update("capacidade", event.target.value)} className="mt-1 w-full rounded-lg border bg-white p-2" /></label>
          <div />
          <label className="text-sm font-medium">Idade mínima<input required min="0" type="number" value={draft.idade_minima} onChange={(event) => update("idade_minima", event.target.value)} className="mt-1 w-full rounded-lg border bg-white p-2" /></label>
          <label className="text-sm font-medium">Idade máxima<input required min="0" type="number" value={draft.idade_maxima} onChange={(event) => update("idade_maxima", event.target.value)} className="mt-1 w-full rounded-lg border bg-white p-2" /></label>
          <label className="text-sm font-medium">Abertura das inscrições<input required type="datetime-local" value={draft.inscricoes_abrem_em} onChange={(event) => update("inscricoes_abrem_em", event.target.value)} className="mt-1 w-full rounded-lg border bg-white p-2" /></label>
          <label className="text-sm font-medium">Encerramento das inscrições<input required type="datetime-local" value={draft.inscricoes_encerram_em} onChange={(event) => update("inscricoes_encerram_em", event.target.value)} className="mt-1 w-full rounded-lg border bg-white p-2" /></label>
          {saveError && <p role="alert" className="text-sm font-medium text-red-700 sm:col-span-2">{saveError}</p>}
          <div className="flex flex-wrap gap-2 sm:col-span-2">
            <button type="submit" disabled={!dirty || saving} className="rounded-lg bg-escalada-azul px-4 py-2 font-semibold text-white disabled:opacity-50">
              {saving ? "Salvando..." : "Salvar alterações"}
            </button>
            <button type="button" disabled={saving} onClick={cancel} className="rounded-lg border bg-white px-4 py-2 font-semibold disabled:opacity-50">Cancelar</button>
          </div>
        </form>
      )}
    </section>
  );
}
