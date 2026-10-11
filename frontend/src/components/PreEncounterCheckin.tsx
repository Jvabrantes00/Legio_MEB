"use client";

import {
  ArrowLeft, Camera, ChevronLeft, ChevronRight, CircleAlert, Search,
  UserPlus, X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { errorMessage, readApiError } from "../lib/form-api-error";
import {
  type PaginatedPreEncounterPersonLookup,
  type PaginatedPreEncounterRegistrationLookup,
  type PreEncounterCare,
  type PreEncounterCareConference,
  type PreEncounterContextCapabilities,
  type PreEncounterDetail,
  type PreEncounterOperationalItem,
  type PreEncounterPaymentStatus,
  parsePreEncounterCare,
  parsePreEncounterCareConference,
  parsePreEncounterContextCapabilities,
  parsePreEncounterDetail,
  parsePreEncounterItems,
  parsePreEncounterPersonLookup,
  parsePreEncounterRegistrationLookup,
} from "../lib/pre-encounter-contract";
import { siaFetch } from "../lib/sia-api";

type Props = {
  encontroId: string;
  initialCapabilities?: PreEncounterContextCapabilities | null;
  capabilitiesError?: string | null;
  onReloadCapabilities?: () => Promise<void>;
};

type Filters = {
  presente: string;
  pagamento: string;
  aptidao: string;
  situacao_vaga: string;
};

const EMPTY_FILTERS: Filters = {
  presente: "",
  pagamento: "",
  aptidao: "",
  situacao_vaga: "",
};

const LABELS = {
  inscricao: "Com inscrição",
  pessoa: "Pessoa cadastrada",
  avulso: "Atendimento avulso",
  pendente: "Pendente",
  pago: "Pago",
  isento: "Isento",
  apto: "Apto",
  nao_apto: "Não apto",
  aguardando_decisao_diretoria: "Aguardando decisão da Diretoria",
  aprovado: "Aprovado",
  nao_aprovado: "Não aprovado",
} as const;

function label(value: string | null): string {
  if (!value) return "Sem decisão";
  return LABELS[value as keyof typeof LABELS] ?? value;
}

function apiErrorFallback(status: number, fallback: string): string {
  if (status === 400) return "Revise os dados informados.";
  if (status === 403) return "Esta operação não está disponível para você.";
  if (status === 404) return "Recurso não encontrado no Encontro atual.";
  if (status === 409) return "O estado mudou durante a operação. Os dados serão atualizados.";
  if (status >= 500) return "Falha no serviço. Tente novamente.";
  return fallback;
}

async function responseError(response: Response, fallback: string) {
  return readApiError(response, apiErrorFallback(response.status, fallback));
}

function buildListPath(
  encontroId: string,
  page: number,
  query: string,
  filters: Filters,
) {
  const base = `/encontros/${encontroId}/pre-encontro/atendimentos`;
  const params = new URLSearchParams({ page: String(page) });
  if (query) {
    params.set("q", query);
    return `${base}/busca/?${params}`;
  }
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  return `${base}/?${params}`;
}

export function PreEncounterCheckin({
  encontroId,
  initialCapabilities,
  capabilitiesError = null,
  onReloadCapabilities,
}: Props) {
  const [capabilities, setCapabilities] = useState(initialCapabilities);
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(initialCapabilities === undefined);
  const [items, setItems] = useState<PreEncounterOperationalItem[]>([]);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [page, setPage] = useState(1);
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<PreEncounterDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [checkinOpen, setCheckinOpen] = useState(false);
  const preEncounterConfigured = capabilities?.pre_encontro_configurado ?? false;
  const canConsultOperation = capabilities?.consultar_operacao ?? false;

  const loadCapabilities = useCallback(async () => {
    setCapabilitiesLoading(true);
    try {
      const response = await siaFetch(`/encontros/${encontroId}/pre-encontro/capabilities/`);
      if (!response.ok) throw new Error(await responseError(response, "Não foi possível consultar as ações disponíveis."));
      setCapabilities(parsePreEncounterContextCapabilities(await response.json()));
    } catch (error: unknown) {
      setCapabilities(null);
      setListError(errorMessage(error, "Não foi possível consultar as ações disponíveis."));
    } finally {
      setCapabilitiesLoading(false);
    }
  }, [encontroId]);

  useEffect(() => {
    if (initialCapabilities !== undefined) return;
    const timer = window.setTimeout(() => void loadCapabilities(), 0);
    return () => window.clearTimeout(timer);
  }, [initialCapabilities, loadCapabilities]);

  useEffect(() => {
    if (initialCapabilities === undefined) return;
    const timer = window.setTimeout(() => setCapabilities(initialCapabilities), 0);
    return () => window.clearTimeout(timer);
  }, [initialCapabilities]);

  const loadList = useCallback(async () => {
    if (!preEncounterConfigured || !canConsultOperation) return;
    setListLoading(true);
    setListError(null);
    try {
      const response = await siaFetch(buildListPath(encontroId, page, query, filters));
      if (!response.ok) throw new Error(await responseError(response, "Não foi possível carregar os atendimentos."));
      const body = parsePreEncounterItems(await response.json());
      setItems(body.results);
      setCount(body.count);
      setHasNext(Boolean(body.next));
      setHasPrevious(Boolean(body.previous));
    } catch (error: unknown) {
      setListError(errorMessage(error, "Não foi possível carregar os atendimentos."));
    } finally {
      setListLoading(false);
    }
  }, [
    canConsultOperation,
    preEncounterConfigured,
    encontroId,
    filters,
    page,
    query,
  ]);

  const loadDetail = useCallback(async (id: number) => {
    setDetailLoading(true);
    try {
      const response = await siaFetch(`/encontros/${encontroId}/pre-encontro/atendimentos/${id}/`);
      if (!response.ok) throw new Error(await responseError(response, "Não foi possível carregar o atendimento."));
      setDetail(parsePreEncounterDetail(await response.json()));
    } catch (error: unknown) {
      toast.error(errorMessage(error, "Não foi possível carregar o atendimento."));
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, [encontroId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadList(), 0);
    return () => window.clearTimeout(timer);
  }, [loadList]);
  useEffect(() => {
    if (selectedId === null) return;
    const timer = window.setTimeout(() => void loadDetail(selectedId), 0);
    return () => window.clearTimeout(timer);
  }, [loadDetail, selectedId]);

  const refresh = useCallback(async () => {
    await Promise.all([
      loadList(),
      selectedId === null ? Promise.resolve() : loadDetail(selectedId),
    ]);
  }, [loadDetail, loadList, selectedId]);

  const handleActionError = useCallback(async (response: Response, fallback: string) => {
    const message = await responseError(response, fallback);
    toast.error(message);
    if ([403, 409].includes(response.status)) {
      await loadCapabilities();
      await refresh();
    }
  }, [loadCapabilities, refresh]);

  if (capabilitiesLoading) return <p className="p-6 text-sm text-gray-500">Carregando Pré-Encontro...</p>;
  if (capabilitiesError) {
    return (
      <section className="rounded-2xl border border-red-200 bg-white p-6" aria-label="Pré-Encontro">
        <h2 className="text-xl font-bold text-gray-900">Pré-Encontro</h2>
        <p className="mt-2 text-sm text-red-700">{capabilitiesError}</p>
        {onReloadCapabilities && <button type="button" onClick={() => void onReloadCapabilities()} className="mt-3 rounded-lg border border-red-300 px-3 py-2 text-sm font-semibold text-red-800">Tentar novamente</button>}
      </section>
    );
  }
  if (capabilities && !capabilities.pre_encontro_configurado) {
    return (
      <PreEncounterEmptyState
        encontroId={encontroId}
        canConfigure={capabilities.configurar_pre_encontro}
        onConfigured={async () => {
          if (onReloadCapabilities) await onReloadCapabilities();
          else await loadCapabilities();
        }}
      />
    );
  }
  if (!capabilities?.consultar_operacao) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-6" aria-label="Pré-Encontro">
        <h2 className="text-xl font-bold text-gray-900">Pré-Encontro</h2>
        <p className="mt-2 text-sm text-gray-600">A operação não está disponível neste contexto.</p>
        {listError && <p className="mt-2 text-sm text-red-700">{listError}</p>}
      </section>
    );
  }

  return (
    <section className="space-y-4" aria-label="Pré-Encontro">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Pré-Encontro</h2>
          <p className="text-sm text-gray-600">Credenciamento do Encontro atual · {count} atendimento(s)</p>
        </div>
        {capabilities.registrar_checkin && (
          <button
            type="button"
            onClick={() => setCheckinOpen(true)}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-escalada-azul px-4 py-2.5 font-semibold text-white hover:bg-blue-800"
          >
            <UserPlus size={18} /> Novo atendimento
          </button>
        )}
      </header>

      <ListControls
        queryInput={queryInput}
        setQueryInput={setQueryInput}
        onSearch={() => { setPage(1); setQuery(queryInput.trim()); }}
        queryActive={Boolean(query)}
        filters={filters}
        setFilters={(next) => { setPage(1); setQuery(""); setFilters(next); }}
      />

      {query && (
        <p className="text-xs text-gray-500">
          Busca ativa por “{query}”. Limpe a busca para aplicar filtros operacionais.
        </p>
      )}
      {listError && (
        <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <span>{listError}</span>
          <button type="button" onClick={() => void loadList()} className="font-semibold underline">Tentar novamente</button>
        </div>
      )}

      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="min-w-0 rounded-xl border border-gray-200 bg-white">
          <PreEncounterList
            items={items}
            loading={listLoading}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <Pagination
            page={page}
            hasNext={hasNext}
            hasPrevious={hasPrevious}
            loading={listLoading}
            onChange={setPage}
          />
        </div>

        {selectedId !== null && (
          <PreEncounterDetailPanel
            encontroId={encontroId}
            detail={detail}
            loading={detailLoading}
            onClose={() => { setSelectedId(null); setDetail(null); }}
            onRefresh={refresh}
            onActionError={handleActionError}
          />
        )}
      </div>

      {checkinOpen && (
        <CheckinFlow
          encontroId={encontroId}
          onClose={() => setCheckinOpen(false)}
          onCreated={async (created) => {
            setCheckinOpen(false);
            setSelectedId(created.id);
            setPage(1);
            toast.success("Presença registrada");
            await loadList();
          }}
          onActionError={handleActionError}
        />
      )}
    </section>
  );
}

function PreEncounterEmptyState({ encontroId, canConfigure, onConfigured }: {
  encontroId: string;
  canConfigure: boolean;
  onConfigured: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({ horario: "", local: "", observacoes: "" });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!values.horario || !values.local.trim()) {
      setError("Informe horário e local.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await jsonCommand(
        `/encontros/${encontroId}/pre-encontro/configurar/`,
        "POST",
        { ...values, local: values.local.trim() },
      );
      if (!response.ok) {
        setError(await responseError(response, "Não foi possível configurar o Pré-Encontro."));
        return;
      }
      toast.success("Pré-Encontro configurado");
      await onConfigured();
    } catch (caught: unknown) {
      setError(errorMessage(caught, "Falha ao configurar o Pré-Encontro."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6" aria-label="Pré-Encontro">
      <h2 className="text-2xl font-bold text-gray-900">Pré-Encontro</h2>
      <p className="mt-3 text-gray-600">Nenhum Pré-Encontro configurado para este Encontro.</p>
      {canConfigure && !open && <button type="button" onClick={() => setOpen(true)} className="mt-4 rounded-lg bg-escalada-azul px-4 py-2.5 font-semibold text-white">Configurar Pré-Encontro</button>}
      {canConfigure && open && <form onSubmit={submit} className="mt-5 grid max-w-xl gap-3 rounded-xl border bg-gray-50 p-4 sm:grid-cols-2">
        <label className="text-sm font-medium">Horário<input required type="time" value={values.horario} onChange={(event) => setValues({ ...values, horario: event.target.value })} className="mt-1 w-full rounded-lg border bg-white p-2" /></label>
        <label className="text-sm font-medium sm:col-span-2">Local<input required value={values.local} onChange={(event) => setValues({ ...values, local: event.target.value })} className="mt-1 w-full rounded-lg border bg-white p-2" /></label>
        <label className="text-sm font-medium sm:col-span-2">Observações (opcional)<textarea value={values.observacoes} onChange={(event) => setValues({ ...values, observacoes: event.target.value })} className="mt-1 min-h-20 w-full rounded-lg border bg-white p-2" /></label>
        {error && <p role="alert" className="text-sm font-medium text-red-700 sm:col-span-2">{error}</p>}
        <div className="flex gap-2 sm:col-span-2"><button disabled={busy} className="rounded-lg bg-escalada-azul px-4 py-2 font-semibold text-white disabled:opacity-50">{busy ? "Configurando..." : "Confirmar configuração"}</button><button type="button" disabled={busy} onClick={() => setOpen(false)} className="rounded-lg border px-4 py-2 font-semibold">Cancelar</button></div>
      </form>}
    </section>
  );
}

function ListControls({
  queryInput, setQueryInput, onSearch, queryActive, filters, setFilters,
}: {
  queryInput: string;
  setQueryInput: (value: string) => void;
  onSearch: () => void;
  queryActive: boolean;
  filters: Filters;
  setFilters: (value: Filters) => void;
}) {
  return (
    <div className="space-y-3 rounded-xl border border-gray-200 bg-white p-4">
      <form
        className="flex gap-2"
        onSubmit={(event) => { event.preventDefault(); onSearch(); }}
      >
        <label className="relative flex-1">
          <span className="sr-only">Buscar atendimento</span>
          <Search className="absolute left-3 top-3 text-gray-400" size={18} />
          <input
            value={queryInput}
            onChange={(event) => setQueryInput(event.target.value)}
            placeholder="Nome, CPF, telefone ou inscrição"
            className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-3 outline-none focus:ring-2 focus:ring-escalada-azul"
          />
        </label>
        <button type="submit" className="rounded-lg border border-escalada-azul px-4 font-semibold text-escalada-azul">Buscar</button>
      </form>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Filter label="Presença" value={filters.presente} disabled={queryActive} options={[["true", "Presente"], ["false", "Ausente"]]} onChange={(value) => setFilters({ ...filters, presente: value })} />
        <Filter label="Pagamento" value={filters.pagamento} disabled={queryActive} options={[["pendente", "Pendente"], ["pago", "Pago"], ["isento", "Isento"]]} onChange={(value) => setFilters({ ...filters, pagamento: value })} />
        <Filter label="Aptidão" value={filters.aptidao} disabled={queryActive} options={[["apto", "Apto"], ["nao_apto", "Não apto"], ["aguardando_decisao_diretoria", "Aguardando Diretoria"]]} onChange={(value) => setFilters({ ...filters, aptidao: value })} />
        <Filter label="Vaga" value={filters.situacao_vaga} disabled={queryActive} options={[["aguardando_decisao_diretoria", "Aguardando Diretoria"], ["aprovado", "Aprovado"], ["nao_aprovado", "Não aprovado"]]} onChange={(value) => setFilters({ ...filters, situacao_vaga: value })} />
      </div>
    </div>
  );
}

function Filter({ label: title, value, disabled, options, onChange }: {
  label: string;
  value: string;
  disabled: boolean;
  options: [string, string][];
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs font-medium text-gray-600">
      {title}
      <select value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-2 py-2 text-sm disabled:bg-gray-100">
        <option value="">Todos</option>
        {options.map(([option, text]) => <option key={option} value={option}>{text}</option>)}
      </select>
    </label>
  );
}

function PreEncounterList({ items, loading, selectedId, onSelect }: {
  items: PreEncounterOperationalItem[];
  loading: boolean;
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  if (loading) return <p className="p-8 text-center text-sm text-gray-500">Carregando atendimentos...</p>;
  if (!items.length) return <p className="p-8 text-center text-sm text-gray-500">Nenhum atendimento encontrado.</p>;
  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50 text-xs uppercase text-gray-500"><tr>
            <th className="px-3 py-3">Pessoa</th><th className="px-3 py-3">Origem</th>
            <th className="px-3 py-3">Pagamento</th><th className="px-3 py-3">Vaga / aptidão</th>
            <th className="px-3 py-3">Foto</th><th className="px-3 py-3">Cuidados</th>
          </tr></thead>
          <tbody className="divide-y">
            {items.map((item) => (
              <tr key={item.id} onClick={() => onSelect(item.id)} className={`cursor-pointer hover:bg-blue-50 ${selectedId === item.id ? "bg-blue-50" : ""}`}>
                <td className="px-3 py-3 font-semibold text-gray-900">{item.identificacao}<span className="block text-xs font-normal text-gray-500">Presente</span></td>
                <td className="px-3 py-3">{label(item.origem)}</td>
                <td className="px-3 py-3">{label(item.pagamento)}</td>
                <td className={`px-3 py-3 ${item.aptidao.situacao === "aguardando_decisao_diretoria" ? "font-bold text-red-700" : ""}`}>
                  {label(item.situacao_vaga ?? item.aptidao.situacao)}
                </td>
                <td className="px-3 py-3">{item.possui_foto ? "Disponível" : "Pendente"}</td>
                <td className="px-3 py-3">{item.possui_dados_cuidado ? (item.cuidado_conferido ? "Conferidos" : "A conferir") : "Sem dados"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="divide-y md:hidden">
        {items.map((item) => (
          <li key={item.id}>
            <button type="button" onClick={() => onSelect(item.id)} className="w-full p-4 text-left hover:bg-blue-50">
              <span className="font-semibold text-gray-900">{item.identificacao}</span>
              <span className="mt-1 block text-xs text-gray-500">{label(item.origem)} · {label(item.pagamento)} · {item.possui_foto ? "Com foto" : "Sem foto"}</span>
              <span className={`mt-2 block text-sm ${item.aptidao.situacao === "aguardando_decisao_diretoria" ? "font-bold text-red-700" : "text-gray-700"}`}>{label(item.aptidao.situacao)}</span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

function Pagination({ page, hasNext, hasPrevious, loading, onChange }: {
  page: number; hasNext: boolean; hasPrevious: boolean; loading: boolean; onChange: (page: number) => void;
}) {
  return (
    <div className="flex items-center justify-between border-t p-3 text-sm">
      <button type="button" aria-label="Página anterior" disabled={!hasPrevious || loading} onClick={() => onChange(page - 1)} className="inline-flex items-center gap-1 rounded border px-3 py-2 disabled:opacity-40"><ChevronLeft size={16} /> Anterior</button>
      <span>Página {page}</span>
      <button type="button" aria-label="Próxima página" disabled={!hasNext || loading} onClick={() => onChange(page + 1)} className="inline-flex items-center gap-1 rounded border px-3 py-2 disabled:opacity-40">Próxima <ChevronRight size={16} /></button>
    </div>
  );
}

function PreEncounterDetailPanel({ encontroId, detail, loading, onClose, onRefresh, onActionError }: {
  encontroId: string;
  detail: PreEncounterDetail | null;
  loading: boolean;
  onClose: () => void;
  onRefresh: () => Promise<void>;
  onActionError: (response: Response, fallback: string) => Promise<void>;
}) {
  return (
    <aside className="fixed inset-0 z-40 overflow-y-auto bg-white p-4 lg:static lg:z-auto lg:max-h-[75vh] lg:rounded-xl lg:border lg:border-gray-200 lg:p-5" aria-label="Painel do atendimento">
      <button type="button" onClick={onClose} className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-escalada-azul lg:float-right lg:text-gray-500"><ArrowLeft size={18} /><span className="lg:hidden">Voltar à lista</span><X className="hidden lg:block" size={18} /></button>
      {loading || !detail ? <p className="clear-both py-8 text-center text-sm text-gray-500">Carregando atendimento...</p> : (
        <div className="clear-both space-y-5">
          <div>
            <h3 className="text-xl font-bold text-gray-900">{detail.identificacao}</h3>
            <p className="text-sm text-gray-500">{label(detail.origem)} · presença registrada</p>
            {!detail.inscricao_id && <p className="mt-2 rounded-lg bg-amber-50 p-2 text-sm font-medium text-amber-900">Sem inscrição vinculada</p>}
          </div>
          <section className="rounded-lg border p-3">
            <h4 className="font-semibold">Aptidão e vaga</h4>
            <p className={`mt-1 text-sm ${detail.aptidao.situacao === "aguardando_decisao_diretoria" ? "font-bold text-red-700" : ""}`}>{label(detail.aptidao.situacao)}</p>
            <p className="mt-1 text-xs text-gray-600">{detail.aptidao.motivo}</p>
            <p className="mt-2 text-xs text-gray-500">Pagamento, foto e conferência de cuidados não são impeditivos de aptidão.</p>
          </section>
          <VacancyDecisionSection encontroId={encontroId} detail={detail} onRefresh={onRefresh} onActionError={onActionError} />
          {detail.capabilities.registrar_pagamento && <PaymentSection encontroId={encontroId} detail={detail} onRefresh={onRefresh} onActionError={onActionError} />}
          {(detail.capabilities.visualizar_foto || detail.capabilities.alterar_foto) && <PhotoSection encontroId={encontroId} detail={detail} onRefresh={onRefresh} onActionError={onActionError} />}
          {detail.capabilities.consultar_cuidados && detail.possui_dados_cuidado && <CareSection encontroId={encontroId} detail={detail} onRefresh={onRefresh} onActionError={onActionError} />}
          {detail.capabilities.regularizar && <RegularizationSection encontroId={encontroId} detail={detail} onRefresh={onRefresh} onActionError={onActionError} />}
        </div>
      )}
    </aside>
  );
}

function VacancyDecisionSection({ encontroId, detail, onRefresh, onActionError }: ActionSectionProps) {
  const [busy, setBusy] = useState(false);
  if (detail.situacao_vaga !== "aguardando_decisao_diretoria") return null;
  async function decide(status: "aprovado" | "nao_aprovado") {
    if (status === "nao_aprovado" && !window.confirm("Confirmar que esta vaga não será aprovada?")) return;
    setBusy(true);
    try {
      const response = await jsonCommand(`/encontros/${encontroId}/pre-encontro/atendimentos/${detail.id}/decisao-vaga/`, "POST", { status });
      if (!response.ok) return await onActionError(response, "Não foi possível registrar a decisão.");
      toast.success("Decisão registrada");
      await onRefresh();
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha de conexão.")); }
    finally { setBusy(false); }
  }
  return (
    <section className="rounded-lg border-2 border-red-300 bg-red-50 p-3">
      <h4 className="flex items-center gap-2 font-bold text-red-800"><CircleAlert size={18} /> Aguardando decisão da Diretoria</h4>
      {detail.capabilities.decidir_vaga && <div className="mt-3 flex gap-2"><button disabled={busy} onClick={() => void decide("aprovado")} className="rounded bg-escalada-azul px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Aprovar</button><button disabled={busy} onClick={() => void decide("nao_aprovado")} className="rounded border border-red-700 px-3 py-2 text-sm font-semibold text-red-800 disabled:opacity-50">Não aprovar</button></div>}
    </section>
  );
}

type ActionSectionProps = {
  encontroId: string;
  detail: PreEncounterDetail;
  onRefresh: () => Promise<void>;
  onActionError: (response: Response, fallback: string) => Promise<void>;
};

async function jsonCommand(path: string, method: "POST" | "PUT", body: object) {
  return siaFetch(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

function PaymentSection({ encontroId, detail, onRefresh, onActionError }: ActionSectionProps) {
  const [paidOpen, setPaidOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [forma, setForma] = useState("pix");
  const [valor, setValor] = useState("");
  async function update(status: PreEncounterPaymentStatus) {
    setBusy(true);
    try {
      const payload = status === "pago" ? { status, forma, valor: valor || null } : { status };
      const response = await jsonCommand(`/encontros/${encontroId}/pre-encontro/atendimentos/${detail.id}/pagamento/`, "PUT", payload);
      if (!response.ok) return await onActionError(response, "Não foi possível atualizar o pagamento.");
      toast.success("Pagamento atualizado"); setPaidOpen(false); await onRefresh();
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha de conexão.")); }
    finally { setBusy(false); }
  }
  return (
    <section className="rounded-lg border p-3">
      <h4 className="font-semibold">Pagamento</h4><p className="text-sm text-gray-600">Status atual: {label(detail.pagamento)}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button disabled={busy} onClick={() => void update("pendente")} className="rounded border px-2 py-1 text-xs">Pendente</button>
        <button disabled={busy} onClick={() => setPaidOpen(true)} className="rounded border px-2 py-1 text-xs">Registrar pago</button>
        <button disabled={busy} onClick={() => void update("isento")} className="rounded border px-2 py-1 text-xs">Isento</button>
      </div>
      {paidOpen && <div className="mt-3 grid gap-2 rounded bg-gray-50 p-3"><label className="text-xs">Forma<select aria-label="Forma de pagamento" value={forma} onChange={(event) => setForma(event.target.value)} className="mt-1 w-full rounded border p-2"><option value="pix">PIX</option><option value="dinheiro">Dinheiro</option><option value="cartao">Cartão</option><option value="outro">Outro</option></select></label><label className="text-xs">Valor<input aria-label="Valor pago" inputMode="decimal" value={valor} onChange={(event) => setValor(event.target.value)} className="mt-1 w-full rounded border p-2" /></label><button disabled={busy} onClick={() => void update("pago")} className="rounded bg-escalada-azul p-2 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Salvando..." : "Confirmar pagamento"}</button></div>}
    </section>
  );
}

function CareSection({ encontroId, detail, onRefresh, onActionError }: ActionSectionProps) {
  const [care, setCare] = useState<PreEncounterCare | null>(null);
  const [conference, setConference] = useState<PreEncounterCareConference | null>(null);
  const [loading, setLoading] = useState(false);
  async function loadCare() {
    setLoading(true);
    try {
      const response = await siaFetch(`/encontros/${encontroId}/pre-encontro/atendimentos/${detail.id}/cuidados/`);
      if (!response.ok) return await onActionError(response, "Não foi possível consultar os cuidados.");
      setCare(parsePreEncounterCare(await response.json()));
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha de conexão.")); }
    finally { setLoading(false); }
  }
  async function check() {
    setLoading(true);
    try {
      const response = await jsonCommand(`/encontros/${encontroId}/pre-encontro/atendimentos/${detail.id}/cuidados/conferir/`, "POST", {});
      if (!response.ok) return await onActionError(response, "Não foi possível conferir os cuidados.");
      setConference(parsePreEncounterCareConference(await response.json()));
      toast.success("Cuidados conferidos"); await onRefresh();
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha de conexão.")); }
    finally { setLoading(false); }
  }
  return (
    <section className="rounded-lg border p-3">
      <h4 className="font-semibold">Cuidados</h4>
      {!care ? <button disabled={loading} onClick={() => void loadCare()} className="mt-2 rounded border px-3 py-2 text-sm font-semibold">{loading ? "Carregando..." : "Ver cuidados"}</button> : <div className="mt-3 space-y-2 text-sm"><p className="rounded bg-blue-50 p-2 text-blue-900">Informações declaradas; esta conferência não representa aprovação médica.</p>{Object.entries(care).map(([key, value]) => value ? <p key={key}><strong>{key.replaceAll("_", " ")}:</strong> {value}</p> : null)}{detail.capabilities.conferir_cuidados && <button disabled={loading} onClick={() => void check()} className="rounded bg-escalada-azul px-3 py-2 font-semibold text-white">Marcar como conferido</button>}</div>}
      {conference?.dados_alterados_apos_conferencia && <p className="mt-2 font-semibold text-red-700">Dados alterados após a última conferência</p>}
      {conference?.conferido && <p className="mt-2 text-xs text-gray-500">Conferido por {conference.ator} em {new Date(conference.conferido_em).toLocaleString("pt-BR")}</p>}
    </section>
  );
}

function PhotoSection({ encontroId, detail, onRefresh, onActionError }: ActionSectionProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const objectUrl = useRef<string | null>(null);
  useEffect(() => () => { if (objectUrl.current) URL.revokeObjectURL(objectUrl.current); }, []);
  async function openPreview() {
    setBusy(true);
    try {
      const response = await siaFetch(`/encontros/${encontroId}/pre-encontro/atendimentos/${detail.id}/foto/`);
      if (!response.ok) return await onActionError(response, "Não foi possível abrir a foto.");
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
      objectUrl.current = URL.createObjectURL(await response.blob());
      setPreview(objectUrl.current);
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha ao carregar a imagem.")); }
    finally { setBusy(false); }
  }
  async function upload() {
    if (!file) return;
    setBusy(true);
    try {
      const body = new FormData(); body.set("foto", file);
      const response = await siaFetch(`/encontros/${encontroId}/pre-encontro/atendimentos/${detail.id}/foto/`, { method: "PUT", body });
      if (!response.ok) return await onActionError(response, "Não foi possível enviar a foto.");
      setFile(null); toast.success("Foto atualizada"); await onRefresh();
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha no envio da foto.")); }
    finally { setBusy(false); }
  }
  return (
    <section className="rounded-lg border p-3">
      <h4 className="flex items-center gap-2 font-semibold"><Camera size={17} /> Foto</h4>
      <p className="text-sm text-gray-600">{detail.possui_foto ? "Foto disponível" : "Foto ainda não adicionada"}</p>
      {detail.capabilities.visualizar_foto && detail.possui_foto && <button disabled={busy} onClick={() => void openPreview()} className="mt-2 rounded border px-3 py-2 text-sm">Abrir preview privado</button>}
      {preview && <div className="mt-3">
        {/* eslint-disable-next-line @next/next/no-img-element -- blob autenticado não pode passar pelo otimizador */}
        <img src={preview} alt={`Foto de ${detail.identificacao}`} className="max-h-56 rounded-lg object-contain" />
        <button onClick={() => setPreview(null)} className="mt-1 text-xs underline">Fechar preview</button>
      </div>}
      {detail.capabilities.alterar_foto && <div className="mt-3 space-y-2"><input aria-label="Selecionar ou capturar foto" type="file" accept="image/*" capture="environment" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="block w-full text-xs" />{file && <button disabled={busy} onClick={() => void upload()} className="rounded bg-escalada-azul px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Enviando..." : detail.possui_foto ? "Substituir foto" : "Confirmar envio"}</button>}</div>}
    </section>
  );
}

function RegularizationSection({ encontroId, detail, onRefresh, onActionError }: ActionSectionProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"inscricao" | "pessoa">("inscricao");
  const [query, setQuery] = useState("");
  const [registrations, setRegistrations] = useState<PaginatedPreEncounterRegistrationLookup | null>(null);
  const [people, setPeople] = useState<PaginatedPreEncounterPersonLookup | null>(null);
  const [busy, setBusy] = useState(false);
  async function search() {
    if (mode === "pessoa" && query.trim().length < 2) return toast.error("Informe ao menos 2 caracteres.");
    setBusy(true);
    try {
      const path = `/encontros/${encontroId}/pre-encontro/atendimentos/${detail.id}/regularizacao/${mode === "pessoa" ? "pessoas" : "inscricoes"}/?q=${encodeURIComponent(query.trim())}`;
      const response = await siaFetch(path);
      if (!response.ok) return await onActionError(response, "Não foi possível localizar vínculos para regularização.");
      const body: unknown = await response.json();
      if (mode === "pessoa") setPeople(parsePreEncounterPersonLookup(body));
      else setRegistrations(parsePreEncounterRegistrationLookup(body));
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha de conexão.")); }
    finally { setBusy(false); }
  }
  async function regularize(payload: { pessoa_id?: number; inscricao_id?: number }) {
    setBusy(true);
    try {
      const response = await jsonCommand(`/encontros/${encontroId}/pre-encontro/atendimentos/${detail.id}/regularizar/`, "POST", payload);
      if (!response.ok) return await onActionError(response, "Não foi possível regularizar o atendimento.");
      toast.success("Atendimento regularizado"); setOpen(false); await onRefresh();
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha de conexão.")); }
    finally { setBusy(false); }
  }
  return (
    <section className="rounded-lg border p-3"><button type="button" onClick={() => setOpen(!open)} className="font-semibold text-escalada-azul">Regularizar atendimento</button>{open && <div className="mt-3 space-y-2"><div className="flex gap-2"><button onClick={() => setMode("inscricao")} className={`rounded border px-2 py-1 text-xs ${mode === "inscricao" ? "bg-blue-50" : ""}`}>Inscrição</button><button onClick={() => setMode("pessoa")} className={`rounded border px-2 py-1 text-xs ${mode === "pessoa" ? "bg-blue-50" : ""}`}>Pessoa</button></div><div className="flex gap-2"><input aria-label="Buscar vínculo para regularização" value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 rounded border p-2 text-sm" /><button disabled={busy} onClick={() => void search()} className="rounded border px-2 text-sm">Buscar</button></div><LookupResults registrations={mode === "inscricao" ? registrations : null} people={mode === "pessoa" ? people : null} onRegistration={(id) => void regularize({ inscricao_id: id })} onPerson={(id) => void regularize({ pessoa_id: id })} /></div>}</section>
  );
}

function LookupResults({ registrations, people, onRegistration, onPerson }: {
  registrations: PaginatedPreEncounterRegistrationLookup | null;
  people: PaginatedPreEncounterPersonLookup | null;
  onRegistration: (id: number) => void;
  onPerson: (id: number) => void;
}) {
  return <ul className="max-h-52 divide-y overflow-y-auto rounded border">{registrations?.results.map((item) => <li key={item.inscricao_id}><button className="w-full p-2 text-left text-sm hover:bg-gray-50" onClick={() => onRegistration(item.inscricao_id)}><strong>{item.nome}</strong><span className="block text-xs text-gray-500">{item.identificador} · {item.cpf_mascarado ?? "CPF não informado"}</span></button></li>)}{people?.results.map((item) => <li key={item.pessoa_id}><button className="w-full p-2 text-left text-sm hover:bg-gray-50" onClick={() => onPerson(item.pessoa_id)}><strong>{item.nome}</strong><span className="block text-xs text-gray-500">{item.cpf_mascarado ?? "CPF não informado"} · {item.telefone_mascarado ?? "Sem telefone"}</span></button></li>)}</ul>;
}

function CheckinFlow({ encontroId, onClose, onCreated, onActionError }: {
  encontroId: string;
  onClose: () => void;
  onCreated: (detail: PreEncounterDetail) => Promise<void>;
  onActionError: (response: Response, fallback: string) => Promise<void>;
}) {
  const [mode, setMode] = useState<"choose" | "inscricao" | "pessoa" | "avulso">("choose");
  const [query, setQuery] = useState("");
  const [registrations, setRegistrations] = useState<PaginatedPreEncounterRegistrationLookup | null>(null);
  const [people, setPeople] = useState<PaginatedPreEncounterPersonLookup | null>(null);
  const [busy, setBusy] = useState(false);
  const [walkin, setWalkin] = useState({ nome_informado: "", data_nascimento_informada: "", telefone_informado: "", cpf_informado: "" });
  const [validation, setValidation] = useState<string | null>(null);
  async function create(payload: object) {
    setBusy(true); setValidation(null);
    try {
      const response = await jsonCommand(`/encontros/${encontroId}/pre-encontro/check-in/`, "POST", payload);
      if (!response.ok) return await onActionError(response, "Não foi possível registrar a presença.");
      await onCreated(parsePreEncounterDetail(await response.json()));
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha de conexão.")); }
    finally { setBusy(false); }
  }
  async function search() {
    if (mode === "pessoa" && query.trim().length < 2) return setValidation("Informe ao menos 2 caracteres.");
    setBusy(true); setValidation(null);
    try {
      const path = `/encontros/${encontroId}/pre-encontro/lookups/${mode === "pessoa" ? "pessoas" : "inscricoes"}/?q=${encodeURIComponent(query.trim())}`;
      const response = await siaFetch(path);
      if (!response.ok) return await onActionError(response, "Não foi possível consultar as opções.");
      const body: unknown = await response.json();
      if (mode === "pessoa") setPeople(parsePreEncounterPersonLookup(body));
      else setRegistrations(parsePreEncounterRegistrationLookup(body));
    } catch (error: unknown) { toast.error(errorMessage(error, "Falha de conexão.")); }
    finally { setBusy(false); }
  }
  function submitWalkin(event: FormEvent) {
    event.preventDefault();
    if (!walkin.nome_informado.trim() || !walkin.data_nascimento_informada || !walkin.telefone_informado.trim()) {
      setValidation("Informe nome, data de nascimento e telefone."); return;
    }
    void create({ ...walkin, cpf_informado: walkin.cpf_informado.trim() || null });
  }
  const title = mode === "choose" ? "Novo atendimento" : `Novo atendimento · ${label(mode)}`;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="checkin-title">
      <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-2xl sm:max-w-lg sm:rounded-2xl">
        <div className="flex items-center justify-between"><h3 id="checkin-title" className="text-xl font-bold">{title}</h3><button aria-label="Fechar novo atendimento" onClick={onClose}><X /></button></div>
        {mode === "choose" ? <div className="mt-5 grid gap-3"><button onClick={() => setMode("inscricao")} className="rounded-xl border p-4 text-left font-semibold hover:border-escalada-azul">1. Com inscrição</button><button onClick={() => setMode("pessoa")} className="rounded-xl border p-4 text-left font-semibold hover:border-escalada-azul">2. Pessoa já cadastrada</button><button onClick={() => setMode("avulso")} className="rounded-xl border p-4 text-left font-semibold hover:border-escalada-azul">3. Atendimento avulso</button></div> : <button onClick={() => { setMode("choose"); setValidation(null); }} className="mt-3 text-sm font-semibold text-escalada-azul">← Alterar origem</button>}
        {(mode === "inscricao" || mode === "pessoa") && <div className="mt-4 space-y-3"><div className="flex gap-2"><input aria-label={mode === "pessoa" ? "Buscar Pessoa" : "Buscar inscrição"} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nome, CPF, telefone ou identificador" className="min-w-0 flex-1 rounded border p-2" /><button disabled={busy} onClick={() => void search()} className="rounded bg-escalada-azul px-3 text-white">Buscar</button></div><LookupResults registrations={mode === "inscricao" ? registrations : null} people={mode === "pessoa" ? people : null} onRegistration={(id) => void create({ inscricao_id: id })} onPerson={(id) => void create({ pessoa_id: id })} /></div>}
        {mode === "avulso" && <form className="mt-4 grid gap-3" onSubmit={submitWalkin}><label className="text-sm font-medium">Nome<input value={walkin.nome_informado} onChange={(event) => setWalkin({ ...walkin, nome_informado: event.target.value })} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm font-medium">Data de nascimento<input type="date" value={walkin.data_nascimento_informada} onChange={(event) => setWalkin({ ...walkin, data_nascimento_informada: event.target.value })} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm font-medium">Telefone<input value={walkin.telefone_informado} onChange={(event) => setWalkin({ ...walkin, telefone_informado: event.target.value })} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm font-medium">CPF (opcional)<input value={walkin.cpf_informado} onChange={(event) => setWalkin({ ...walkin, cpf_informado: event.target.value })} className="mt-1 w-full rounded border p-2" /></label><button disabled={busy} className="rounded bg-escalada-azul p-3 font-semibold text-white disabled:opacity-50">{busy ? "Registrando..." : "Registrar presença"}</button></form>}
        {validation && <p role="alert" className="mt-3 text-sm font-medium text-red-700">{validation}</p>}
      </div>
    </div>
  );
}
