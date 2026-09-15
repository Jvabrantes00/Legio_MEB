import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import {
  applyAuthenticationResult,
  resolveSession,
} from "./lib/server/django-auth";

export async function proxy(request: NextRequest) {
  const isLogin = request.nextUrl.pathname === "/login";

  let result;
  try {
    result = await resolveSession(request);
  } catch {
    // Sem resposta do Django, rotas privadas permanecem fechadas. Os cookies
    // não são apagados porque a indisponibilidade não prova sessão inválida.
    return isLogin
      ? NextResponse.next()
      : NextResponse.redirect(new URL("/login", request.url));
  }

  const sessionIsValid = result.upstream.status === 200;
  const identityIsValidButForbidden = result.upstream.status === 403;

  if (isLogin) {
    const response = sessionIsValid || identityIsValidButForbidden
      ? NextResponse.redirect(new URL("/", request.url))
      : NextResponse.next();
    applyAuthenticationResult(response, result);
    return response;
  }

  const response = sessionIsValid || identityIsValidButForbidden
    ? NextResponse.next()
    : NextResponse.redirect(new URL("/login", request.url));
  applyAuthenticationResult(response, result);
  return response;
}

export const config = {
  matcher: ["/", "/login", "/alpinistas/:path*", "/encontros/:path*"],
};
