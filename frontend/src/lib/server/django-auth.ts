import { createHash } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  clearAuthCookies,
  REFRESH_COOKIE,
  setAuthCookies,
} from "./auth-cookies";
import { backendApiUrl } from "./sia-config";

type SendAuthenticatedRequest = (access: string, attempt: 0 | 1) => Promise<Response>;

export interface AuthenticatedResult {
  upstream: Response;
  newAccess?: string;
  clearAuthentication?: boolean;
}

const refreshInFlight = new Map<string, Promise<string | null>>();

function looksLikeJwt(value: unknown): value is string {
  return typeof value === "string" && value.split(".").length === 3;
}

async function requestNewAccess(refresh: string): Promise<string | null> {
  try {
    const response = await fetch(backendApiUrl(["token", "refresh"]), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
      redirect: "manual",
    });
    if (!response.ok) return null;
    const payload: unknown = await response.json();
    if (
      typeof payload !== "object" ||
      payload === null ||
      !("access" in payload) ||
      !looksLikeJwt(payload.access)
    ) {
      return null;
    }
    return payload.access;
  } catch {
    return null;
  }
}

function refreshAccess(refresh: string): Promise<string | null> {
  const key = createHash("sha256").update(refresh).digest("hex");
  const existing = refreshInFlight.get(key);
  if (existing) return existing;

  const pending = requestNewAccess(refresh).finally(() => refreshInFlight.delete(key));
  refreshInFlight.set(key, pending);
  return pending;
}

function unauthorizedResponse(): Response {
  return Response.json({ detail: "Sessão inválida ou expirada." }, { status: 401 });
}

export async function authenticatedDjangoRequest(
  request: NextRequest,
  send: SendAuthenticatedRequest,
): Promise<AuthenticatedResult> {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;

  if (!access) {
    if (!refresh) {
      return { upstream: unauthorizedResponse(), clearAuthentication: true };
    }
    const newAccess = await refreshAccess(refresh);
    if (!newAccess) {
      return { upstream: unauthorizedResponse(), clearAuthentication: true };
    }
    const upstream = await send(newAccess, 0);
    return {
      upstream,
      newAccess,
      clearAuthentication: upstream.status === 401,
    };
  }

  const firstResponse = await send(access, 0);
  if (firstResponse.status !== 401) {
    return { upstream: firstResponse };
  }
  if (!refresh) {
    return { upstream: firstResponse, clearAuthentication: true };
  }

  const newAccess = await refreshAccess(refresh);
  if (!newAccess) {
    return { upstream: unauthorizedResponse(), clearAuthentication: true };
  }

  const retryResponse = await send(newAccess, 1);
  return {
    upstream: retryResponse,
    newAccess,
    clearAuthentication: retryResponse.status === 401,
  };
}

export function applyAuthenticationResult(
  response: NextResponse,
  result: AuthenticatedResult,
) {
  if (result.clearAuthentication) {
    clearAuthCookies(response);
  } else if (result.newAccess) {
    setAuthCookies(response, { access: result.newAccess });
  }
}

export function isJwtPair(value: unknown): value is { access: string; refresh: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    "access" in value &&
    "refresh" in value &&
    looksLikeJwt(value.access) &&
    looksLikeJwt(value.refresh)
  );
}
