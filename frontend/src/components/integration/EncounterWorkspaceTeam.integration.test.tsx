// @vitest-environment jsdom
import { act, cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { siaFetch } from "../../lib/sia-api";
import { EncounterTeamPanel } from "../encounter-team/EncounterTeamPanel";
import { EncounterTeamSetup } from "../encounter-team/EncounterTeamSetup";
import { EncounterWorkspace, type EncounterWorkspaceTab } from "../EncounterWorkspace";
const auth = vi.hoisted(() => ({ active: false, roles: ["Suporte"] }));
vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
vi.mock("../SiaSessionProvider", () => ({ useSiaSession: () => ({ session: auth.active ? { id: 1, username: "suporte", roles: auth.roles, superuser: false } : null }) }));
vi.mock("../EncounterAgendaSection", () => ({ EncounterAgendaSection: () => null }));
const caps = { consultar_resumo: true, consultar_encontristas: false, consultar_contato: false, acessar_pre_encontro: false, acessar_equipes: true, acessar_formacao: false, acessar_agenda: false, consultar_inscricoes: false, configurar_inscricoes: false };
const summary = { encontro: { id: 37, nome: "Encontro Exemplo", tipo: "ESCALADA", local: "Local fictício" }, lifecycle: "EM_PREPARACAO", agenda: { configurada: false, oficializada: false, quantidade_itens: 0, proximo_item: null, datas_principais: [], pre_encontro_data: null }, encontristas: { inscricoes_recebidas: 0, pendentes: 0, confirmados: 0, total_funil: 0, por_situacao: { INSCRITO: 0, CANCELADO: 0, AGUARDANDO_DECISAO: 0, APTO: 0, NAO_APTO: 0, CONFIRMADO: 0 } }, pre_encontro: { configurado: false, data: null, capacidade: null, quantidade_checkins: 0, quantidade_aptos: 0, quantidade_aguardando_decisao: 0 }, equipes: { modelo_equipes: "CANONICO", quantidade_equipes: 0, quantidade_funcoes: 0, vagas_estruturais: null, vagas_preenchidas: 0 }, formacao: { total_sessoes: 0, planejadas: 0, realizadas: 0, canceladas: 0 }, alertas: [] };
function Harness() { const [tab, setTab] = useState<EncounterWorkspaceTab>("visao-geral"); return <EncounterWorkspace encontroId="37" activeTab={tab} onTabChange={setTab} renderTeam={(capabilities, equipes, resumoErro) => <EncounterTeamPanel encontroId={37} capabilities={capabilities} equipes={equipes} resumoErro={resumoErro} />} />; }
beforeEach(() => { auth.active = false; auth.roles = ["Suporte"]; vi.mocked(siaFetch).mockReset(); });
afterEach(cleanup);
it("injeta a consulta somente ao abrir a aba de equipe", async () => {
  vi.mocked(siaFetch).mockImplementation(async (path) => {
    const url = String(path);
    const body = url === "/encontros/37/workspace/capabilities/" ? caps : url === "/encontros/37/workspace/" ? summary : url === "/encontros/37/workspace/equipes/" ? [] : null;
    if (body === null) throw new Error(`URL inesperada: ${url}`);
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  const user = userEvent.setup(); render(<Harness />);
  await screen.findByRole("heading", { name: "Encontro Exemplo" });
  expect(vi.mocked(siaFetch).mock.calls.some(([path]) => String(path) === "/encontros/37/workspace/equipes/")).toBe(false);
  await user.click(screen.getByRole("tab", { name: "Equipe" }));
  expect(await screen.findByText("Equipes ainda não preparadas")).toBeTruthy();
  expect(vi.mocked(siaFetch).mock.calls.some(([path]) => String(path) === "/encontros/37/workspace/equipes/")).toBe(true);
});

it("integra ativação, preparação, avisos, bloqueio e duplicidade", async () => {
  auth.active = true;
  const team = { id: 1, encontro_id: 37, codigo: "A", nome: "Apoio", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [{ id: 3, codigo: "M", nome: "Membro", ordem: 0, quantidade_estrutural: 3, concede_registro_presenca: false, trabalhos: [] }] };
  const people = [{ id: 1, pessoa_id: 11, nome: "Pessoa Aviso", grupo: "A", cpf: "dado-sensivel" }, { id: 2, pessoa_id: 12, nome: "Pessoa Bloqueio", grupo: "B" }];
  let prepared = false; let created = false;
  const list = () => ({ count: created ? 4 : 0, next: null, previous: null, results: created ? ["convidado", "confirmado", "recusado", "sem_resposta"].map((status, i) => ({ id: i + 1, pessoa_id: i ? 20 + i : 11, pessoa_nome: i ? `Pessoa ${i}` : "Pessoa Aviso", encontro_id: 37, finalidade: "trabalhar", status, role_trabalho_proposta_id: 3, trabalho_id: null, trabalho_status: null, criado_em: "2026-01-01" })) : [] });
  const assessment = (category: string) => ({ avaliacao: { resultado: category, motivos: [{ codigo: category === "AVISO" ? "ALPINISTA_INATIVO" : "AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA", categoria: category, mensagem: category === "AVISO" ? "Verifique atividade" : "Caminho incompleto" }] } });
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path), post = init?.method === "POST";
    if (url.endsWith("modelo-equipes/")) return Response.json(post ? { modelo_equipes: "CANONICO" } : { elegivel: true, motivos: [], contagens: { vinculos_legados_equipe: 0, vinculos_tipo_indefinido: 0, equipes_canonicas: 0, trabalhos_canonicos: 0 } });
    if (url.endsWith("preparar-equipes/")) { prepared = true; return Response.json([team]); }
    if (url.endsWith("workspace/equipes/")) return Response.json(prepared ? [team] : []);
    if (url.startsWith("/alpinistas/seletor-trabalho/")) return Response.json({ count: 2, next: null, previous: null, results: people });
    if (url.startsWith("/convites-encontros/?")) return Response.json(list());
    if (url === "/convites-encontros/" && post) {
      const payload = JSON.parse(String(init?.body));
      if (payload.pessoa_id === 12) return Response.json(assessment("BLOQUEIO"), { status: 400 });
      if (created) return Response.json({ non_field_errors: ["Os campos pessoa_id, encontro_id, finalidade devem criar um set único."] }, { status: 400 });
      if (!payload.confirmar_avisos) return Response.json(assessment("AVISO"), { status: 400 });
      created = true; return Response.json({ id: 1 }, { status: 201 });
    }
    throw new Error(`URL inesperada: ${url}`);
  });
  function Flow() {
    const [modelo, setModelo] = useState<"LEGADO" | "CANONICO">("LEGADO");
    return <>{modelo === "LEGADO" ? <EncounterTeamSetup encontroId={37} modelo="LEGADO" canActivate canPrepare onChange={() => setModelo("CANONICO")} /> : <EncounterTeamPanel encontroId={37} capabilities={caps} equipes={{ modelo_equipes: modelo, quantidade_equipes: 0 }} />}</>;
  }
  const user = userEvent.setup(); render(<Flow />);
  await screen.findByText("Encontro apto à ativação.");
  await user.type(screen.getByLabelText("Justificativa"), "Motivo");
  await user.click(screen.getByLabelText("Confirmo a ativação do modelo canônico"));
  await user.click(screen.getByRole("button", { name: "Ativar modelo canônico" }));
  await user.click(await screen.findByRole("button", { name: "Preparar equipes" }));
  await screen.findByText("Equipes preparadas.");
  await screen.findByRole("option", { name: /Pessoa Aviso/ });
  await screen.findByRole("option", { name: /Apoio — Membro/ });
  await user.selectOptions(screen.getByLabelText("Alpinista"), "11");
  await user.selectOptions(screen.getByLabelText("Função"), "3");
  await user.click(screen.getByRole("button", { name: "Registrar convite" }));
  await screen.findByText(/Verifique atividade/);
  await user.click(screen.getByLabelText("Confirmo os avisos e registrar convite"));
  await user.click(screen.getByRole("button", { name: "Registrar convite com confirmação" }));
  await screen.findByText(/Convite registrado no SIA/);
  await screen.findByText(/Pendente \(aguardando resposta\)/);
  expect(screen.getByText(/Pessoa 1 — Confirmado/)).toBeTruthy(); expect(screen.getByText(/Recusado/)).toBeTruthy(); expect(screen.getByText(/Sem resposta/)).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Alpinista"), "12");
  await user.click(screen.getByRole("button", { name: "Registrar convite" }));
  await screen.findByText(/Caminho incompleto/);
  expect(screen.queryByLabelText("Confirmo os avisos e registrar convite")).toBeNull();
  await user.selectOptions(screen.getByLabelText("Alpinista"), "11");
  await user.click(screen.getByRole("button", { name: "Registrar convite" }));
  await screen.findByText("Já existe um convite de trabalho para esta pessoa neste Encontro.");
  expect(document.body.textContent).not.toContain("dado-sensivel");
  expect(document.body.textContent).not.toMatch(/convite enviado|notificação enviada/i);
});
it.each([0, 1])("trata modelo legado com %i registros", async (count) => {
  const legacySummary = { ...summary, equipes: { ...summary.equipes, modelo_equipes: "LEGADO", quantidade_equipes: count } };
  const team = { id: 1, encontro_id: 37, codigo: "A", nome: "Equipe preexistente", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [] };
  vi.mocked(siaFetch).mockImplementation(async (path) => {
    const url = String(path);
    const body = url === "/encontros/37/workspace/capabilities/" ? caps : url === "/encontros/37/workspace/" ? legacySummary : url === "/encontros/37/workspace/equipes/" ? [team] : null;
    if (body === null) throw new Error("URL inesperada");
    return new Response(JSON.stringify(body), { status: 200 });
  });
  const user = userEvent.setup(); render(<Harness />);
  await screen.findByRole("heading", { name: "Encontro Exemplo" });
  expect(vi.mocked(siaFetch).mock.calls.some(([path]) => String(path) === "/encontros/37/workspace/equipes/")).toBe(false);
  await user.click(screen.getByRole("tab", { name: "Equipe" }));
  expect(screen.getByText(/modelo canônico de Equipes não está ativo/)).toBeTruthy();
  if (count) {
    expect(await screen.findByText("Equipe preexistente")).toBeTruthy();
    expect(screen.getByText("Canônicos preexistentes — não ativos no modelo LEGADO")).toBeTruthy();
  }
  expect(vi.mocked(siaFetch).mock.calls.some(([path]) => String(path) === "/encontros/37/workspace/equipes/")).toBe(Boolean(count));
  expect(screen.queryByText("Equipes ainda não preparadas")).toBeNull();
});

it("sincroniza as duas fontes após alocar e permite tentar atualização falha", async () => {
  auth.active = true;
  const role = { id: 3, codigo: "M", nome: "Membro", ordem: 0, quantidade_estrutural: 2, concede_registro_presenca: false, trabalhos: [] };
  const team = { id: 1, encontro_id: 37, codigo: "A", nome: "Apoio", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [role] };
  const invite = { id: 1, pessoa_id: 2, pessoa_nome: "Pessoa", encontro_id: 37, finalidade: "trabalhar", status: "confirmado", role_trabalho_proposta_id: null, trabalho_id: 7, trabalho_status: "aguardando_alocacao", criado_em: "2026" };
  let teamsCount = 0, invitesCount = 0, failed = false;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path);
    if (init?.method === "POST") { failed = true; return Response.json({}); }
    if (url.endsWith("workspace/equipes/")) { teamsCount++; if (failed) { failed = false; return Response.json({ detail: "Falhou" }, { status: 500 }); } return Response.json([team]); }
    if (url.startsWith("/convites-encontros/?")) { invitesCount++; return Response.json({ count: 1, next: null, previous: null, results: [invite] }); }
    if (url.startsWith("/alpinistas/")) return Response.json({ count: 0, next: null, previous: null, results: [] });
    throw new Error(url);
  });
  const user = userEvent.setup(); render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={{ modelo_equipes: "CANONICO", quantidade_equipes: 1 }} />);
  const allocate = await screen.findByRole("button", { name: "Alocar" }); await user.click(allocate);
  await user.selectOptions(screen.getByRole("dialog").querySelector("select")!, "3");
  expect(vi.mocked(siaFetch).mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "Confirmar" }));
  await screen.findByText(/dados podem estar desatualizados/); expect(teamsCount).toBe(2); expect(invitesCount).toBe(2);
  expect((screen.getByRole("button", { name: "Alocar" }) as HTMLButtonElement).disabled).toBe(true);
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await screen.findByText("Apoio");
  await vi.waitFor(() => expect((screen.getByRole("button", { name: "Alocar" }) as HTMLButtonElement).disabled).toBe(false));
  expect(teamsCount).toBe(3); expect(invitesCount).toBe(3);
});

it.each(["Realocar", "Desalocar", "Iniciar trabalho"])("recarrega equipes e convites após %s", async (action) => {
  auth.active = true;
  const role = (id: number, nome: string, trabalhos: object[]) => ({ id, codigo: `R${id}`, nome, ordem: id, quantidade_estrutural: 3, concede_registro_presenca: false, trabalhos });
  const team = { id: 1, encontro_id: 37, codigo: "A", nome: "Apoio", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [role(3, "Origem", [{ id: 7, pessoa_id: 2, pessoa_nome: "Pessoa", status: "alocado" }]), role(4, "Destino", [])] };
  const invite = { id: 1, pessoa_id: 9, pessoa_nome: "Outra", encontro_id: 37, finalidade: "trabalhar", status: "confirmado", role_trabalho_proposta_id: null, trabalho_id: null, trabalho_status: null, criado_em: "2026" };
  let teamsCount = 0, invitesCount = 0;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path); if (init?.method === "POST") return Response.json({});
    if (url.endsWith("workspace/equipes/")) { teamsCount++; return Response.json([team]); }
    if (url.startsWith("/convites-encontros/?")) { invitesCount++; return Response.json({ count: 1, next: null, previous: null, results: [invite] }); }
    if (url.startsWith("/alpinistas/")) return Response.json({ count: 0, next: null, previous: null, results: [] }); throw new Error(url);
  });
  const user = userEvent.setup(); render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={{ modelo_equipes: "CANONICO", quantidade_equipes: 1 }} />);
  const button = await screen.findByRole("button", { name: action }); await vi.waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
  await user.click(button);
  if (action !== "Iniciar trabalho") { if (action === "Realocar") await user.selectOptions(screen.getByRole("dialog").querySelector("select")!, "4"); await user.click(screen.getByRole("button", { name: "Confirmar" })); }
  await vi.waitFor(() => { expect(teamsCount).toBe(2); expect(invitesCount).toBe(2); });
});

it("descarta diálogo ao trocar Encontro ou revogar gestão", async () => {
  auth.active = true;
  const role = { id: 3, codigo: "M", nome: "Membro", ordem: 0, quantidade_estrutural: 2, concede_registro_presenca: false, trabalhos: [{ id: 7, pessoa_id: 2, pessoa_nome: "Pessoa", status: "alocado" }] };
  const team = { id: 1, encontro_id: 37, codigo: "A", nome: "Apoio", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [role] };
  vi.mocked(siaFetch).mockImplementation(async (path) => String(path).endsWith("workspace/equipes/") ? Response.json([team]) : Response.json({ count: 0, next: null, previous: null, results: [] }));
  const user = userEvent.setup(); const view = render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={{ modelo_equipes: "CANONICO", quantidade_equipes: 1 }} />);
  const open = async () => { const button = await screen.findByRole("button", { name: "Desalocar" }); await vi.waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false)); await user.click(button); expect(screen.getByRole("dialog")).toBeTruthy(); };
  await open(); view.rerender(<EncounterTeamPanel encontroId={38} capabilities={caps} equipes={{ modelo_equipes: "CANONICO", quantidade_equipes: 1 }} />); expect(screen.queryByRole("dialog")).toBeNull();
  await open(); auth.active = false; view.rerender(<EncounterTeamPanel encontroId={38} capabilities={caps} equipes={{ modelo_equipes: "CANONICO", quantidade_equipes: 1 }} />); expect(screen.queryByRole("dialog")).toBeNull(); expect(screen.queryByRole("button", { name: "Desalocar" })).toBeNull();
  expect(vi.mocked(siaFetch).mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
});

it("mantém dados e ações bloqueadas até as duas respostas da atualização", async () => {
  auth.active = true;
  const team = { id: 1, encontro_id: 37, codigo: "A", nome: "Apoio", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [{ id: 3, codigo: "M", nome: "Membro", ordem: 0, quantidade_estrutural: 2, concede_registro_presenca: false, trabalhos: [{ id: 7, pessoa_id: 2, pessoa_nome: "Pessoa", status: "alocado" }] }] };
  const listing = { count: 0, next: null, previous: null, results: [] }; let resolveTeams!: (r: Response) => void; let resolveInvites!: (r: Response) => void; let refresh = false;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path); if (init?.method === "POST") { refresh = true; return Response.json({}); }
    if (url.endsWith("workspace/equipes/")) return refresh ? new Promise<Response>((resolve) => { resolveTeams = resolve; }) : Response.json([team]);
    if (url.startsWith("/convites-encontros/?")) return refresh ? new Promise<Response>((resolve) => { resolveInvites = resolve; }) : Response.json(listing);
    return Response.json(listing);
  });
  const user = userEvent.setup(); render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={{ modelo_equipes: "CANONICO", quantidade_equipes: 1 }} />);
  const button = await screen.findByRole("button", { name: "Desalocar" }); await vi.waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
  await user.click(button); await user.click(screen.getByRole("button", { name: "Confirmar" })); await screen.findByText("Atualizando...");
  expect(screen.getByText("Pessoa — alocado")).toBeTruthy(); expect((screen.getByRole("button", { name: "Desalocar" }) as HTMLButtonElement).disabled).toBe(true);
  resolveInvites(Response.json(listing)); await vi.waitFor(() => expect(resolveTeams).toBeDefined());
  expect((screen.getByRole("button", { name: "Desalocar" }) as HTMLButtonElement).disabled).toBe(true);
  resolveTeams(Response.json([team])); await vi.waitFor(() => expect((screen.getByRole("button", { name: "Desalocar" }) as HTMLButtonElement).disabled).toBe(false));
});

it("Coordenação Geral com acesso contextual vê composição sem controles de escrita", async () => {
  auth.active = true; auth.roles = ["Coordenação Geral"];
  const team = { id: 1, encontro_id: 37, codigo: "A", nome: "Apoio", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [{ id: 3, codigo: "M", nome: "Membro", ordem: 0, quantidade_estrutural: 2, concede_registro_presenca: false, trabalhos: [{ id: 7, pessoa_id: 2, pessoa_nome: "Pessoa", status: "alocado" }] }] };
  vi.mocked(siaFetch).mockResolvedValue(Response.json([team]));
  render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={{ modelo_equipes: "CANONICO", quantidade_equipes: 1 }} />);
  await screen.findByText("Pessoa — alocado");
  for (const label of ["Alocar", "Realocar", "Desalocar", "Iniciar trabalho", "Preparar equipes"]) expect(screen.queryByRole("button", { name: label })).toBeNull();
});

function deferredResponse() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((done) => { resolve = done; });
  return { promise, resolve };
}
const r1Team = (name: string, pessoa: string, quantity = 3) => ({ id: 1, encontro_id: 37, codigo: "A", nome: name, ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: null, capacidade: { resultado: "ELEGIVEL", motivos: [] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [{ id: 3, codigo: "M", nome: "Membro", ordem: 0, quantidade_estrutural: quantity, concede_registro_presenca: false, trabalhos: [{ id: 7, pessoa_id: 2, pessoa_nome: pessoa, status: "alocado" }] }] });
const r1Invite = (name: string) => ({ id: 10, pessoa_id: 11, pessoa_nome: name, encontro_id: 37, finalidade: "trabalhar", status: "confirmado", role_trabalho_proposta_id: null, trabalho_id: 12, trabalho_status: "aguardando_alocacao", criado_em: "2026" });
const r1Page = (name: string) => ({ count: 1, next: null, previous: null, results: [r1Invite(name)] });
const r1Summary = { modelo_equipes: "CANONICO" as const, quantidade_equipes: 1 };
const r1Posts = () => vi.mocked(siaFetch).mock.calls.filter(([, init]) => init?.method === "POST");
async function r1Desalocar(user: ReturnType<typeof userEvent.setup>) {
  const button = await screen.findByRole("button", { name: "Desalocar" });
  await vi.waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
  await user.click(button); await user.click(screen.getByRole("button", { name: "Confirmar" }));
}

it("descarta respostas antigas após retry concorrente e mantém bloqueio enquanto a recarga válida está pendente", async () => {
  auth.active = true; const oldTeams = deferredResponse(), newTeams = deferredResponse(), newInvites = deferredResponse();
  let teamCalls = 0, inviteCalls = 0;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path); if (init?.method === "POST") return Response.json({});
    if (url.endsWith("workspace/equipes/")) { teamCalls++; return teamCalls === 1 ? Response.json([r1Team("Inicial", "Pessoa inicial")]) : teamCalls === 2 ? oldTeams.promise : newTeams.promise; }
    if (url.startsWith("/convites-encontros/?")) { inviteCalls++; return inviteCalls === 1 ? Response.json(r1Page("Convite inicial")) : inviteCalls === 2 ? Response.json({ detail: "Lista indisponível" }, { status: 500 }) : newInvites.promise; }
    return Response.json({ count: 0, next: null, previous: null, results: [] });
  });
  const user = userEvent.setup(); render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={r1Summary} />);
  await r1Desalocar(user); await screen.findByText(/dados podem estar desatualizados/);
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await vi.waitFor(() => { expect(teamCalls).toBe(3); expect(inviteCalls).toBe(3); });
  await act(async () => newTeams.resolve(Response.json([r1Team("Atual", "Pessoa atual", 4)])));
  expect(await screen.findByText("Pessoa atual — alocado")).toBeTruthy();
  expect((screen.getByRole("button", { name: "Desalocar" }) as HTMLButtonElement).disabled).toBe(true);
  await act(async () => newInvites.resolve(Response.json(r1Page("Convite atual"))));
  await screen.findByText("Convite atual — Confirmado");
  await vi.waitFor(() => expect((screen.getByRole("button", { name: "Alocar" }) as HTMLButtonElement).disabled).toBe(false));
  await act(async () => oldTeams.resolve(Response.json([r1Team("Antiga", "Pessoa antiga", 99)])));
  expect(screen.queryByText("Pessoa antiga — alocado")).toBeNull(); expect(screen.getByText("Pessoa atual — alocado")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Alocar" }));
  expect(within(screen.getByRole("dialog")).getByRole("option", { name: /Atual — Membro.*ocupação: 1.*4/ })).toBeTruthy();
  expect(screen.getByText("Convite atual — Confirmado")).toBeTruthy();
});

it("recupera falha de convites após equipes atualizadas sem liberar ações antes do retry", async () => {
  auth.active = true; let teamCalls = 0, inviteCalls = 0;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path); if (init?.method === "POST") return Response.json({});
    if (url.endsWith("workspace/equipes/")) { teamCalls++; return Response.json([r1Team(teamCalls === 1 ? "Inicial" : "Atual", "Pessoa", 4)]); }
    if (url.startsWith("/convites-encontros/?")) { inviteCalls++; return inviteCalls === 2 ? Response.json({ detail: "Falha nos convites" }, { status: 500 }) : Response.json(r1Page(inviteCalls === 1 ? "Antigo" : "Recuperado")); }
    return Response.json({ count: 0, next: null, previous: null, results: [] });
  });
  const user = userEvent.setup(); render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={r1Summary} />);
  await r1Desalocar(user); await screen.findByText(/dados podem estar desatualizados/); expect(await screen.findByText("Atual")).toBeTruthy();
  expect(screen.getByText("Falha nos convites")).toBeTruthy(); expect((screen.getByRole("button", { name: "Alocar" }) as HTMLButtonElement).disabled).toBe(true);
  await user.click(screen.getByRole("button", { name: "Tentar novamente" })); await screen.findByText("Recuperado — Confirmado");
  await vi.waitFor(() => expect((screen.getByRole("button", { name: "Alocar" }) as HTMLButtonElement).disabled).toBe(false));
  expect(teamCalls).toBe(3); expect(inviteCalls).toBe(3);
});

it("ignora lista antiga tardia após nova recarga e não libera controles antes das duas fontes", async () => {
  auth.active = true; const oldInvites = deferredResponse(), newInvites = deferredResponse(), newTeams = deferredResponse(); let teams = 0, invites = 0;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path); if (init?.method === "POST") return Response.json({});
    if (url.endsWith("workspace/equipes/")) { teams++; return teams === 1 ? Response.json([r1Team("Inicial", "Pessoa inicial")]) : teams === 2 ? Response.json({ detail: "Erro equipes" }, { status: 500 }) : newTeams.promise; }
    if (url.startsWith("/convites-encontros/?")) { invites++; return invites === 1 ? Response.json(r1Page("Inicial")) : invites === 2 ? oldInvites.promise : newInvites.promise; }
    return Response.json({ count: 0, next: null, previous: null, results: [] });
  });
  const user = userEvent.setup(); render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={r1Summary} />);
  await r1Desalocar(user); await screen.findByText(/dados podem estar desatualizados/); await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await vi.waitFor(() => { expect(teams).toBe(3); expect(invites).toBe(3); });
  await act(async () => newInvites.resolve(Response.json(r1Page("Atual")))); expect(await screen.findByText("Atual — Confirmado")).toBeTruthy();
  await act(async () => oldInvites.resolve(Response.json(r1Page("Antigo tardio"))));
  expect(screen.queryByText("Antigo tardio — Confirmado")).toBeNull(); expect(screen.getByText("Atual — Confirmado")).toBeTruthy();
  expect((screen.getByRole("button", { name: "Alocar" }) as HTMLButtonElement).disabled).toBe(true);
  await act(async () => newTeams.resolve(Response.json([r1Team("Equipe atual", "Pessoa atual", 4)])));
  await vi.waitFor(() => expect((screen.getByRole("button", { name: "Alocar" }) as HTMLButtonElement).disabled).toBe(false));
  expect(screen.queryByText("Antigo tardio — Confirmado")).toBeNull();
});

it("descarta contexto e resultados tardios ao trocar Encontro e revogar acesso durante POST", async () => {
  auth.active = true; const post = deferredResponse(); let refreshCount = 0;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path); if (init?.method === "POST") return post.promise;
    if (url.endsWith("workspace/equipes/")) { refreshCount++; return Response.json([url.includes("/38/") ? { ...r1Team("Equipe nova", "Pessoa nova"), encontro_id: 38 } : r1Team("Equipe antiga", "Pessoa antiga")]); }
    if (url.startsWith("/convites-encontros/?")) return Response.json(r1Page("Convite"));
    return Response.json({ count: 0, next: null, previous: null, results: [] });
  });
  const user = userEvent.setup(); const view = render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={r1Summary} />);
  await r1Desalocar(user); expect(r1Posts()).toHaveLength(1);
  view.rerender(<EncounterTeamPanel encontroId={38} capabilities={caps} equipes={r1Summary} />);
  expect(screen.queryByRole("dialog")).toBeNull(); await screen.findByText("Pessoa nova — alocado"); expect(screen.queryByText("Pessoa antiga — alocado")).toBeNull();
  view.rerender(<EncounterTeamPanel encontroId={38} capabilities={{ ...caps, acessar_equipes: false }} equipes={r1Summary} />);
  expect(screen.queryByText("Pessoa nova — alocado")).toBeNull(); expect(screen.queryByRole("button", { name: "Desalocar" })).toBeNull();
  await act(async () => post.resolve(Response.json({}))); expect(screen.queryByText("Pessoa antiga — alocado")).toBeNull();
  expect(screen.queryByRole("button", { name: "Desalocar" })).toBeNull(); expect(r1Posts()).toHaveLength(1); expect(refreshCount).toBe(2);
});

it("bloqueia envio de convite e outras ações durante POST de trabalho e recarga", async () => {
  const list = { count: 2, next: null, previous: null, results: [r1Invite("Convite"), { ...r1Invite("Confirmado sem trabalho"), id: 14, trabalho_id: null, trabalho_status: null }] };
  auth.active = true; const post = deferredResponse(), teams = deferredResponse(), invites = deferredResponse(); let loading = false;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path); if (init?.method === "POST") return post.promise;
    if (url.endsWith("workspace/equipes/")) return loading ? teams.promise : Response.json([r1Team("Equipe", "Pessoa")]);
    if (url.startsWith("/convites-encontros/?")) return loading ? invites.promise : Response.json(list);
    return Response.json({ count: 1, next: null, previous: null, results: [{ id: 20, pessoa_id: 21, nome: "Alpinista", grupo: null }] });
  });
  const user = userEvent.setup(); render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={r1Summary} />);
  await screen.findByRole("option", { name: "Alpinista" }); await screen.findByText("Convite — Confirmado");
  await user.selectOptions(screen.getByLabelText("Alpinista"), "21"); await user.selectOptions(screen.getByLabelText("Função"), "3");
  await r1Desalocar(user); expect(r1Posts()).toHaveLength(1);
  const register = screen.getByRole("button", { name: "Registrar convite" }); const allocate = screen.getByRole("button", { name: "Alocar" }); const start = screen.getByRole("button", { name: "Iniciar trabalho" });
  expect(register.matches(":disabled")).toBe(true); expect(allocate.matches(":disabled")).toBe(true); expect(start.matches(":disabled")).toBe(true);
  await user.click(register); await user.click(allocate); await user.click(start); expect(r1Posts()).toHaveLength(1);
  loading = true; await act(async () => post.resolve(Response.json({}))); await screen.findByText("Atualizando...");
  expect(register.matches(":disabled")).toBe(true); expect(allocate.matches(":disabled")).toBe(true); expect(start.matches(":disabled")).toBe(true);
  await user.click(register); await user.click(allocate); await user.click(start); expect(r1Posts()).toHaveLength(1);
  await act(async () => { teams.resolve(Response.json([r1Team("Equipe", "Pessoa")])); invites.resolve(Response.json(list)); });
  await vi.waitFor(() => expect(register.matches(":disabled")).toBe(false));
});

it("revoga gestão durante recarga e ignora respostas antigas sem restaurar escrita", async () => {
  auth.active = true; const oldTeams = deferredResponse(), oldInvites = deferredResponse(); let refreshing = false;
  vi.mocked(siaFetch).mockImplementation(async (path, init) => {
    const url = String(path); if (init?.method === "POST") { refreshing = true; return Response.json({}); }
    if (url.endsWith("workspace/equipes/")) return refreshing && auth.active ? oldTeams.promise : Response.json([r1Team("Leitura atual", "Pessoa atual")]);
    if (url.startsWith("/convites-encontros/?")) return refreshing ? oldInvites.promise : Response.json(r1Page("Protegido"));
    return Response.json({ count: 0, next: null, previous: null, results: [] });
  });
  const user = userEvent.setup(); const view = render(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={r1Summary} />);
  await r1Desalocar(user); await screen.findByText("Atualizando...");
  auth.active = false; view.rerender(<EncounterTeamPanel encontroId={37} capabilities={caps} equipes={r1Summary} />);
  expect(screen.queryByText("Protegido — Confirmado")).toBeNull(); expect(screen.queryByRole("dialog")).toBeNull();
  await screen.findByText("Pessoa atual — alocado");
  await act(async () => { oldTeams.resolve(Response.json([r1Team("Antiga", "Pessoa antiga")])); oldInvites.resolve(Response.json(r1Page("Antigo"))); });
  expect(screen.queryByText("Pessoa antiga — alocado")).toBeNull(); expect(screen.queryByText("Antigo — Confirmado")).toBeNull();
  expect(screen.queryByRole("button", { name: "Desalocar" })).toBeNull(); expect(screen.queryByRole("button", { name: "Alocar" })).toBeNull(); expect(r1Posts()).toHaveLength(1);
});
