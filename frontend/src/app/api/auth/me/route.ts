import { NextRequest, NextResponse } from "next/server";

import {
  applyAuthenticationResult,
  authenticatedDjangoRequest,
} from "../../../../lib/server/django-auth";
import { backendApiUrl } from "../../../../lib/server/sia-config";

export async function GET(request: NextRequest) {
  try {
    const result = await authenticatedDjangoRequest(request, (access) =>
      fetch(backendApiUrl(["auth", "me"]), {
        headers: { Authorization: `Bearer ${access}`, Accept: "application/json" },
        cache: "no-store",
        redirect: "manual",
      }),
    );
    const text = result.upstream.status === 204 ? null : await result.upstream.text();
    const headers = new Headers({ "Cache-Control": "private, no-store" });
    const contentType = result.upstream.headers.get("content-type");
    if (contentType) headers.set("Content-Type", contentType);
    const response = new NextResponse(text, { status: result.upstream.status, headers });
    applyAuthenticationResult(response, result);
    return response;
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível validar a sessão." },
      { status: 502, headers: { "Cache-Control": "private, no-store" } },
    );
  }
}
