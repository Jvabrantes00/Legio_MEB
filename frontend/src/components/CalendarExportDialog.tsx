"use client";

import { Download, ExternalLink, FileClock, Loader2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { keepFocusInsideDialog } from "../lib/dialog-focus";
import { errorMessage, readApiError } from "../lib/form-api-error";
import { MONTH_LABELS, type CalendarView } from "../lib/institutional-calendar";
import { siaFetch } from "../lib/sia-api";

export type CalendarExportScope = "PUBLICO" | "INTERNO";
export type CalendarExportFormat = "MONTH" | "YEAR_MONTHLY" | "YEAR_SUMMARY";

export interface CalendarPublication {
  id: number;
  escopo: CalendarExportScope;
  periodo: "MES" | "ANO";
  layout: "MENSAL" | "ANUAL_RESUMIDO";
  ano: number;
  mes: number | null;
  publicado_em: string;
  publicado_por: string;
  sha256: string;
  hash_abreviado: string;
  download_url: string;
}

export interface ExportSelection {
  scope: CalendarExportScope;
  format: CalendarExportFormat;
  year: number;
  month: number;
}

type CalendarRequest = (path: string, init?: RequestInit) => Promise<Response>;

interface CalendarExportDialogProps {
  open: boolean;
  year: number;
  month: number;
  view: CalendarView;
  canManage: boolean;
  onClose: () => void;
}

const FORMAT_LABELS: Record<CalendarExportFormat, string> = {
  MONTH: "Mês selecionado",
  YEAR_MONTHLY: "Ano completo — páginas mensais",
  YEAR_SUMMARY: "Ano completo — visão resumida",
};

export function buildCalendarExportParams(selection: ExportSelection): URLSearchParams {
  const params = new URLSearchParams({
    escopo: selection.scope,
    ano: String(selection.year),
  });
  if (selection.format === "MONTH") {
    params.set("periodo", "MES");
    params.set("layout", "MENSAL");
    params.set("mes", String(selection.month + 1));
  } else if (selection.format === "YEAR_MONTHLY") {
    params.set("periodo", "ANO");
    params.set("layout", "MENSAL");
  } else {
    params.set("periodo", "ANO");
    params.set("layout", "ANUAL_RESUMIDO");
  }
  return params;
}

export function publicationSummary(selection: ExportSelection): string[] {
  return [
    selection.scope === "PUBLICO" ? "Público" : "Interno",
    selection.format === "MONTH"
      ? `${MONTH_LABELS[selection.month]} de ${selection.year}`
      : `Ano ${selection.year}`,
    `Formato: ${FORMAT_LABELS[selection.format]}`,
  ];
}

export function requestCalendarPreview(
  selection: ExportSelection,
  request: CalendarRequest = siaFetch,
): Promise<Response> {
  const params = buildCalendarExportParams(selection);
  return request(`/calendario-institucional/preview-pdf/?${params}`);
}

export function publishCalendarVersion(
  selection: ExportSelection,
  request: CalendarRequest = siaFetch,
): Promise<Response> {
  return request("/calendario-institucional/publicacoes/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(Object.fromEntries(buildCalendarExportParams(selection))),
  });
}

export function requestCalendarPublicationHistory(
  request: CalendarRequest = siaFetch,
): Promise<Response> {
  return request("/calendario-institucional/publicacoes/");
}

export function requestCalendarPublicationDownload(
  downloadUrl: string,
  request: CalendarRequest = siaFetch,
): Promise<Response> {
  return request(downloadUrl);
}

export function PublicationConfirmation({
  selection,
  busy,
  onCancel,
  onPublish,
}: {
  selection: ExportSelection;
  busy: boolean;
  onCancel: () => void;
  onPublish: () => void;
}) {
  return <div className="mt-5 rounded-2xl border border-blue-200 bg-blue-50 p-4" role="alertdialog" aria-labelledby="calendar-publish-confirmation"><h3 id="calendar-publish-confirmation" className="font-black text-slate-950">Publicar esta versão do Calendário Institucional?</h3><ul className="mt-2 text-sm text-slate-700">{publicationSummary(selection).map((item) => <li key={item}>{item}</li>)}</ul><p className="mt-3 text-sm font-medium text-slate-700">Esta versão será preservada no histórico e não poderá ser alterada.</p><div className="mt-4 flex justify-end gap-2"><button type="button" onClick={onCancel} disabled={busy} className="calendar-control px-3 text-sm font-bold">Cancelar</button><button type="button" onClick={onPublish} disabled={busy} className="rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">{busy ? "Publicando..." : "Publicar versão"}</button></div></div>;
}

function responseFilename(response: Response, fallback: string): string {
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const basic = disposition.match(/filename="?([^";]+)"?/i)?.[1];
  const value = utf8 ?? basic;
  return value ? decodeURIComponent(value) : fallback;
}

function previewFallback(selection: ExportSelection): string {
  if (selection.format === "MONTH") {
    return `calendario-${selection.scope.toLowerCase()}-${selection.year}-${String(selection.month + 1).padStart(2, "0")}.pdf`;
  }
  const suffix = selection.format === "YEAR_MONTHLY" ? "mensal" : "resumido";
  return `calendario-${selection.scope.toLowerCase()}-${selection.year}-${suffix}.pdf`;
}

async function downloadResponse(response: Response, fallback: string) {
  const blob = await response.blob();
  return {
    url: URL.createObjectURL(blob),
    filename: responseFilename(response, fallback),
  };
}

function formatPublication(item: CalendarPublication): string {
  if (item.periodo === "MES" && item.mes) {
    return `${MONTH_LABELS[item.mes - 1]} ${item.ano} — Mensal`;
  }
  return item.layout === "MENSAL"
    ? `${item.ano} — Páginas mensais`
    : `${item.ano} — Visão resumida`;
}

export function CalendarExportDialog({
  open,
  year,
  month,
  view,
  canManage,
  onClose,
}: CalendarExportDialogProps) {
  const dialog = useRef<HTMLElement>(null);
  const busyRef = useRef<"preview" | "publish" | "download" | null>(null);
  const [scope, setScope] = useState<CalendarExportScope>("PUBLICO");
  const [format, setFormat] = useState<CalendarExportFormat>(
    view === "month" ? "MONTH" : "YEAR_SUMMARY",
  );
  const [busy, setBusy] = useState<"preview" | "publish" | "download" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ url: string; filename: string } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [history, setHistory] = useState<CalendarPublication[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const selection: ExportSelection = { scope, format, year, month };

  useEffect(() => {
    busyRef.current = busy;
  }, [busy]);

  const clearPreview = useCallback(() => {
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current.url);
      return null;
    });
    setConfirming(false);
    setSuccess(null);
  }, []);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const response = await requestCalendarPublicationHistory();
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível carregar o histórico."));
      setHistory(await response.json() as CalendarPublication[]);
    } catch (cause: unknown) {
      setError(errorMessage(cause, "Não foi possível carregar o histórico."));
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open || !canManage) return;
    const previous = document.activeElement as HTMLElement | null;
    const timer = window.setTimeout(() => {
      dialog.current?.focus();
      void loadHistory();
    }, 0);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busyRef.current) onClose();
      keepFocusInsideDialog(event, dialog.current);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("keydown", onKeyDown);
      previous?.focus();
    };
  }, [canManage, loadHistory, onClose, open]);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview.url);
  }, [preview]);

  if (!open || !canManage) return null;

  const updateScope = (value: CalendarExportScope) => {
    clearPreview();
    setScope(value);
  };
  const updateFormat = (value: CalendarExportFormat) => {
    clearPreview();
    setFormat(value);
  };

  const generatePreview = async () => {
    setBusy("preview");
    setError(null);
    setSuccess(null);
    try {
      const response = await requestCalendarPreview(selection);
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível gerar o preview."));
      clearPreview();
      setPreview(await downloadResponse(response, previewFallback(selection)));
    } catch (cause: unknown) {
      setError(errorMessage(cause, "Não foi possível gerar o preview."));
    } finally {
      setBusy(null);
    }
  };

  const publish = async () => {
    setBusy("publish");
    setError(null);
    try {
      const response = await publishCalendarVersion(selection);
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível publicar esta versão."));
      setConfirming(false);
      setSuccess("Versão publicada e preservada no histórico.");
      await loadHistory();
    } catch (cause: unknown) {
      setError(errorMessage(cause, "Não foi possível publicar esta versão."));
    } finally {
      setBusy(null);
    }
  };

  const downloadPublication = async (item: CalendarPublication) => {
    setBusy("download");
    setError(null);
    try {
      const response = await requestCalendarPublicationDownload(item.download_url);
      if (!response.ok) throw new Error(await readApiError(response, "Não foi possível baixar a publicação."));
      const result = await downloadResponse(response, `calendario-${item.id}.pdf`);
      const anchor = document.createElement("a");
      anchor.href = result.url;
      anchor.download = result.filename;
      anchor.click();
      URL.revokeObjectURL(result.url);
    } catch (cause: unknown) {
      setError(errorMessage(cause, "Não foi possível baixar a publicação."));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/45 p-0 backdrop-blur-sm sm:items-center sm:p-5">
      <section ref={dialog} role="dialog" aria-modal="true" aria-labelledby="calendar-export-title" aria-busy={Boolean(busy)} tabIndex={-1} className="max-h-[94vh] w-full overflow-y-auto bg-white p-5 shadow-2xl sm:max-w-3xl sm:rounded-3xl sm:p-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-blue-700">Calendário Institucional</p>
            <h2 id="calendar-export-title" className="mt-1 text-2xl font-black text-slate-950">Exportar e publicar</h2>
            <p className="mt-2 text-sm text-slate-600">Gere um preview antes de criar uma versão imutável no histórico.</p>
          </div>
          <button type="button" onClick={onClose} disabled={Boolean(busy)} aria-label="Fechar exportação" className="calendar-control"><X size={18} /></button>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <fieldset>
            <legend className="text-sm font-black text-slate-900">Escopo</legend>
            <div className="mt-3 grid gap-2">
              {(["PUBLICO", "INTERNO"] as const).map((value) => <label key={value} className="flex cursor-pointer gap-3 rounded-2xl border border-slate-200 p-3 text-sm"><input type="radio" name="calendar-export-scope" value={value} checked={scope === value} onChange={() => updateScope(value)} /><span><strong>{value === "PUBLICO" ? "Público" : "Interno"}</strong><span className="mt-0.5 block text-slate-500">{value === "PUBLICO" ? "Somente agenda publicável externamente." : "Inclui Preparatórias e Avaliação, sem dados pessoais."}</span></span></label>)}
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-sm font-black text-slate-900">Formato</legend>
            <div className="mt-3 grid gap-2">
              {(["MONTH", "YEAR_MONTHLY", "YEAR_SUMMARY"] as const).map((value) => {
                const disabled = value === "MONTH" && view === "year";
                return <label key={value} className={`flex gap-3 rounded-2xl border border-slate-200 p-3 text-sm ${disabled ? "cursor-not-allowed bg-slate-50 text-slate-400" : "cursor-pointer"}`}><input type="radio" name="calendar-export-format" value={value} checked={format === value} disabled={disabled} onChange={() => updateFormat(value)} /><span><strong>{FORMAT_LABELS[value]}</strong>{value === "MONTH" ? <span className="mt-0.5 block text-slate-500">{disabled ? "Abra um mês para usar esta opção." : `${MONTH_LABELS[month]} de ${year}.`}</span> : null}</span></label>;
              })}
            </div>
          </fieldset>
        </div>

        {error ? <p className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">{error}</p> : null}
        {success ? <p className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800" role="status">{success}</p> : null}

        <div className="mt-6 flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <button type="button" onClick={() => void generatePreview()} disabled={Boolean(busy)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">{busy === "preview" ? <Loader2 className="animate-spin" size={17} /> : <ExternalLink size={17} />}Gerar preview</button>
          {preview ? <div className="flex flex-col gap-2 sm:flex-row"><a href={preview.url} download={preview.filename} target="_blank" rel="noreferrer" className="calendar-control justify-center gap-2 px-3 text-sm font-bold"><Download size={16} />Abrir/baixar preview</a><button type="button" onClick={() => setConfirming(true)} disabled={Boolean(busy)} className="calendar-control justify-center px-3 text-sm font-bold">Publicar versão</button></div> : null}
        </div>

        {confirming ? <PublicationConfirmation selection={selection} busy={busy === "publish"} onCancel={() => setConfirming(false)} onPublish={() => void publish()} /> : null}

        <section className="mt-7 border-t border-slate-100 pt-5" aria-labelledby="calendar-publication-history">
          <h3 id="calendar-publication-history" className="flex items-center gap-2 font-black text-slate-950"><FileClock size={18} />Histórico de publicações</h3>
          {historyLoading ? <p className="mt-3 text-sm text-slate-500" role="status">Carregando histórico...</p> : null}
          {!historyLoading && history.length === 0 ? <p className="mt-3 text-sm text-slate-500">Nenhuma versão publicada.</p> : null}
          <ul className="mt-3 grid gap-2">
            {history.map((item) => <li key={item.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-bold text-slate-900">{item.escopo === "PUBLICO" ? "Público" : "Interno"} · {formatPublication(item)}</p><p className="mt-1 text-xs text-slate-500">{new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(item.publicado_em))} · {item.publicado_por} · SHA-256 {item.hash_abreviado}</p></div><button type="button" onClick={() => void downloadPublication(item)} disabled={Boolean(busy)} className="calendar-control justify-center gap-2 px-3 text-sm font-bold"><Download size={15} />Baixar</button></li>)}
          </ul>
        </section>
      </section>
    </div>
  );
}
