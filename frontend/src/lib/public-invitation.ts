import { ensureCsrfToken } from "./sia-api";

export type PublicInvitationState =
  | "pendente"
  | "confirmado"
  | "recusado"
  | "expirado"
  | "suspenso"
  | "indisponivel";

export interface PublicInvitation {
  estado: PublicInvitationState;
  titulo_encontro: string;
  datas_encontro: string[];
  prazo_resposta: string;
  finalidade: "participar";
  pode_responder: boolean;
  mensagem: string;
}

export type PublicInvitationResult =
  | { success: true; convite: PublicInvitation }
  | { success: false; status: number; message: string };

export type PublicInvitationAction = "validar" | "confirmar" | "recusar";

const GENERIC_INVALID = "Não foi possível validar este convite. Confira os dados ou procure a equipe de Fichas.";

export async function submitPublicInvitation(
  token: string,
  birthDate: string,
  action: PublicInvitationAction,
): Promise<PublicInvitationResult> {
  let response: Response;
  try {
    const csrfToken = await ensureCsrfToken();
    response = await fetch("/api/public/convites/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ token, data_nascimento: birthDate, acao: action }),
      cache: "no-store",
    });
  } catch {
    return { success: false, status: 502, message: "Serviço temporariamente indisponível." };
  }
  if (response.ok) {
    const convite: PublicInvitation = await response.json();
    return { success: true, convite };
  }
  const messages: Record<number, string> = {
    404: GENERIC_INVALID,
    429: "Muitas tentativas. Tente novamente mais tarde.",
    502: "Serviço temporariamente indisponível.",
  };
  return {
    success: false,
    status: response.status,
    message: messages[response.status] ?? "Não foi possível concluir esta operação.",
  };
}
