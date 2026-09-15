import { NextRequest, NextResponse } from "next/server";

import {
  clearAuthCookies,
  clearCsrfCookie,
  REFRESH_COOKIE,
} from "../../../../lib/server/auth-cookies";
import { validateCsrf } from "../../../../lib/server/csrf";
import { backendApiUrl } from "../../../../lib/server/sia-config";

export async function POST(request: NextRequest) {
  const csrfFailure = validateCsrf(request);
  if (csrfFailure) return csrfFailure;

  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  let revocation = refresh ? "not-confirmed" : "not-present";
  if (refresh) {
    try {
      const upstream = await fetch(backendApiUrl(["token", "blacklist"]), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ refresh }),
        cache: "no-store",
        redirect: "manual",
      });
      if (upstream.ok) revocation = "confirmed";
    } catch {
      revocation = "unavailable";
    }
  }

  const response = new NextResponse(null, {
    status: 204,
    headers: {
      "Cache-Control": "private, no-store",
      "X-SIA-Refresh-Revocation": revocation,
    },
  });
  clearAuthCookies(response);
  clearCsrfCookie(response);
  return response;
}
