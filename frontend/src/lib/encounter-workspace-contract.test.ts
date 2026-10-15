import { describe, expect, it } from "vitest";

import {
  parseEncounterCandidateFull,
  parseEncounterCandidatePage,
  parseEncounterCandidateSummary,
  parseEncounterRegistrationConfig,
  parseEncounterWorkspaceCapabilities,
} from "./encounter-workspace-contract";

const summary = {
  ref: { origem_tipo: "INSCRICAO", origem_id: "2a62fca6-e0cc-4fb4-9728-8ff8be832adc" },
  nome: "Candidata",
  origem: { codigo: "INSCRICAO", label: "Inscrição" },
  situacao: { codigo: "INSCRITO", label: "Inscrito" },
  presenca_pre: false,
  aptidao: null,
  pessoa_id: null,
};

describe("contrato do Workspace do Encontro", () => {
  it("mantém summary sem contato ou dados sensíveis", () => {
    const parsed = parseEncounterCandidateSummary(summary);
    expect(parsed.situacao.codigo).toBe("INSCRITO");
    expect("telefone" in parsed).toBe(false);
    expect("cuidados" in parsed).toBe(false);
    expect("cpf" in parsed).toBe(false);
  });

  it("modela full somente com telefone e nunca cuidados", () => {
    const parsed = parseEncounterCandidateFull({ ...summary, telefone: "61999990000" });
    expect(parsed.telefone).toBe("61999990000");
    expect("cuidados" in parsed).toBe(false);
  });

  it("torna paginação explícita", () => {
    const page = parseEncounterCandidatePage({ count: 12, next: "?page=2", previous: null, results: [summary] });
    expect(page.count).toBe(12);
    expect(page.results).toHaveLength(1);
  });

  it("aceita somente códigos canônicos de origem e situação", () => {
    expect(() => parseEncounterCandidateSummary({ ...summary, origem: { codigo: "LEGADO", label: "Legado" } })).toThrow();
    expect(() => parseEncounterCandidateSummary({ ...summary, situacao: { codigo: "PENDENTE", label: "Pendente" } })).toThrow();
  });

  it("usa capabilities server-driven sem roles", () => {
    const capabilities = parseEncounterWorkspaceCapabilities({
      consultar_resumo: true,
      consultar_encontristas: true,
      consultar_contato: false,
      acessar_pre_encontro: true,
      acessar_equipes: false,
      acessar_formacao: false,
      acessar_agenda: true,
      consultar_inscricoes: true,
      configurar_inscricoes: true,
    });
    expect(capabilities.consultar_contato).toBe(false);
    expect("roles" in capabilities).toBe(false);
  });

  it("modela a ausência e a configuração sem tornar public_id editável", () => {
    const ausente = parseEncounterRegistrationConfig({
      configurado: false,
      capacidade: null,
      idade_minima: null,
      idade_maxima: null,
      inscricoes_abrem_em: null,
      inscricoes_encerram_em: null,
      public_id: null,
      status_janela: null,
    });
    expect(ausente.configurado).toBe(false);

    const configurada = parseEncounterRegistrationConfig({
      configurado: true,
      capacidade: 30,
      idade_minima: 15,
      idade_maxima: 18,
      inscricoes_abrem_em: "2030-01-01T08:00:00-03:00",
      inscricoes_encerram_em: "2030-02-01T08:00:00-03:00",
      public_id: "2a62fca6-e0cc-4fb4-9728-8ff8be832adc",
      status_janela: "abertas",
    });
    expect(configurada.configurado && configurada.public_id).toBe(
      "2a62fca6-e0cc-4fb4-9728-8ff8be832adc",
    );
  });
});
