// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { siaFetch } from "../../lib/sia-api";
import { EncounterTeamPanel } from "../encounter-team/EncounterTeamPanel";
import { EncounterTeamSetup } from "../encounter-team/EncounterTeamSetup";
import { EncounterWorkspace, type EncounterWorkspaceTab } from "../EncounterWorkspace";
const auth = vi.hoisted(() => ({ active: false }));
vi.mock("../../lib/sia-api", () => ({ siaFetch: vi.fn() }));
vi.mock("../SiaSessionProvider", () => ({ useSiaSession: () => ({ session: auth.active ? { id: 1, username: "suporte", roles: ["Suporte"], superuser: false } : null }) }));
vi.mock("../EncounterAgendaSection", () => ({ EncounterAgendaSection: () => null }));
const caps = { consultar_resumo: true, consultar_encontristas: false, consultar_contato: false, acessar_pre_encontro: false, acessar_equipes: true, acessar_formacao: false, acessar_agenda: false, consultar_inscricoes: false, configurar_inscricoes: false };
const summary = { encontro: { id: 37, nome: "Encontro Exemplo", tipo: "ESCALADA", local: "Local fictício" }, lifecycle: "EM_PREPARACAO", agenda: { configurada: false, oficializada: false, quantidade_itens: 0, proximo_item: null, datas_principais: [], pre_encontro_data: null }, encontristas: { inscricoes_recebidas: 0, pendentes: 0, confirmados: 0, total_funil: 0, por_situacao: { INSCRITO: 0, CANCELADO: 0, AGUARDANDO_DECISAO: 0, APTO: 0, NAO_APTO: 0, CONFIRMADO: 0 } }, pre_encontro: { configurado: false, data: null, capacidade: null, quantidade_checkins: 0, quantidade_aptos: 0, quantidade_aguardando_decisao: 0 }, equipes: { modelo_equipes: "CANONICO", quantidade_equipes: 0, quantidade_funcoes: 0, vagas_estruturais: null, vagas_preenchidas: 0 }, formacao: { total_sessoes: 0, planejadas: 0, realizadas: 0, canceladas: 0 }, alertas: [] };
function Harness() { const [tab, setTab] = useState<EncounterWorkspaceTab>("visao-geral"); return <EncounterWorkspace encontroId="37" activeTab={tab} onTabChange={setTab} renderTeam={(capabilities, equipes, resumoErro) => <EncounterTeamPanel encontroId={37} capabilities={capabilities} equipes={equipes} resumoErro={resumoErro} />} />; }
beforeEach(() => { auth.active = false; vi.mocked(siaFetch).mockReset(); });
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
