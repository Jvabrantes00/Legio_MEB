import { NextResponse } from "next/server";

const POSITIVE_INTEGER = /^[1-9]\d*$/;

export type PreEncounterPdfKind = "operational" | "care";

export function preEncounterPdfKind(
  method: string,
  path: readonly string[],
): PreEncounterPdfKind | null {
  if (
    method !== "GET"
    || path.length !== 5
    || path[0] !== "encontros"
    || !POSITIVE_INTEGER.test(path[1] ?? "")
    || path[2] !== "pre-encontro"
    || path[3] !== "pdf"
  ) return null;
  if (path[4] === "operacional") return "operational";
  if (path[4] === "cuidados") return "care";
  return null;
}

export function createPreEncounterPdfResponse(upstream: Response): NextResponse {
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
