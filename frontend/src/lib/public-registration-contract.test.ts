import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./sia-api", () => ({ ensureCsrfToken: vi.fn().mockResolvedValue("csrf-publico") }));

import {
  ageOnCivilDate,
  buildPublicRegistrationPayload,
  emptyPublicRegistrationValues,
  finalizePublicRegistration,
  formatCepInput,
  isValidCpf,
  isMinorOnFirstOfficialDay,
  loadPublicRegistration,
  normalizeCep,
  parseCivilDate,
  publicSubmissionErrorMessage,
  submitPublicRegistration,
  validatePublicRegistration,
  type PublicRegistrationEncounter,
  type PublicRegistrationValues,
} from "./public-registration-contract";

const escalation: PublicRegistrationEncounter = {
  titulo: "Escalada 2030", tipo: "Escalada", inscricoes_abrem_em: "2030-01-01T00:00:00-03:00",
  inscricoes_encerram_em: "2030-05-01T00:00:00-03:00", inscricoes_abertas: true, primeiro_dia_oficial: "2030-06-01",
};

function validValues(): PublicRegistrationValues {
  return {
    ...emptyPublicRegistrationValues(), nome_completo: "Maria da Silva", data_nascimento: "2000-05-20",
    email: "maria@example.test", cep: "70000-000", logradouro: "Rua Um", numero: "10", bairro: "Centro",
    cidade: "Brasília", uf: "df", como_conheceu: "indicacao", possui_alergias: "nao",
    batismo: "sim", primeira_comunhao: "nao", crisma: "nao_sei",
    possui_restricoes_intolerancias: "nao", usa_medicamentos: "nao", neurodivergencia_apoio: "nao",
  };
}

describe("contrato público da ficha", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("calcula idade usando datas civis, sem depender de timestamp ou timezone", () => {
    expect(parseCivilDate("2030-02-29")).toBeNull();
    expect(parseCivilDate("2032-02-29")).toEqual({ year: 2032, month: 2, day: 29 });
    expect(ageOnCivilDate("2012-06-02", "2030-06-01")).toBe(17);
    expect(ageOnCivilDate("2012-06-01", "2030-06-01")).toBe(18);
    expect(isMinorOnFirstOfficialDay("2012-06-02", escalation)).toBe(true);
  });

  it("exige responsável de quem tem 17 anos no primeiro dia, mesmo que faça 18 durante o Encontro", () => {
    const values = { ...validValues(), data_nascimento: "2012-06-02" };
    const errors = validatePublicRegistration(values, escalation);
    expect(errors.responsavel_nome).toBeTruthy();
    expect(errors.responsavel_cpf).toBeTruthy();
    expect(errors.responsavel_parentesco).toBeTruthy();
    expect(errors.responsavel_telefone).toBeTruthy();
  });

  it("trata quem completa 18 no primeiro dia como adulto e permite ausência de contato", () => {
    const values = { ...validValues(), data_nascimento: "2012-06-01" };
    expect(validatePublicRegistration(values, escalation)).toEqual({});
    expect(buildPublicRegistrationPayload(values, escalation).responsavel).toBeUndefined();
  });

  it("aceita contato de emergência adulto sem CPF, mas exige o conjunto mínimo quando iniciado", () => {
    const values = { ...validValues(), responsavel_nome: "José", responsavel_parentesco: "Pai", responsavel_telefone: "61999999999" };
    expect(validatePublicRegistration(values, escalation)).toEqual({});
    expect(buildPublicRegistrationPayload(values, escalation).responsavel).toEqual(expect.objectContaining({ cpf: "", nome_completo: "José" }));
    expect(validatePublicRegistration({ ...validValues(), responsavel_nome: "José" }, escalation).responsavel_telefone).toBeTruthy();
  });

  it("recalcula a seção condicional quando a data de nascimento muda", () => {
    const adult = validValues();
    expect(validatePublicRegistration(adult, escalation).responsavel_nome).toBeUndefined();
    const minor = { ...adult, data_nascimento: "2015-01-01" };
    expect(validatePublicRegistration(minor, escalation).responsavel_nome).toBeTruthy();
  });

  it("valida contato alternativo, Outro e detalhes de cuidado", () => {
    const values = { ...validValues(), email: "", telefone_whatsapp: "", como_conheceu: "outro", possui_alergias: "sim", usa_medicamentos: "sim" };
    const errors = validatePublicRegistration(values, escalation);
    expect(errors.email).toBeTruthy();
    expect(errors.telefone_whatsapp).toBeTruthy();
    expect(errors.como_conheceu_outro).toBeTruthy();
    expect(errors.alergias).toBeTruthy();
    expect(errors.medicamentos).toBeTruthy();
    expect(errors.horarios_medicamentos).toBeTruthy();
  });

  it("alinha a validação de CPF ao backend antes da revisão", () => {
    expect(isValidCpf("529.982.247-25")).toBe(true);
    expect(isValidCpf("52998224725")).toBe(true);
    expect(isValidCpf("12345678900")).toBe(false);
    expect(validatePublicRegistration({ ...validValues(), cpf: "12345678900" }, escalation).cpf).toContain("CPF válido");
    expect(validatePublicRegistration({ ...validValues(), cpf: "" }, escalation)).toEqual({});
  });

  it("valida, mascara e normaliza CEP estruturalmente", () => {
    expect(normalizeCep("71900000")).toBe("71900-000");
    expect(normalizeCep("71900-000")).toBe("71900-000");
    expect(formatCepInput("71900000")).toBe("71900-000");
    expect(normalizeCep("7190000")).toBeNull();
    expect(normalizeCep("719000000")).toBeNull();
    expect(normalizeCep("7190A000")).toBeNull();
    expect(validatePublicRegistration({ ...validValues(), cep: "7190000" }, escalation).cep).toBe("Informe um CEP com 8 dígitos.");
    expect(validatePublicRegistration({ ...validValues(), cep: "719000000" }, escalation).cep).toBe("Informe um CEP com 8 dígitos.");
    expect(validatePublicRegistration({ ...validValues(), cep: "7190A000" }, escalation).cep).toBe("Informe um CEP com 8 dígitos.");
    expect(buildPublicRegistrationPayload({ ...validValues(), cep: "71900000" }, escalation).dados_declarados.cep).toBe("71900-000");
  });

  it("exige Como conheceu e elimina complemento contraditório ao sair de Outro", () => {
    expect(validatePublicRegistration({ ...validValues(), como_conheceu: "" }, escalation).como_conheceu).toBeTruthy();
    expect(validatePublicRegistration({ ...validValues(), como_conheceu: "outro", como_conheceu_outro: "" }, escalation).como_conheceu_outro).toBeTruthy();
    const payload = buildPublicRegistrationPayload(
      { ...validValues(), como_conheceu: "paroquia", como_conheceu_outro: "valor antigo" },
      escalation,
    );
    expect(payload.dados_declarados.como_conheceu).toBe("paroquia");
    expect(payload.dados_declarados.como_conheceu_outro).toBe("");
  });

  it("aceita somente e-mail ou somente telefone como contato", () => {
    expect(validatePublicRegistration(validValues(), escalation)).toEqual({});
    const phoneOnly = { ...validValues(), email: "", telefone_whatsapp: "61999999999" };
    expect(validatePublicRegistration(phoneOnly, escalation)).toEqual({});
  });

  it("exige escolha explícita dos sacramentos sem alterar os valores canônicos", () => {
    const values = { ...validValues(), batismo: "", primeira_comunhao: "", crisma: "" };
    const errors = validatePublicRegistration(values, escalation);
    expect(errors.batismo).toBeTruthy();
    expect(errors.primeira_comunhao).toBeTruthy();
    expect(errors.crisma).toBeTruthy();
    expect(buildPublicRegistrationPayload(validValues(), escalation).dados_declarados).toEqual(
      expect.objectContaining({ batismo: "sim", primeira_comunhao: "nao", crisma: "nao_sei" }),
    );
  });

  it("inclui dados específicos somente no ESPPA e valida cônjuge ou referência", () => {
    const esppa = { ...escalation, tipo: "Esppa" as const };
    expect(validatePublicRegistration(validValues(), esppa).estado_civil).toBeTruthy();
    const married = { ...validValues(), estado_civil: "casado", nome_conjuge: "Ana", telefone_conjuge: "61999999999" };
    expect(validatePublicRegistration(married, esppa)).toEqual({});
    expect(buildPublicRegistrationPayload(married, esppa).dados_esppa).toEqual(expect.objectContaining({ estado_civil: "casado", nome_conjuge: "Ana" }));
    expect(buildPublicRegistrationPayload(married, escalation).dados_esppa).toBeUndefined();
  });

  it("preparar e revisar o payload não faz POST; somente a confirmação final envia uma vez", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({ mensagem: "ok" }, { status: 201 }));
    const payload = buildPublicRegistrationPayload(validValues(), escalation);
    expect(fetchMock).not.toHaveBeenCalled();
    const response = await submitPublicRegistration("123e4567-e89b-42d3-a456-426614174000", payload);
    expect(response.status).toBe(201);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/public/encontros/"), expect.objectContaining({ method: "POST", credentials: "same-origin" }));
    const init = fetchMock.mock.calls[0][1];
    expect(new Headers(init?.headers).get("authorization")).toBeNull();
    expect(JSON.parse(String(init?.body))).toEqual(payload);
  });

  it("carrega Escalada e ESPPA pelo BFF e preserva estados indisponíveis", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json(escalation))
      .mockResolvedValueOnce(Response.json({ ...escalation, tipo: "Esppa" }))
      .mockResolvedValueOnce(Response.json({ detail: "indisponível" }, { status: 404 }))
      .mockResolvedValueOnce(Response.json({ detail: "temporário" }, { status: 502 }));
    expect((await loadPublicRegistration("uuid-escalada")).encounter?.tipo).toBe("Escalada");
    expect((await loadPublicRegistration("uuid-esppa")).encounter?.tipo).toBe("Esppa");
    expect((await loadPublicRegistration("uuid-ausente")).response.status).toBe(404);
    expect((await loadPublicRegistration("uuid-temporario")).response.status).toBe(502);
    expect(fetchMock.mock.calls.every(([url]) => String(url).startsWith("/api/public/encontros/"))).toBe(true);
  });

  it("traduz falhas públicas sem expor detalhes internos", () => {
    expect(publicSubmissionErrorMessage(400)).toContain("Revise");
    expect(publicSubmissionErrorMessage(404)).toContain("não está mais disponível");
    expect(publicSubmissionErrorMessage(429)).toContain("Muitas tentativas");
    expect(publicSubmissionErrorMessage(502)).toContain("alguns instantes");
  });

  it("conclui o fluxo somente após resposta real de sucesso do BFF", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({ mensagem: "Inscrição enviada com sucesso." }, { status: 201 }),
    );
    const result = await finalizePublicRegistration(
      "123e4567-e89b-42d3-a456-426614174000",
      validValues(),
      escalation,
    );
    expect(result).toEqual({ success: true, message: "Inscrição enviada com sucesso." });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ method: "POST" }));
  });

  it.each([400, 404, 429, 502])("não produz sucesso quando o BFF responde %s", async (status) => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({ detail: "erro público" }, { status }),
    );
    const result = await finalizePublicRegistration("123e4567-e89b-42d3-a456-426614174000", validValues(), escalation);
    expect(result.success).toBe(false);
    expect(result.message).toBeTruthy();
  });
});
