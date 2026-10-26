import { describe, expect, it } from "vitest";

import {
  parsePreEncounterCare,
  parsePreEncounterContextCapabilities,
  parsePreEncounterDetail,
  parsePreEncounterItems,
  parsePreEncounterPhotoItems,
} from "./pre-encounter-contract";

const operational = {
  id: 7,
  identificacao: "Pessoa Exemplo",
  origem: "inscricao",
  presente: true,
  registrado_em: "2030-06-01T12:00:00-03:00",
  pagamento: "pendente",
  aptidao: { situacao: "apto", motivo: "Projeção canônica" },
  situacao_vaga: null,
  possui_foto: false,
  possui_dados_cuidado: true,
  cuidado_conferido: false,
};

const capabilities = {
  regularizar: true,
  registrar_pagamento: true,
  consultar_cuidados: true,
  conferir_cuidados: true,
  visualizar_foto: true,
  alterar_foto: true,
  associar_foto_pessoa: true,
  decidir_vaga: false,
};

describe("contratos operacionais do Pré-Encontro", () => {
  it("projeta o contrato mínimo de fotografia sem incorporar campos operacionais", () => {
    const page = parsePreEncounterPhotoItems({
      count: 1,
      next: null,
      previous: null,
      results: [{
        id: 7,
        identificacao: "Pessoa Exemplo",
        origem: "inscricao",
        possui_foto: true,
        capabilities: {
          visualizar_foto: true,
          alterar_foto: true,
          associar_foto_pessoa: false,
        },
        pagamento: "pago",
        pessoa_id: 99,
        cpf: "não deve integrar a projeção",
      }],
    });

    expect(page.results[0]).toEqual({
      id: 7,
      identificacao: "Pessoa Exemplo",
      origem: "inscricao",
      possui_foto: true,
      capabilities: {
        visualizar_foto: true,
        alterar_foto: true,
        associar_foto_pessoa: false,
      },
    });
    expect("pagamento" in page.results[0]).toBe(false);
    expect("pessoa_id" in page.results[0]).toBe(false);
    expect("cpf" in page.results[0]).toBe(false);
  });

  it("rejeita tipos e capabilities inválidos no contrato mínimo de fotografia", () => {
    expect(() => parsePreEncounterPhotoItems({
      count: 1,
      next: null,
      previous: null,
      results: [{
        id: 7,
        identificacao: "Pessoa Exemplo",
        origem: "inscricao",
        possui_foto: "sim",
        capabilities: {},
      }],
    })).toThrow();
  });

  it("preserva paginação, indicadores mínimos e aptidão recebida", () => {
    const page = parsePreEncounterItems({ count: 21, next: "?page=2", previous: null, results: [operational] });
    expect(page.count).toBe(21);
    expect(page.next).toBe("?page=2");
    expect(page.results[0].aptidao).toEqual({ situacao: "apto", motivo: "Projeção canônica" });
    expect(page.results[0].pagamento).toBe("pendente");
  });

  it("não incorpora conteúdo sensível de cuidado ao contrato comum", () => {
    const item = parsePreEncounterItems({ count: 1, next: null, previous: null, results: [operational] }).results[0];
    expect(item.possui_dados_cuidado).toBe(true);
    expect("alergias" in item).toBe(false);
    expect("medicamentos" in item).toBe(false);
  });

  it("aceita estados canônicos de vaga e rejeita shape inválido", () => {
    const detail = parsePreEncounterDetail({
      ...operational,
      situacao_vaga: "aguardando_decisao_diretoria",
      aptidao: { situacao: "aguardando_decisao_diretoria", motivo: "Há disputa" },
      pessoa_id: null,
      inscricao_id: 5,
      capabilities,
    });
    expect(detail.situacao_vaga).toBe("aguardando_decisao_diretoria");
    expect(() => parsePreEncounterItems({ count: 1, next: null, previous: null, results: [{ ...operational, pagamento: "quitado" }] })).toThrow();
  });

  it("valida capabilities sem identidade ou papéis", () => {
    const parsed = parsePreEncounterContextCapabilities({
      pre_encontro_configurado: false,
      localizar_atendimento_foto: true,
      consultar_operacao: true,
      baixar_pdf_operacional: true,
      consultar_cuidados: true,
      registrar_checkin: false,
      aumentar_capacidade: false,
      configurar_pre_encontro: true,
    });
    expect(parsed).toEqual({
      pre_encontro_configurado: false,
      localizar_atendimento_foto: true,
      consultar_operacao: true,
      baixar_pdf_operacional: true,
      consultar_cuidados: true,
      registrar_checkin: false,
      aumentar_capacidade: false,
      configurar_pre_encontro: true,
    });
    expect("roles" in parsed).toBe(false);
  });

  it("rejeita capabilities contextuais sem os estados explícitos de configuração", () => {
    expect(() => parsePreEncounterContextCapabilities({
      consultar_operacao: true,
      consultar_cuidados: true,
      registrar_checkin: false,
      aumentar_capacidade: false,
    })).toThrow();
  });

  it("mantém cuidado em contrato separado e completo", () => {
    const fields = {
      possui_alergias: "sim", alergias: "Declarado", possui_restricoes_intolerancias: "nao",
      restricoes_intolerancias: "", usa_medicamentos: "nao", medicamentos: "",
      horarios_medicamentos: "", observacoes_medicamentos: "", neurodivergencia_apoio: "nao",
      neurodivergencia_condicao: "", necessidades_apoio: "", sensibilidades_desconfortos: "",
      o_que_ajuda: "", outras_informacoes: "", observacoes: "", atualizado_em: "2030-06-01T10:00:00-03:00",
    };
    expect(parsePreEncounterCare(fields).alergias).toBe("Declarado");
    expect(() => parsePreEncounterCare({ atualizado_em: "2030-01-01" })).toThrow();
  });
});
