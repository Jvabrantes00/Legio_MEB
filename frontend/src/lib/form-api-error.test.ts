import { describe, expect, it } from "vitest";
import { errorMessage, formatDrfFormError, readApiError, readDrfFormError } from "./form-api-error";

describe("erros de validação dos formulários", () => {
  it.each([
    ["cpf", "CPF"],
    ["email", "E-mail"],
    ["telefone", "Telefone"],
    ["dataNascimento", "Data de nascimento"],
  ])("mostra o campo %s da resposta DRF", (field, label) => {
    expect(formatDrfFormError({ [field]: ["Valor inválido."] }, "Erro"))
      .toBe(`${label}: Valor inválido.`);
  });

  it("lê resposta HTTP 400 sem esconder a mensagem de CPF", async () => {
    const response = Response.json({ cpf: ["CPF inválido."] }, { status: 400 });
    expect(await readDrfFormError(response, "Erro"))
      .toBe("CPF: CPF inválido.");
  });

  it("usa mensagem genérica quando a resposta não é JSON", async () => {
    expect(await readDrfFormError(new Response("falha", { status: 500 }), "Erro"))
      .toBe("Erro");
  });

  it.each([
    [401, "Sua sessão expirou. Entre novamente."],
    [403, "Você não tem permissão para realizar esta ação."],
    [404, "O recurso solicitado não foi encontrado."],
  ])("preserva a semântica do status HTTP %s", async (status, message) => {
    expect(await readApiError(new Response(null, { status }), "Erro")).toBe(message);
  });

  it("prefere o detalhe DRF à mensagem baseada no status", async () => {
    const response = Response.json({ detail: "Recurso de outro encontro." }, { status: 404 });
    expect(await readApiError(response, "Erro")).toBe("Recurso de outro encontro.");
  });

  it("normaliza somente instâncias de Error", () => {
    expect(errorMessage(new Error("Falhou"), "Erro")).toBe("Falhou");
    expect(errorMessage({ message: "não confiável" }, "Erro")).toBe("Erro");
  });
});
