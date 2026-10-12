import { NextResponse } from "next/server";

const POSITIVE_INTEGER = /^[1-9]\d*$/;

function isId(value: string | undefined): boolean {
  return Boolean(value && POSITIVE_INTEGER.test(value));
}

export type PreEncounterMediaOperation = "preview" | "upload" | "associate";

export function preEncounterMediaOperation(
  method: string,
  path: readonly string[],
): PreEncounterMediaOperation | null {
  if (
    path.length < 6
    || path[0] !== "encontros"
    || !isId(path[1])
    || path[2] !== "pre-encontro"
    || path[3] !== "atendimentos"
    || !isId(path[4])
    || path[5] !== "foto"
  ) return null;

  if (path.length === 6 && method === "GET") return "preview";
  if (path.length === 6 && method === "PUT") return "upload";
  if (path.length === 7 && path[6] === "usar-na-pessoa" && method === "POST") {
    return "associate";
  }
  return null;
}

export function createPreEncounterMediaResponse(upstream: Response): NextResponse {
  const headers = new Headers({
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
  });
  for (const name of ["content-type", "content-disposition", "content-length"]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new NextResponse(upstream.body, { status: upstream.status, headers });
}
