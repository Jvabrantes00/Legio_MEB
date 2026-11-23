import { describe, expect, it } from "vitest";
import { buildEncounterTeamPath, parseEncounterTeams, parseSelectorPage, parseInvitePage, parseEligibilityError, parseReadiness, parseActivation, parsePreparation } from "./encounter-team-contract";

const team = () => ({ id: 1, encontro_id: 2, codigo: "A", nome: "Equipe", ordem: 0, capacidade_minima_recomendada: null, capacidade_maxima_recomendada: 4, capacidade: { resultado: "AVISO", motivos: [{ codigo: "CAPACIDADE_MINIMA_NAO_ATINGIDA", categoria: "AVISO", mensagem: "Abaixo", contexto: { equipe_id: 1, cpf: "privado" } }] }, composicao: { resultado: "ELEGIVEL", motivos: [] }, roles: [{ id: 3, codigo: "R", nome: "Role", ordem: 0, quantidade_estrutural: null, concede_registro_presenca: false, trabalhos: [{ id: 4, pessoa_id: 5, pessoa_nome: "Pessoa", status: "alocado", cpf: "privado" }] }] });
describe("contrato de equipes", () => {
  it("valida as projeções e elimina dados extras", () => {
    const paging = { count: 1, next: null, previous: null };
    const result = parseSelectorPage({ ...paging, results: [{ id: 1, pessoa_id: 2, nome: "Ana", grupo: "A", cpf: "privado" }] });
    expect(JSON.stringify(result)).not.toContain("privado");
    expect(parseInvitePage({ ...paging, results: [{ id: 1, pessoa_id: 2, pessoa_nome: "Ana", encontro_id: 3, finalidade: "trabalhar", status: "sem_resposta", role_trabalho_proposta_id: null, criado_em: "2026-01-01" }] }).results[0].status).toBe("sem_resposta");
    expect(() => parseInvitePage({ ...paging, results: [{ finalidade: "participar" }] })).toThrow();
    expect(parseEligibilityError({ avaliacao: { resultado: "AVISO", motivos: [{ codigo: "ALPINISTA_INATIVO", categoria: "AVISO", mensagem: "Aviso" }] } }).motivos[0].categoria).toBe("AVISO");
    expect(parseReadiness({ elegivel: true, motivos: [], contagens: { vinculos_legados_equipe: 0, vinculos_tipo_indefinido: 0, equipes_canonicas: 0, trabalhos_canonicos: 0 } }).elegivel).toBe(true);
    expect(parseActivation({ modelo_equipes: "CANONICO" }).modelo_equipes).toBe("CANONICO");
    expect(parsePreparation([{ id: 1, nome: "Equipe" }])).toHaveLength(1);
  });
  it("aceita dados válidos e nulos permitidos, descartando extras", () => {
    const parsed = parseEncounterTeams([{ ...team(), segredo: "privado" }]);
    expect(parsed[0].capacidade_minima_recomendada).toBeNull();
    expect(parsed[0].roles[0].quantidade_estrutural).toBeNull();
    expect(JSON.stringify(parsed)).not.toContain("privado");
    expect(buildEncounterTeamPath(2)).toBe("/encontros/2/workspace/equipes/");
  });
  it("rejeita enums, tipos, nulos e estruturas inválidas", () => {
    for (const value of [null, {}, [null], [{ ...team(), nome: null }], [{ ...team(), ordem: "1" }], [{ ...team(), roles: {} }], [{ ...team(), capacidade: { resultado: "OUTRO", motivos: [] } }], [{ ...team(), composicao: { resultado: "AVISO", motivos: [{ codigo: "INVALIDO", categoria: "AVISO", mensagem: "x" }] } }], [{ ...team(), capacidade: { resultado: "AVISO", motivos: [{ codigo: "CAPACIDADE_MAXIMA_EXCEDIDA", categoria: "AVISO", mensagem: "x", contexto: null }] } }]]) expect(() => parseEncounterTeams(value)).toThrow();
  });
});
