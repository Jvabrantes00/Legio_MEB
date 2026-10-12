import { describe, expect, it } from "vitest";

import {
  createPreEncounterPdfResponse,
  preEncounterPdfKind,
} from "./pre-encounter-pdf";
import { validateProxyPath } from "./sia-proxy";

const operational = ["encontros", "12", "pre-encontro", "pdf", "operacional"] as const;
const care = ["encontros", "12", "pre-encontro", "pdf", "cuidados"] as const;

describe("BFF explícito de PDFs do Pré-Encontro", () => {
  it("permite somente GET nos dois downloads exatos", () => {
    expect(preEncounterPdfKind("GET", operational)).toBe("operational");
    expect(preEncounterPdfKind("GET", care)).toBe("care");
    expect(() => validateProxyPath(operational, new URLSearchParams(), "GET")).not.toThrow();
    expect(() => validateProxyPath(care, new URLSearchParams(), "GET")).not.toThrow();
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      expect(preEncounterPdfKind(method, operational)).toBeNull();
      expect(() => validateProxyPath(operational, new URLSearchParams(), method)).toThrow();
    }
  });

  it.each([
    [[...operational, "extra"]],
    [["encontros", "12", "pre-encontro", "pdf", "arbitrario"]],
    [["encontros", "../12", "pre-encontro", "pdf", "operacional"]],
    [["https://evil.example", "12", "pre-encontro", "pdf", "operacional"]],
  ])("nega path extra, arbitrário, traversal e URL absoluta: %j", (path) => {
    expect(preEncounterPdfKind("GET", path)).toBeNull();
    expect(() => validateProxyPath(path, new URLSearchParams(), "GET")).toThrow();
  });

  it("repassa bytes e headers privados sem expor JWT", async () => {
    const bytes = new TextEncoder().encode("%PDF-1.7");
    const response = createPreEncounterPdfResponse(new Response(bytes, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": "attachment; filename=pre-encontro-operacional.pdf",
        Authorization: "Bearer segredo-do-servidor",
      },
    }));

    expect(new TextDecoder().decode(await response.arrayBuffer())).toBe("%PDF-1.7");
    expect(response.headers.get("content-type")).toBe("application/pdf");
    expect(response.headers.get("content-disposition")).toContain("pre-encontro-operacional.pdf");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.has("authorization")).toBe(false);
  });
});
