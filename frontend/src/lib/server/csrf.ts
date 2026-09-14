import { randomBytes, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import { CSRF_COOKIE } from "./auth-cookies";
import { getSiaServerConfig } from "./sia-config";

export const CSRF_HEADER = "x-csrf-token";
export const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function generateCsrfToken(): string {
  return randomBytes(32).toString("base64url");
}

function constantTimeEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  return (
    leftBuffer.length === rightBuffer.length &&
    timingSafeEqual(leftBuffer, rightBuffer)
  );
}

export function validateCsrf(request: NextRequest): NextResponse | null {
  if (!MUTATING_METHODS.has(request.method.toUpperCase())) {
    return null;
  }

  const origin = request.headers.get("origin");
  const cookieToken = request.cookies.get(CSRF_COOKIE)?.value;
  const headerToken = request.headers.get(CSRF_HEADER);
  const expectedOrigin = getSiaServerConfig().appOrigin;

  if (
    origin !== expectedOrigin ||
    !cookieToken ||
    !headerToken ||
    !constantTimeEqual(cookieToken, headerToken)
  ) {
    return NextResponse.json(
      { detail: "Requisição recusada pela proteção CSRF." },
      { status: 403, headers: { "Cache-Control": "private, no-store" } },
    );
  }
  return null;
}
