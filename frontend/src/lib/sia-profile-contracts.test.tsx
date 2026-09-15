import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { AlpinistaSummaryPanel } from "../components/AlpinistaSummaryPanel";
import { EncontroSummaryPanel } from "../components/EncontroSummaryPanel";
import { ConfirmedAlpinistasTable } from "../components/ConfirmedAlpinistasTable";
import {
  confirmedAlpinistas, isAlpinistaFull, isEncontroFull,
  type AlpinistaFull, type AlpinistaSummary, type EncounterParticipation, type EncontroSummary,
} from "./sia-profile-contracts";

const summary: AlpinistaSummary = {
  id: 1, nome: "Pessoa resumida", foto: null, idade: 17, grupo: "Grupo teste",
  whatsapp: "61900000000", batizado: true, primeira_comunhao: null,
  crismado: false, musica: { violeiro: true, canta: false },
  responsaveis: [{ nome: "Responsável", telefone: "61911111111" }],
};
const full: AlpinistaFull = {
  id: 2, nome: "Pessoa completa", foto: null, cpf: null,
  email: "pessoa@example.test", telefone: "61900000000", dataNascimento: null,
  endereco: null, nomePai: null, telefonePai: null, nomeMae: null,
  telefoneMae: null, restricaoSaude: null, medicacao: null,
  conheciaEscalada: null, grupo: null, status: "pendente",
  batizado: null, primeira_comunhao: null, crismado: null,
  eh_violeiro: false, canta: false, is_neurodivergente: false,
  tipo_neurodivergente: null, idade_atual: null,
  encontros_realizados: [], historico_equipes: [], historico_eventos: [],
};

describe("contratos resumido e completo de Alpinista", () => {
  it("distingue o resumo sem status do perfil completo", () => {
    expect(isAlpinistaFull(summary)).toBe(false);
    expect(isAlpinistaFull(full)).toBe(true);
    expect(isAlpinistaFull(null)).toBe(false);
  });

  it("resumo mostra apenas campos permitidos, incluindo música/sacramentos/responsáveis", () => {
    const html = renderToStaticMarkup(<AlpinistaSummaryPanel profile={summary} />);
    expect(html).toContain("WhatsApp");
    expect(html).toContain("Batizado");
    expect(html).toContain("Violeiro");
    expect(html).toContain("Responsável");
    expect(html).not.toMatch(/CPF|E-mail|Endereço|Medicações|Neurodivergência|Status/);
  });

  it("responsáveis ausentes não causam acesso a campo inexistente", () => {
    const html = renderToStaticMarkup(<AlpinistaSummaryPanel profile={{ ...summary, responsaveis: undefined }} />);
    expect(html).not.toContain("Responsáveis");
  });
});

describe("Encontro da Comunicação e participações", () => {
  const encontro: EncontroSummary = {
    id: 7, encontro: "Encontro resumido", tipo: "AVC", data_referencia: "2026-10-15",
  };

  it("resumo de Encontro não usa local, status nem data exata", () => {
    expect(isEncontroFull(encontro)).toBe(false);
    expect(isEncontroFull(null)).toBe(false);
    const html = renderToStaticMarkup(<EncontroSummaryPanel encontro={encontro} />);
    expect(html).toContain("Encontro resumido");
    expect(html).toContain("AVC");
    expect(html).not.toMatch(/Local|Status|Dias do Encontro|Efetivar|Remover/);
  });

  it("perfil completo é identificado pelos campos reais", () => {
    expect(isEncontroFull({ ...encontro, local: "Local", status: "agendado", data_exato: "Dias" })).toBe(true);
  });

  it("confirmados usam somente id/nome, sem contato ou nascimento inventados", () => {
    const participacoes: EncounterParticipation[] = [
      { id: 1, alpinista: { id: 10, nome: "Confirmado" }, funcao: { id: 1, nome: "Encontrista", tipo: "encontrista" } },
      { id: 2, alpinista: { id: 11, nome: "Equipe" }, funcao: { id: 2, nome: "Equipe", tipo: "equipe" } },
    ];
    expect(confirmedAlpinistas(participacoes)).toEqual([{ id: 10, nome: "Confirmado" }]);
    const html = renderToStaticMarkup(<ConfirmedAlpinistasTable
      people={confirmedAlpinistas(participacoes)} selected={[]} toggle={() => {}}
    />);
    expect(html).toContain("Confirmado");
    expect(html).not.toMatch(/Contato|Telefone|E-mail|Nascimento/);
  });
});
