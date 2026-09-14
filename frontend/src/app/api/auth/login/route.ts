import { NextRequest, NextResponse } from "next/server";

import { setAuthCookies } from "../../../../lib/server/auth-cookies";
import { validateCsrf } from "../../../../lib/server/csrf";
import { isJwtPair } from "../../../../lib/server/django-auth";
import { backendApiUrl } from "../../../../lib/server/sia-config";

interface SafeSession {
  id: number;
  username: string;
  roles: string[];
  superuser: boolean;
}

function isSafeSession(value: unknown): value is SafeSession {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value && typeof value.id === "number" &&
    "username" in value && typeof value.username === "string" &&
    "roles" in value && Array.isArray(value.roles) && value.roles.every((role) => typeof role === "string") &&
    "superuser" in value && typeof value.superuser === "boolean"
  );
}

export async function POST(request: NextRequest) {
  const csrfFailure = validateCsrf(request);
  if (csrfFailure) return csrfFailure;

  let credentials: unknown;
  try {
    credentials = await request.json();
  } catch {
    return NextResponse.json({ detail: "Credenciais inválidas." }, { status: 400 });
  }
  if (
    typeof credentials !== "object" || credentials === null ||
    !("username" in credentials) || typeof credentials.username !== "string" ||
    !("password" in credentials) || typeof credentials.password !== "string" ||
    !credentials.username || !credentials.password
  ) {
    return NextResponse.json({ detail: "Credenciais inválidas." }, { status: 400 });
  }

  try {
    const tokenResponse = await fetch(backendApiUrl(["token"]), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ username: credentials.username, password: credentials.password }),
      cache: "no-store",
      redirect: "manual",
    });
    if (!tokenResponse.ok) {
      return NextResponse.json(
        { detail: "Usuário ou senha incorretos." },
        { status: 401, headers: { "Cache-Control": "private, no-store" } },
      );
    }

    const tokens: unknown = await tokenResponse.json();
    if (!isJwtPair(tokens)) throw new Error("Resposta de token inválida.");

    const meResponse = await fetch(backendApiUrl(["auth", "me"]), {
      headers: { Authorization: `Bearer ${tokens.access}`, Accept: "application/json" },
      cache: "no-store",
      redirect: "manual",
    });
    if (!meResponse.ok) throw new Error("Token emitido não validou a sessão.");
    const session: unknown = await meResponse.json();
    if (!isSafeSession(session)) throw new Error("Contrato de sessão inválido.");

    const response = NextResponse.json(session, {
      status: 200,
      headers: { "Cache-Control": "private, no-store" },
    });
    setAuthCookies(response, tokens);
    return response;
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível autenticar no SIA." },
      { status: 502, headers: { "Cache-Control": "private, no-store" } },
    );
  }
}
