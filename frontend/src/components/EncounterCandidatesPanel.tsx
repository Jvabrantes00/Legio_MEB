"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  parseEncounterCandidateFull,
  parseEncounterCandidatePage,
  parseEncounterCandidateSummary,
  type EncounterCandidateFull,
  type EncounterCandidatePage,
  type EncounterCandidateSummary,
  type EncounterWorkspaceCapabilities,
  type EncounterWorkspaceCandidateOrigin,
  type EncounterWorkspaceCandidateStatus,
} from "../lib/encounter-workspace-contract";
import { errorMessage, readApiError } from "../lib/form-api-error";
import { siaFetch } from "../lib/sia-api";

type Candidate = EncounterCandidateSummary | EncounterCandidateFull;

type CandidateLoadResult = {
  requestKey: string;
  data: EncounterCandidatePage<Candidate> | null;
  error: string | null;
};

type EncounterCandidatesPanelProps = {
  encontroId: string;
  capabilities?: EncounterWorkspaceCapabilities | null;
};

const STATUS_OPTIONS: ReadonlyArray<{
  value: EncounterWorkspaceCandidateStatus;
  label: string;
}> = [
  { value: "INSCRITO", label: "Inscrito" },
  { value: "CANCELADO", label: "Cancelado" },
  { value: "AGUARDANDO_DECISAO", label: "Aguardando decisão" },
  { value: "APTO", label: "Apto" },
  { value: "NAO_APTO", label: "Não apto" },
  { value: "CONFIRMADO", label: "Confirmado" },
];

const ORIGIN_OPTIONS: ReadonlyArray<{
  value: EncounterWorkspaceCandidateOrigin;
  label: string;
}> = [
  { value: "INSCRICAO", label: "Inscrição" },
  { value: "PESSOA", label: "Pessoa existente" },
  { value: "AVULSO", label: "Avulso" },
];

const APTITUDE_LABELS = {
  apto: "Apto",
  nao_apto: "Não apto",
  aguardando_decisao_diretoria: "Aguardando decisão da Diretoria",
} as const;

function hasValidAccess(
  capabilities: EncounterWorkspaceCapabilities | null | undefined,
): capabilities is EncounterWorkspaceCapabilities {
  return capabilities?.consultar_encontristas === true
    && typeof capabilities.consultar_contato === "boolean";
}

function buildCandidatesPath({
  encontroId,
  page,
  search,
  status,
  origin,
}: {
  encontroId: string;
  page: number;
  search: string;
  status: EncounterWorkspaceCandidateStatus | "";
  origin: EncounterWorkspaceCandidateOrigin | "";
}): string {
  const params = new URLSearchParams({ page: String(page) });
  if (search) params.set("search", search);
  if (status) params.set("situacao", status);
  if (origin) params.set("origem", origin);
  return `/encontros/${encontroId}/workspace/encontristas/?${params.toString()}`;
}

export function EncounterCandidatesPanel({
  encontroId,
  capabilities,
}: EncounterCandidatesPanelProps) {
  const allowed = hasValidAccess(capabilities);
  const canViewContact = allowed && capabilities.consultar_contato;
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<EncounterWorkspaceCandidateStatus | "">("");
  const [origin, setOrigin] = useState<EncounterWorkspaceCandidateOrigin | "">("");
  const [page, setPage] = useState(1);
  const [retry, setRetry] = useState(0);
  const [loadResult, setLoadResult] = useState<CandidateLoadResult | null>(null);
  const requestId = useRef(0);

  const requestKey = useMemo(() => JSON.stringify({
    encontroId,
    canViewContact,
    page,
    search,
    status,
    origin,
    retry,
  }), [canViewContact, encontroId, origin, page, retry, search, status]);

  useEffect(() => {
    requestId.current += 1;
    const currentRequestId = requestId.current;

    if (!allowed) {
      return;
    }

    const controller = new AbortController();

    async function load() {
      try {
        const response = await siaFetch(buildCandidatesPath({
          encontroId,
          page,
          search,
          status,
          origin,
        }), { signal: controller.signal });
        if (!response.ok) {
          throw new Error(await readApiError(
            response,
            "Não foi possível carregar os Encontristas.",
          ));
        }
        const body: unknown = await response.json();
        const parsed = canViewContact
          ? parseEncounterCandidatePage(body, parseEncounterCandidateFull)
          : parseEncounterCandidatePage(body, parseEncounterCandidateSummary);
        if (!controller.signal.aborted && requestId.current === currentRequestId) {
          setLoadResult({ requestKey, data: parsed, error: null });
        }
      } catch (caught: unknown) {
        if (!controller.signal.aborted && requestId.current === currentRequestId) {
          setLoadResult({
            requestKey,
            data: null,
            error: errorMessage(caught, "Não foi possível carregar os Encontristas."),
          });
        }
      }
    }

    void load();
    return () => controller.abort();
  }, [allowed, canViewContact, encontroId, origin, page, requestKey, search, status]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  }

  if (!allowed) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6" aria-label="Encontristas">
        <h2 className="text-xl font-bold text-slate-900">Encontristas</h2>
        <p className="mt-2 text-sm text-slate-600">
          A consulta de Encontristas não está disponível neste contexto.
        </p>
      </section>
    );
  }

  const currentResult = loadResult?.requestKey === requestKey ? loadResult : null;
  const currentData = currentResult?.data ?? null;
  const loadError = currentResult?.error ?? null;
  const isLoading = currentResult === null;
  const items = currentData?.results ?? [];

  return (
    <section className="space-y-4" aria-label="Encontristas">
      <header>
        <h2 className="text-2xl font-bold text-slate-900">Encontristas</h2>
        <p className="mt-1 text-sm text-slate-600">
          Consulta canônica do Encontro atual
          {currentData ? ` · ${currentData.count} registro(s)` : ""}
        </p>
      </header>

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 lg:grid-cols-[minmax(0,1fr)_13rem_13rem]">
        <form onSubmit={submitSearch} className="flex min-w-0 gap-2" aria-label="Busca de Encontristas">
          <label className="min-w-0 flex-1 text-sm font-semibold text-slate-700">
            {canViewContact ? "Buscar por nome ou telefone" : "Buscar por nome"}
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal"
            />
          </label>
          <button
            type="submit"
            className="self-end rounded-lg bg-escalada-azul px-4 py-2 font-semibold text-white"
          >
            Buscar
          </button>
        </form>

        <label className="text-sm font-semibold text-slate-700">
          Situação
          <select
            value={status}
            onChange={(event) => {
              setPage(1);
              setStatus(event.target.value as EncounterWorkspaceCandidateStatus | "");
            }}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal"
          >
            <option value="">Todas</option>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        <label className="text-sm font-semibold text-slate-700">
          Origem
          <select
            value={origin}
            onChange={(event) => {
              setPage(1);
              setOrigin(event.target.value as EncounterWorkspaceCandidateOrigin | "");
            }}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal"
          >
            <option value="">Todas</option>
            {ORIGIN_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
      </div>

      {loadError ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          <span>{loadError}</span>
          <button type="button" onClick={() => setRetry((value) => value + 1)} className="font-semibold underline">
            Tentar novamente
          </button>
        </div>
      ) : null}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500" role="status">Carregando Encontristas...</p>
        ) : !loadError && items.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-500">Nenhum Encontrista encontrado.</p>
        ) : !loadError ? (
          <table className="w-full min-w-[44rem] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Nome</th>
                <th className="px-4 py-3">Situação</th>
                <th className="px-4 py-3">Origem</th>
                <th className="px-4 py-3">Pré-Encontro</th>
                <th className="px-4 py-3">Aptidão</th>
                {canViewContact ? <th className="px-4 py-3">Telefone</th> : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((candidate) => (
                <tr key={`${candidate.ref.origem_tipo}:${candidate.ref.origem_id}`}>
                  <td className="px-4 py-3 font-semibold text-slate-900">{candidate.nome}</td>
                  <td className="px-4 py-3 text-slate-700">{candidate.situacao.label}</td>
                  <td className="px-4 py-3 text-slate-700">{candidate.origem.label}</td>
                  <td className="px-4 py-3 text-slate-700">{candidate.presenca_pre ? "Presente" : "Não registrado"}</td>
                  <td className="px-4 py-3 text-slate-700">
                    {candidate.aptidao ? APTITUDE_LABELS[candidate.aptidao] : "Não avaliada"}
                  </td>
                  {canViewContact ? (
                    <td className="px-4 py-3 text-slate-700">
                      {"telefone" in candidate ? candidate.telefone || "Não informado" : "Não informado"}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>

      {!isLoading && !loadError && currentData ? (
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={!currentData.previous}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold disabled:opacity-50"
          >
            Página anterior
          </button>
          <span className="text-sm text-slate-600">Página {page}</span>
          <button
            type="button"
            onClick={() => setPage((value) => value + 1)}
            disabled={!currentData.next}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold disabled:opacity-50"
          >
            Próxima página
          </button>
        </div>
      ) : null}
    </section>
  );
}
