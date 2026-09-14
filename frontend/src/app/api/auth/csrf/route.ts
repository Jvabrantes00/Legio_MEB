import { NextRequest, NextResponse } from "next/server";

import { CSRF_COOKIE, setCsrfCookie } from "../../../../lib/server/auth-cookies";
import { generateCsrfToken } from "../../../../lib/server/csrf";

export function GET(request: NextRequest) {
  const response = new NextResponse(null, {
    status: 204,
    headers: { "Cache-Control": "private, no-store" },
  });
  if (!request.cookies.get(CSRF_COOKIE)?.value) {
    setCsrfCookie(response, generateCsrfToken());
  }
  return response;
}
