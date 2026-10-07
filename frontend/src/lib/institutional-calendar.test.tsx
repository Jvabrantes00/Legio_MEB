import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AgendaItems } from "../components/EncounterAgendaSection";
import {
  CalendarEncounterDrawer,
  canOfficializeAgenda,
  officializeAgendaFromDrawer,
} from "../components/CalendarEncounterDrawer";
import { CalendarEncounterForm } from "../components/CalendarEncounterForm";
import {
  CalendarExportDialog,
  PublicationConfirmation,
  buildCalendarExportParams,
  publicationSummary,
  publishCalendarVersion,
  requestCalendarPreview,
  requestCalendarPublicationDownload,
  requestCalendarPublicationHistory,
} from "../components/CalendarExportDialog";
import { InstitutionalCalendarHeader } from "../components/InstitutionalCalendarHeader";
import { MonthView, OccurrenceCard, YearView } from "../components/InstitutionalCalendarViews";
import { EncounterCategoryIcon } from "../components/icons/EncounterCategoryIcon";
import {
  buildEncounterAgendaPayload,
  calendarOccurrences,
  dateKey,
  formatDateOnly,
  monthGrid,
  monthInterval,
  parseDateOnly,
  shiftMonth,
  todayParts,
  type CalendarOccurrence,
  type InstitutionalCalendarResponse,
} from "./institutional-calendar";

const occurrence: CalendarOccurrence = {
  id: "DIA_ENCONTRO:1",
  origem_id: 1,
  origem: "DIA_ENCONTRO",
  data: "2027-03-21",
  titulo: "Pré-Escalada",
  subtitulo: "Escalada 2027",
  confirmacao: "PROVISORIA",
  publicavel_externamente: true,
  encontro_id: 7,
  conflito: null,
  encontro_titulo: "Escalada 2027",
  encontro_tipo: "Escalada",
  encontro_status: "em_agendamento",
  pode_editar_calendario: true,
};

describe("datas civis do Calendário", () => {
  it("faz parse e formatação date-only sem deslocamento de timezone", () => {
    expect(parseDateOnly("2027-03-21")).toEqual({ year: 2027, month: 2, day: 21 });
    expect(formatDateOnly("2027-03-21")).toBe("21/03/2027");
    expect(() => parseDateOnly("2027-02-30")).toThrow("Data civil inválida");
  });

  it("constrói grade de segunda a domingo com dias adjacentes", () => {
    const grid = monthGrid(2026, 9, { year: 2026, month: 9, day: 6 });
    expect(grid).toHaveLength(42);
    expect(grid[0].key).toBe("2026-09-28");
    expect(grid[0].inCurrentMonth).toBe(false);
    expect(grid.find((cell) => cell.key === "2026-10-06")?.isToday).toBe(true);
    expect(monthInterval(2026, 9)).toEqual({ inicio: "2026-09-28", fim: "2026-11-08" });
  });

  it("navega corretamente entre anos", () => {
    expect(shiftMonth(2026, 0, -1)).toEqual({ year: 2025, month: 11 });
    expect(shiftMonth(2026, 11, 1)).toEqual({ year: 2027, month: 0 });
    expect(dateKey({ year: 2026, month: 0, day: 3 })).toBe("2026-01-03");
  });

  it("obtém o mês corrente pela data local sem conversão date-only", () => {
    expect(todayParts(new Date(2026, 9, 6, 23, 30))).toEqual({ year: 2026, month: 9, day: 6 });
  });
});

describe("contratos e apresentação do Calendário", () => {
  it("cabeçalho expõe navegação, modos e filtros futuros sem ação falsa", () => {
    const common = { cursor: { year: 2026, month: 9 }, view: "month" as const, filter: "all" as const, onMove: () => {}, onToday: () => {}, onView: () => {}, onFilter: () => {}, onExport: () => {}, onCreate: () => {} };
    const readOnly = renderToStaticMarkup(<InstitutionalCalendarHeader {...common} canManage={false} />);
    const manager = renderToStaticMarkup(<InstitutionalCalendarHeader {...common} canManage />);
    expect(readOnly).toContain("Outubro 2026");
    expect(readOnly).toContain('aria-label="Mês anterior"');
    expect(readOnly).toContain("Hoje");
    expect(readOnly).toContain('aria-pressed="true"');
    expect(readOnly).toMatch(/Eventos<\/button>/);
    expect(readOnly).toMatch(/Outros<\/button>/);
    expect(readOnly).not.toContain("Novo compromisso");
    expect(manager).toContain("Novo compromisso");
    expect(manager).toContain("Exportar");
    const exportButton = manager.match(/<button[^>]*class="calendar-control gap-2[^>]*>[\s\S]*?Exportar<\/button>/)?.[0] ?? "";
    expect(exportButton).not.toContain("disabled");
  });

  it("mapeia as três modalidades finais sem expor o Modelo A", () => {
    const base = { scope: "PUBLICO" as const, year: 2027, month: 2 };
    expect(Object.fromEntries(buildCalendarExportParams({ ...base, format: "MONTH" }))).toEqual({ escopo: "PUBLICO", ano: "2027", periodo: "MES", layout: "MENSAL", mes: "3" });
    expect(Object.fromEntries(buildCalendarExportParams({ ...base, format: "YEAR_MONTHLY" }))).toEqual({ escopo: "PUBLICO", ano: "2027", periodo: "ANO", layout: "MENSAL" });
    expect(Object.fromEntries(buildCalendarExportParams({ ...base, format: "YEAR_SUMMARY" }))).toEqual({ escopo: "PUBLICO", ano: "2027", periodo: "ANO", layout: "ANUAL_RESUMIDO" });
    expect(buildCalendarExportParams({ ...base, format: "YEAR_SUMMARY" }).toString()).not.toContain("modelo");
  });

  it("dialog de exportação é responsivo, acessível e oculta mês na visão anual", () => {
    const monthly = renderToStaticMarkup(<CalendarExportDialog open year={2027} month={2} view="month" canManage onClose={() => {}} />);
    const annual = renderToStaticMarkup(<CalendarExportDialog open year={2027} month={2} view="year" canManage onClose={() => {}} />);
    const readOnly = renderToStaticMarkup(<CalendarExportDialog open year={2027} month={2} view="month" canManage={false} onClose={() => {}} />);
    expect(monthly).toContain('role="dialog"');
    expect(monthly).toContain("Mês selecionado");
    expect(monthly).toContain("Ano completo — páginas mensais");
    expect(monthly).toContain("Ano completo — visão resumida");
    expect(monthly).toContain("Gerar preview");
    expect(monthly).toContain("Histórico de publicações");
    expect(annual).toMatch(/<input(?=[^>]*value="MONTH")(?=[^>]*disabled="")[^>]*>/);
    expect(annual).toContain("Abra um mês para usar esta opção.");
    expect(readOnly).toBe("");
  });

  it("confirma publicação com contexto e aviso de imutabilidade", () => {
    const selection = { scope: "INTERNO" as const, format: "YEAR_SUMMARY" as const, year: 2027, month: 2 };
    const html = renderToStaticMarkup(<PublicationConfirmation selection={selection} busy={false} onCancel={() => {}} onPublish={() => {}} />);
    expect(publicationSummary(selection)).toEqual(["Interno", "Ano 2027", "Formato: Ano completo — visão resumida"]);
    expect(html).toContain("Publicar esta versão do Calendário Institucional?");
    expect(html).toContain("não poderá ser alterada");
    expect(html).toContain("Publicar versão");
  });

  it("preview e publicação usam requests separados", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    const request = async (path: string, init?: RequestInit) => {
      calls.push({ path, init });
      return new Response(null, { status: init?.method === "POST" ? 201 : 200 });
    };
    const selection = { scope: "PUBLICO" as const, format: "YEAR_MONTHLY" as const, year: 2027, month: 2 };
    await requestCalendarPreview(selection, request);
    await publishCalendarVersion(selection, request);
    expect(calls[0].path).toBe("/calendario-institucional/preview-pdf/?escopo=PUBLICO&ano=2027&periodo=ANO&layout=MENSAL");
    expect(calls[0].init).toBeUndefined();
    expect(calls[1]).toEqual({
      path: "/calendario-institucional/publicacoes/",
      init: {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ escopo: "PUBLICO", ano: "2027", periodo: "ANO", layout: "MENSAL" }),
      },
    });
  });

  it("histórico e download usam somente endpoints autenticados do BFF", async () => {
    const calls: string[] = [];
    const request = async (path: string) => {
      calls.push(path);
      return new Response(null, { status: 200 });
    };

    await requestCalendarPublicationHistory(request);
    await requestCalendarPublicationDownload(
      "/calendario-institucional/publicacoes/17/download/",
      request,
    );

    expect(calls).toEqual([
      "/calendario-institucional/publicacoes/",
      "/calendario-institucional/publicacoes/17/download/",
    ]);
  });

  it("achata a Agenda preservando vínculo e capability do Encontro", () => {
    const response: InstitutionalCalendarResponse = {
      periodo: { inicio: "2027-03-01", fim: "2027-03-31" },
      itens: [{
        categoria: "ENCONTRO", encontro_id: 7, titulo: "Escalada 2027", tipo: "Escalada",
        status: "em_agendamento", calendario_id: 1, calendario_versao: 1,
        origem_agenda: "CANONICA", confirmacao: "PROVISORIA", dias: [],
        agenda: [occurrence], pode_editar_calendario: true,
      }],
      conflitos: [],
      capabilities: { pode_visualizar: true, pode_gerir_calendario: true, pode_criar_encontro: true, pode_publicar: true },
    };
    expect(calendarOccurrences(response)[0]).toMatchObject({ encontro_titulo: "Escalada 2027", pode_editar_calendario: true });
  });

  it("monta criação com múltiplos dias, preparatória, complemento e avaliação", () => {
    expect(buildEncounterAgendaPayload({
      encontro: " Escalada 2027 ", tipo: "Escalada", local: " Sede ",
      dias: [{ data: "2027-03-21", rotulo: " Pré-Escalada " }, { data: "2027-03-25", rotulo: "Sexta-feira" }],
      reunioes: [{ data: "2027-03-17", horario: "19:30", local: " Sede ", complemento: " Missa de Entrega " }],
      avaliacaoData: "2027-03-30",
    })).toEqual({
      encontro: "Escalada 2027", tipo: "Escalada", local: "Sede",
      dias: [{ ordem: 1, data: "2027-03-21", rotulo: "Pré-Escalada" }, { ordem: 2, data: "2027-03-25", rotulo: "Sexta-feira" }],
      reunioes: [{ ordem: 1, data: "2027-03-17", horario: "19:30", local: "Sede", complemento: "Missa de Entrega" }],
      avaliacao: { data: "2027-03-30" },
    });
  });

  it("mini-card comunica categoria, rótulo e provisoriedade sem badge confirmado", () => {
    const html = renderToStaticMarkup(<OccurrenceCard item={occurrence} onOpen={() => {}} />);
    expect(html).toContain("Escalada 2027");
    expect(html).toContain("Pré-Escalada");
    expect(html).toContain("Data ainda sujeita a confirmação");
    expect(html).not.toContain("Confirmado");
  });

  it("mini-card apresenta reunião canônica com a nomenclatura Preparatória", () => {
    const meeting = {
      ...occurrence,
      id: "REUNIAO_PREPARATORIA:2",
      origem: "REUNIAO_PREPARATORIA" as const,
      titulo: "2ª Reunião",
      subtitulo: "Missa de Entrega",
      confirmacao: null,
      publicavel_externamente: false,
    };
    const html = renderToStaticMarkup(<OccurrenceCard item={meeting} onOpen={() => {}} />);
    expect(html).toContain("2ª Preparatória");
    expect(html).not.toContain("2ª Reunião");
    expect(html).toContain("Missa de Entrega");
  });

  it("+N mantém compromissos acessíveis e o dia atual não preenche a célula", () => {
    const items = [0, 1, 2].map((index) => ({ ...occurrence, id: `DIA_ENCONTRO:${index}` }));
    const html = renderToStaticMarkup(<MonthView year={2027} month={2} occurrences={items} canManage selectedDate="2027-03-21" onSelectDate={() => {}} onOpenEncounter={() => {}} onCreateAt={() => {}} />);
    expect(html).toContain("+1");
    expect(html).toContain("Criar compromisso em 21/03/2027");
    expect(html).toContain("Dia selecionado");
  });

  it("oculta criação contextual para leitura e mantém a lista mobile", () => {
    const html = renderToStaticMarkup(<MonthView year={2027} month={2} occurrences={[occurrence]} canManage={false} selectedDate="2027-03-21" onSelectDate={() => {}} onOpenEncounter={() => {}} onCreateAt={() => {}} />);
    expect(html).not.toContain("Criar compromisso em");
    expect(html).not.toContain(">Novo<");
    expect(html).toContain("Dia selecionado");
    expect(html).toContain("Escalada 2027");
  });

  it("visão anual contém 12 meses, indicadores e acesso ao mês", () => {
    const html = renderToStaticMarkup(<YearView year={2027} occurrences={[occurrence]} current={{ year: 2027, month: 2 }} onOpenMonth={() => {}} />);
    expect((html.match(/aria-label="Abrir /g) ?? [])).toHaveLength(12);
    expect(html).toContain("Abrir Março de 2027, 1 compromissos");
    expect(html).toContain("ring-blue-100");
  });

  it("Agenda agrupa dias, preparação e pós-Encontro sem dados operacionais", () => {
    const items = [
      occurrence,
      { ...occurrence, id: "REUNIAO_PREPARATORIA:2", origem: "REUNIAO_PREPARATORIA" as const, titulo: "3ª Reunião", subtitulo: "Missa de Entrega", publicavel_externamente: false },
      { ...occurrence, id: "AVALIACAO:3", origem: "AVALIACAO" as const, titulo: "Avaliação", subtitulo: null, publicavel_externamente: false },
    ];
    const html = renderToStaticMarkup(<AgendaItems items={items} />);
    expect(html).toMatch(/Dias do Encontro.*Preparação.*Pós-Encontro/);
    expect(html).toContain("3ª Preparatória");
    expect(html).not.toContain("3ª Reunião");
    expect(html).toContain("Missa de Entrega");
    expect(html).not.toContain("Escalada 2027");
    expect(html).not.toMatch(/presença|participante|equipe/i);
  });

  it("ordena preparatórias pela data canônica, não pelo número do rótulo", () => {
    const items = [
      { ...occurrence, id: "REUNIAO_PREPARATORIA:2", origem: "REUNIAO_PREPARATORIA" as const, data: "2027-10-07", titulo: "2ª Reunião", subtitulo: null, publicavel_externamente: false },
      { ...occurrence, id: "REUNIAO_PREPARATORIA:1", origem: "REUNIAO_PREPARATORIA" as const, data: "2027-10-05", titulo: "1ª Reunião", subtitulo: null, publicavel_externamente: false },
      { ...occurrence, id: "REUNIAO_PREPARATORIA:3", origem: "REUNIAO_PREPARATORIA" as const, data: "2027-10-06", titulo: "3ª Reunião", subtitulo: null, publicavel_externamente: false },
    ];
    const html = renderToStaticMarkup(<AgendaItems items={items} />);
    expect(html.indexOf("1ª Preparatória")).toBeLessThan(html.indexOf("3ª Preparatória"));
    expect(html.indexOf("3ª Preparatória")).toBeLessThan(html.indexOf("2ª Preparatória"));
  });

  it("drawer mantém detalhe enxuto, link canônico e edição somente para gestor", () => {
    const encounter: InstitutionalCalendarResponse["itens"][number] = {
      categoria: "ENCONTRO", encontro_id: 7, titulo: "Escalada 2027", tipo: "Escalada",
      status: "em_agendamento", calendario_id: 1, calendario_versao: 1,
      origem_agenda: "CANONICA", confirmacao: "PROVISORIA", dias: [], agenda: [occurrence],
      pode_editar_calendario: true,
    };
    const readOnly = renderToStaticMarkup(<CalendarEncounterDrawer encounter={encounter} canManage={false} onClose={() => {}} onChanged={() => {}} />);
    const manager = renderToStaticMarkup(<CalendarEncounterDrawer encounter={encounter} canManage onClose={() => {}} onChanged={() => {}} />);
    expect(readOnly).toContain('role="dialog"');
    expect(readOnly).toContain('href="/encontros/7"');
    expect(readOnly).not.toContain("Oficializar agenda");
    expect(readOnly).not.toContain("Editar calendário");
    expect(manager).toContain("Oficializar agenda");
    expect(manager).toContain("Editar calendário");
    expect(manager).toContain("Abrir Encontro completo");
    expect(canOfficializeAgenda(encounter, true)).toBe(true);
  });

  it("drawer não oferece oficialização para agenda já oficial", () => {
    const encounter: InstitutionalCalendarResponse["itens"][number] = {
      categoria: "ENCONTRO", encontro_id: 7, titulo: "Escalada 2027", tipo: "Escalada",
      status: "agendado", calendario_id: 1, calendario_versao: 1,
      origem_agenda: "CANONICA", confirmacao: "OFICIAL", dias: [], agenda: [occurrence],
      pode_editar_calendario: true,
    };
    const html = renderToStaticMarkup(<CalendarEncounterDrawer encounter={encounter} canManage onClose={() => {}} onChanged={() => {}} />);
    expect(html).not.toContain("Oficializar agenda");
    expect(html).toContain("Editar calendário");
    expect(html).toContain("Abrir Encontro completo");
    expect(canOfficializeAgenda(encounter, true)).toBe(false);
  });

  it("oficialização direta usa comando canônico e atualiza calendário e Agenda", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    let calendarReloads = 0;
    let agendaReloads = 0;
    const warnings = await officializeAgendaFromDrawer({
      encounterId: 7,
      onChanged: () => { calendarReloads += 1; },
      reloadAgenda: async () => { agendaReloads += 1; },
      request: async (path, init) => {
        calls.push({ path, init });
        return new Response(JSON.stringify({ avisos_conflito: [{ data: "2027-03-21" }] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      },
    });
    expect(calls).toEqual([{
      path: "/calendario-institucional/encontros/7/oficializar/",
      init: { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" },
    }]);
    expect(calendarReloads).toBe(1);
    expect(agendaReloads).toBe(1);
    expect(warnings).toBe(1);
  });

  it("formulário único aceita data contextual e toda a Agenda inicial", () => {
    const html = renderToStaticMarkup(<CalendarEncounterForm open initialDate="2027-03-21" onClose={() => {}} onCreated={() => {}} />);
    expect(html).toContain("Encontro com Agenda completa");
    expect(html).toContain('value="2027-03-21"');
    expect(html).toContain('value="Pré-Escalada"');
    expect(html).toContain("Adicionar data");
    expect(html).toContain("Adicionar preparatória");
    expect(html).toContain("Avaliação opcional");
  });

  it("SVG personalizado possui título acessível quando informativo", () => {
    const html = renderToStaticMarkup(<EncounterCategoryIcon label="Categoria Encontro" />);
    expect(html).toContain("<svg");
    expect(html).toContain("<title>Categoria Encontro</title>");
  });
});
