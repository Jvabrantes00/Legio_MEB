import type { NextResponse } from "next/server";

import { getSiaServerConfig } from "./sia-config";

export const ACCESS_COOKIE = "sia_access";
export const REFRESH_COOKIE = "sia_refresh";
export const CSRF_COOKIE = "sia_csrf";
export const LEGACY_ACCESS_COOKIE = "sia_token";

export const ACCESS_MAX_AGE = 15 * 60;
export const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

function baseCookieOptions(httpOnly: boolean) {
  return {
    httpOnly,
    secure: getSiaServerConfig().secureCookies,
    sameSite: "lax" as const,
    path: "/",
  };
}

export function setAuthCookies(
  response: NextResponse,
  tokens: { access: string; refresh?: string },
) {
  response.cookies.set(ACCESS_COOKIE, tokens.access, {
    ...baseCookieOptions(true),
    maxAge: ACCESS_MAX_AGE,
  });
  if (tokens.refresh) {
    response.cookies.set(REFRESH_COOKIE, tokens.refresh, {
      ...baseCookieOptions(true),
      maxAge: REFRESH_MAX_AGE,
    });
  }
  clearCookie(response, LEGACY_ACCESS_COOKIE, true);
}

function clearCookie(response: NextResponse, name: string, httpOnly: boolean) {
  response.cookies.set(name, "", {
    ...baseCookieOptions(httpOnly),
    maxAge: 0,
    expires: new Date(0),
  });
}

export function clearAuthCookies(response: NextResponse) {
  clearCookie(response, ACCESS_COOKIE, true);
  clearCookie(response, REFRESH_COOKIE, true);
  clearCookie(response, LEGACY_ACCESS_COOKIE, true);
}

export function clearCsrfCookie(response: NextResponse) {
  clearCookie(response, CSRF_COOKIE, false);
}

export function setCsrfCookie(response: NextResponse, token: string) {
  response.cookies.set(CSRF_COOKIE, token, {
    ...baseCookieOptions(false),
    maxAge: REFRESH_MAX_AGE,
  });
}
