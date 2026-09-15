const FIELD_LABELS: Record<string, string> = {
  nome: "Nome",
  email: "E-mail",
  telefone: "Telefone",
  cpf: "CPF",
  dataNascimento: "Data de nascimento",
  endereco: "Endereço",
  tipo_neurodivergente: "Tipo de neurodivergência",
  encontro: "Nome do Encontro",
  tipo: "Tipo do Encontro",
  data_referencia: "Data de início",
  data_exato: "Dias do Encontro",
  local: "Local",
  status: "Status",
};

export function formatDrfFormError(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object" || Array.isArray(body)) return fallback;

  const errors = body as Record<string, unknown>;
  const messages: string[] = [];
  for (const [field, value] of Object.entries(errors)) {
    const first = Array.isArray(value) ? value[0] : value;
    if (typeof first !== "string" || !first.trim()) continue;
    if (field === "detail" || field === "non_field_errors") messages.push(first);
    else messages.push(`${FIELD_LABELS[field] ?? field}: ${first}`);
  }
  return messages.length ? messages.join("\n") : fallback;
}

export async function readDrfFormError(response: Response, fallback: string) {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return fallback;
  }
  return formatDrfFormError(body, fallback);
}
