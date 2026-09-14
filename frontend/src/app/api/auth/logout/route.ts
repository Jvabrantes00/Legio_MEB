import { NextRequest, NextResponse } from "next/server";

import { clearAuthCookies, clearCsrfCookie } from "../../../../lib/server/auth-cookies";
import { validateCsrf } from "../../../../lib/server/csrf";

export function POST(request: NextRequest) {
  const csrfFailure = validateCsrf(request);
  if (csrfFailure) return csrfFailure;

  const response = new NextResponse(null, {
    status: 204,
    headers: { "Cache-Control": "private, no-store" },
  });
  clearAuthCookies(response);
  clearCsrfCookie(response);
  return response;
}
