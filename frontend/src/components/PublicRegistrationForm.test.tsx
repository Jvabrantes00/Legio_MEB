// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/sia-api", () => ({ ensureCsrfToken: vi.fn().mockResolvedValue("csrf-publico") }));

import { createSingleSubmissionGuard, PublicRegistrationForm, PublicRegistrationStatusCard, PublicRegistrationSuccess, PublicSubmissionFeedback } from "./PublicRegistrationForm";
import { CareSection, EsppaSection, OriginSacramentsSection, ResponsibleSection } from "./public-registration/PublicRegistrationSections";
import { PublicRegistrationReview } from "./public-registration/PublicRegistrationReview";
import { emptyPublicRegistrationValues, finalizePublicRegistration, type PublicRegistrationEncounter } from "../lib/public-registration-contract";

const encounter: PublicRegistrationEncounter = {
  titulo: "Escalada 2030", tipo: "Escalada", inscricoes_abrem_em: "2030-01-01T00:00:00-03:00",
  inscricoes_encerram_em: "2030-05-01T00:00:00-03:00", inscricoes_abertas: true, primeiro_dia_oficial: "2030-06-01",
};
const props = (overrides = {}) => ({ values: { ...emptyPublicRegistrationValues(), ...overrides }, errors: {}, encounter, change: () => undefined });

beforeEach(() => {
  Object.defineProperty(window, "scrollTo", { value: vi.fn(), writable: true });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function fillValidForm() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/^Nome completo/), "Pessoa Teste");
  await user.type(screen.getByLabelText(/^Data de nascimento/), "2000-01-01");
  await user.type(screen.getByLabelText(/^E-mail$/), "pessoa@example.test");
  await user.type(screen.getByLabelText(/^CEP/), "70000-000");
  await user.type(screen.getByLabelText(/^Logradouro/), "Rua Um");
  await user.type(screen.getByLabelText(/^Número/), "1");
  await user.type(screen.getByLabelText(/^Bairro/), "Centro");
  await user.type(screen.getByLabelText(/^Cidade/), "Brasília");
  await user.type(screen.getByLabelText(/^UF/), "DF");
  const originSelect = screen.getByLabelText(/^Como conheceu o Movimento Escalada\?/);
  await user.selectOptions(originSelect, "outro");
  await user.type(screen.getByLabelText(/^Conte como conheceu/), "Informação temporária");
  await user.selectOptions(originSelect, "indicacao");
  expect(screen.queryByLabelText(/^Conte como conheceu/)).toBeNull();
  await user.selectOptions(screen.getByLabelText(/^Batismo/), "sim");
  await user.selectOptions(screen.getByLabelText(/^Primeira Comunhão/), "nao");
  await user.selectOptions(screen.getByLabelText(/^Crisma/), "nao_informado");
  await user.click(within(screen.getByRole("group", { name: /^Possui alergias\?/ })).getByRole("radio", { name: "Não" }));
  await user.click(within(screen.getByRole("group", { name: /^Possui intolerância ou restrição alimentar\?/ })).getByRole("radio", { name: "Não" }));
  await user.click(within(screen.getByRole("group", { name: /^Usa medicamentos\?/ })).getByRole("radio", { name: "Não" }));
  await user.click(within(screen.getByRole("group", { name: /Existe neurodivergência/ })).getByRole("radio", { name: "Não" }));
  return user;
}

describe("ficha pública", () => {
  it("renderiza carregamento e estados públicos minimizados sem navegação privada", () => {
    const loading = renderToStaticMarkup(<PublicRegistrationForm publicId="123e4567-e89b-42d3-a456-426614174000" />);
    expect(loading).toContain("Carregando ficha");
    expect(loading).not.toContain("Sair");
    expect(loading).not.toContain("Alpinistas");
    expect(renderToStaticMarkup(<PublicRegistrationStatusCard state="not-found" />)).toContain("Ficha indisponível");
    expect(renderToStaticMarkup(<PublicRegistrationStatusCard state="temporary" />)).toContain("temporariamente indisponível");
  });

  it("mostra responsável legal para menor e contato opcional para adulto", () => {
    const minor = renderToStaticMarkup(<ResponsibleSection {...props({ data_nascimento: "2012-06-02" })} />);
    expect(minor).toContain("Responsável legal");
    expect(minor).toContain("required");
    const adult = renderToStaticMarkup(<ResponsibleSection {...props({ data_nascimento: "2012-06-01" })} />);
    expect(adult).toContain("Contato de emergência (opcional)");
  });

  it("altera os campos de cuidado de acordo com respostas condicionais", () => {
    const hidden = renderToStaticMarkup(<CareSection {...props({ possui_alergias: "nao", possui_restricoes_intolerancias: "nao", usa_medicamentos: "nao", neurodivergencia_apoio: "nao" })} />);
    expect(hidden).not.toContain("Quais alergias?");
    const shown = renderToStaticMarkup(<CareSection {...props({ possui_alergias: "sim", possui_restricoes_intolerancias: "sim", usa_medicamentos: "sim", neurodivergencia_apoio: "sim" })} />);
    expect(shown).toContain("Quais alergias?");
    expect(shown).toContain("O que costuma ajudar");
  });

  it("apresenta sacramentos como selects acessíveis com placeholder", () => {
    const html = renderToStaticMarkup(<OriginSacramentsSection {...props()} />);
    expect(html.match(/<select/g)).toHaveLength(4);
    expect(html).toContain("Selecione");
    expect(html).toContain('value="nao_informado"');
    expect(html).not.toContain('name="batismo" type="radio"');
  });

  it("apresenta Como conheceu como select com opções canônicas", () => {
    render(<OriginSacramentsSection {...props()} />);
    const select = screen.getByLabelText(/^Como conheceu o Movimento Escalada\?/);
    expect(select.tagName).toBe("SELECT");
    expect((within(select).getByRole("option", { name: "Selecione" }) as HTMLOptionElement).value).toBe("");
    expect((within(select).getByRole("option", { name: "Indicação de amigo/familiar" }) as HTMLOptionElement).value).toBe("indicacao");
    expect((within(select).getByRole("option", { name: "Paróquia" }) as HTMLOptionElement).value).toBe("paroquia");
    expect((within(select).getByRole("option", { name: "Redes sociais" }) as HTMLOptionElement).value).toBe("redes_sociais");
    expect((within(select).getByRole("option", { name: "Já conhecia o Movimento Escalada" }) as HTMLOptionElement).value).toBe("ja_conhecia");
    expect((within(select).getByRole("option", { name: "Outro" }) as HTMLOptionElement).value).toBe("outro");
  });

  it("não mostra ESPPA na Escalada e mostra os campos no ESPPA", () => {
    expect(renderToStaticMarkup(<EsppaSection {...props()} />)).toBe("");
    const html = renderToStaticMarkup(<EsppaSection {...props()} encounter={{ ...encounter, tipo: "Esppa" }} />);
    expect(html).toContain("Informações específicas do ESPPA");
    expect(html).toContain("Estado civil");
  });

  it("apresenta revisão e ações sem criar identificadores ou navegação interna", () => {
    const values = { ...emptyPublicRegistrationValues(), nome_completo: "Pessoa Teste", data_nascimento: "2000-01-01", email: "pessoa@example.test" };
    const html = renderToStaticMarkup(<PublicRegistrationReview values={values} encounter={encounter} />);
    expect(html).toContain("Revise antes de enviar");
    expect(html).toContain("Pessoa Teste");
    expect(html).not.toContain("pessoa_id");
    expect(html).not.toContain("Dashboard");
  });

  it("bloqueia confirmação duplicada enquanto o primeiro envio está em andamento", async () => {
    const guard = createSingleSubmissionGuard();
    let calls = 0;
    let finish!: () => void;
    const operation = () => new Promise<void>((resolve) => { calls += 1; finish = resolve; });
    const first = guard(operation);
    const second = guard(operation);
    expect(await second).toBeUndefined();
    expect(calls).toBe(1);
    finish();
    await first;
  });

  it("mostra a confirmação aprovada apenas no estado de sucesso", () => {
    const html = renderToStaticMarkup(<PublicRegistrationSuccess />);
    expect(html).toContain("Inscrição recebida com sucesso.");
    expect(html).toContain("aguarde o contato ou convite");
    expect(html).not.toContain("vaga garantida");
  });

  it("integra confirmação final, POST único e transição visual para sucesso", async () => {
    const values = {
      ...emptyPublicRegistrationValues(), nome_completo: "Pessoa Teste", data_nascimento: "2000-01-01",
      email: "pessoa@example.test", cep: "70000-000", logradouro: "Rua Um", numero: "1",
      bairro: "Centro", cidade: "Brasília", uf: "DF", como_conheceu: "indicacao",
      batismo: "sim", primeira_comunhao: "nao", crisma: "nao_informado",
      possui_alergias: "nao", possui_restricoes_intolerancias: "nao", usa_medicamentos: "nao",
      neurodivergencia_apoio: "prefere_nao_informar",
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({ mensagem: "Inscrição enviada com sucesso." }, { status: 201 }),
    );
    const result = await finalizePublicRegistration("123e4567-e89b-42d3-a456-426614174000", values, encounter);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.success).toBe(true);
    const html = result.success ? renderToStaticMarkup(<PublicRegistrationSuccess />) : "";
    expect(html).toContain("Inscrição recebida com sucesso.");
  });

  it("mantém o erro visível e não renderiza sucesso quando o POST falha", async () => {
    const values = {
      ...emptyPublicRegistrationValues(), nome_completo: "Pessoa Teste", data_nascimento: "2000-01-01",
      email: "pessoa@example.test", cep: "70000-000", logradouro: "Rua Um", numero: "1",
      bairro: "Centro", cidade: "Brasília", uf: "DF", como_conheceu: "indicacao",
      batismo: "sim", primeira_comunhao: "nao", crisma: "nao_informado",
      possui_alergias: "nao", possui_restricoes_intolerancias: "nao", usa_medicamentos: "nao",
      neurodivergencia_apoio: "nao",
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({ detail: "erro" }, { status: 400 }));
    const result = await finalizePublicRegistration("123e4567-e89b-42d3-a456-426614174000", values, encounter);
    expect(result.success).toBe(false);
    const html = result.success ? renderToStaticMarkup(<PublicRegistrationSuccess />) : renderToStaticMarkup(<PublicSubmissionFeedback message={result.message} />);
    expect(html).toContain('role="alert"');
    expect(html).toContain("Revise os dados");
    expect(html).not.toContain("Inscrição recebida com sucesso.");
  });

  it("clica no fluxo real, não envia na revisão e mostra sucesso após um único POST", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json(encounter))
      .mockResolvedValueOnce(Response.json({ mensagem: "Inscrição enviada com sucesso." }, { status: 201 }));
    render(<PublicRegistrationForm publicId="123e4567-e89b-42d3-a456-426614174000" />);
    await screen.findByRole("heading", { name: "Escalada 2030" });
    const user = await fillValidForm();

    await user.click(screen.getByRole("button", { name: "Revisar inscrição" }));
    expect(await screen.findByRole("heading", { name: "Revise antes de enviar" })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Finalizar inscrição" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Inscrição recebida com sucesso." })).toBeTruthy());
    expect(screen.queryByRole("heading", { name: "Revise antes de enviar" })).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "POST" }));
    const payload = JSON.parse(String(fetchMock.mock.calls[1][1]?.body));
    expect(payload.dados_declarados.como_conheceu).toBe("indicacao");
    expect(payload.dados_declarados.como_conheceu_outro).toBe("");
  });

  it("mascara CEP sem hífen durante a digitação", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json(encounter));
    render(<PublicRegistrationForm publicId="123e4567-e89b-42d3-a456-426614174000" />);
    await screen.findByRole("heading", { name: "Escalada 2030" });
    const user = userEvent.setup();
    const cep = screen.getByLabelText(/^CEP/) as HTMLInputElement;
    await user.type(cep, "71900000");
    expect(cep.value).toBe("71900-000");
  });

  it("impede revisão e POST quando o CEP é inválido", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json(encounter));
    render(<PublicRegistrationForm publicId="123e4567-e89b-42d3-a456-426614174000" />);
    await screen.findByRole("heading", { name: "Escalada 2030" });
    const user = await fillValidForm();
    const cep = screen.getByLabelText(/^CEP/);
    await user.clear(cep);
    await user.type(cep, "7190000");
    await user.click(screen.getByRole("button", { name: "Revisar inscrição" }));

    expect(await screen.findByText("Informe um CEP com 8 dígitos.")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Revise antes de enviar" })).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("volta ao formulário com erro visível quando o POST real é rejeitado", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json(encounter))
      .mockResolvedValueOnce(Response.json({ detail: "Revise os dados informados." }, { status: 400 }));
    render(<PublicRegistrationForm publicId="123e4567-e89b-42d3-a456-426614174000" />);
    await screen.findByRole("heading", { name: "Escalada 2030" });
    const user = await fillValidForm();
    await user.click(screen.getByRole("button", { name: "Revisar inscrição" }));
    await user.click(await screen.findByRole("button", { name: "Finalizar inscrição" }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Revise os dados informados"));
    expect(screen.queryByRole("heading", { name: "Inscrição recebida com sucesso." })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Revise antes de enviar" })).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
