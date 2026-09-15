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
  rotatedTokens?: JwtPair;
  clearAuthentication?: boolean;
}

export interface JwtPair {
  access: string;
  refresh: string;
}

const refreshInFlight = new Map<string, Promise<JwtPair | null>>();
const REFRESH_COORDINATION_GRACE_MS = 10_000;

function looksLikeJwt(value: unknown): value is string {
  return typeof value === "string" && value.split(".").length === 3;
}

async function requestRotatedTokens(refresh: string): Promise<JwtPair | null> {
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
    return isJwtPair(payload) ? payload : null;
  } catch {
    return null;
  }
}

function rotateRefresh(refresh: string): Promise<JwtPair | null> {
  const key = createHash("sha256").update(refresh).digest("hex");
  const existing = refreshInFlight.get(key);
  if (existing) return existing;

  const pending = requestRotatedTokens(refresh);
  refreshInFlight.set(key, pending);
  void pending.finally(() => {
    const cleanupTimer = setTimeout(() => {
      if (refreshInFlight.get(key) === pending) refreshInFlight.delete(key);
    }, REFRESH_COORDINATION_GRACE_MS);
    cleanupTimer.unref();
  });
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
    const rotatedTokens = await rotateRefresh(refresh);
    if (!rotatedTokens) {
      return { upstream: unauthorizedResponse(), clearAuthentication: true };
    }
    const upstream = await send(rotatedTokens.access, 1);
    return {
      upstream,
      rotatedTokens,
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

  const rotatedTokens = await rotateRefresh(refresh);
  if (!rotatedTokens) {
    return { upstream: unauthorizedResponse(), clearAuthentication: true };
  }

  const retryResponse = await send(rotatedTokens.access, 1);
  return {
    upstream: retryResponse,
    rotatedTokens,
    clearAuthentication: retryResponse.status === 401,
  };
}

export function applyAuthenticationResult(
  response: NextResponse,
  result: AuthenticatedResult,
) {
  if (result.clearAuthentication) {
    clearAuthCookies(response);
  } else if (result.rotatedTokens) {
    setAuthCookies(response, result.rotatedTokens);
  }
}

export async function resolveSession(request: NextRequest): Promise<AuthenticatedResult> {
  return authenticatedDjangoRequest(request, (access) =>
    fetch(backendApiUrl(["auth", "me"]), {
      headers: { Authorization: `Bearer ${access}`, Accept: "application/json" },
      cache: "no-store",
      redirect: "manual",
    }),
  );
}

export function isJwtPair(value: unknown): value is JwtPair {
  return (
    typeof value === "object" &&
    value !== null &&
    "access" in value &&
    "refresh" in value &&
    looksLikeJwt(value.access) &&
    looksLikeJwt(value.refresh)
  );
}
