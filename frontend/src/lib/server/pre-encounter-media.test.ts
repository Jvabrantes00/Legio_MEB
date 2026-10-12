import { describe, expect, it } from "vitest";

import {
  createPreEncounterMediaResponse,
  preEncounterMediaOperation,
} from "./pre-encounter-media";
import { validateProxyPath } from "./sia-proxy";

const photo = ["encontros", "12", "pre-encontro", "atendimentos", "34", "foto"] as const;

describe("BFF explícito de mídia do Pré-Encontro", () => {
  it("permite somente preview, upload e associação nos paths exatos", () => {
    expect(preEncounterMediaOperation("GET", photo)).toBe("preview");
    expect(preEncounterMediaOperation("PUT", photo)).toBe("upload");
    expect(preEncounterMediaOperation("POST", [...photo, "usar-na-pessoa"])).toBe("associate");
    for (const [method, path] of [
      ["POST", photo],
      ["PATCH", photo],
      ["DELETE", photo],
      ["GET", [...photo, "usar-na-pessoa"]],
      ["POST", [...photo, "usar-na-pessoa", "extra"]],
    ] as const) {
      expect(preEncounterMediaOperation(method, path)).toBeNull();
      expect(() => validateProxyPath(path, new URLSearchParams(), method)).toThrow();
    }
  });

  it.each([
    [["encontros", "12", "pre-encontro", "atendimentos", "../34", "foto"]],
    [["https://evil.example", "12", "pre-encontro", "atendimentos", "34", "foto"]],
    [["media", "pre_encontros", "fotos", "segredo"]],
    [[...photo, "pre_encontros/fotos/chave"]],
  ])("nega traversal, URL absoluta, /media e storage key arbitrária: %j", (path) => {
    expect(preEncounterMediaOperation("GET", path)).toBeNull();
    expect(() => validateProxyPath(path, new URLSearchParams(), "GET")).toThrow();
  });

  it("repassa binário e headers seguros sem expor autenticação", async () => {
    const bytes = new Uint8Array([137, 80, 78, 71]);
    const response = createPreEncounterMediaResponse(new Response(bytes, {
      status: 200,
      headers: {
        "Content-Type": "image/png",
        "Content-Disposition": "inline; filename=foto-pre-encontro",
        Authorization: "Bearer segredo-do-servidor",
      },
    }));

    expect(new Uint8Array(await response.arrayBuffer())).toEqual(bytes);
    expect(response.headers.get("content-type")).toBe("image/png");
    expect(response.headers.get("content-disposition")).toContain("foto-pre-encontro");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.has("authorization")).toBe(false);
  });

  it("permite multipart somente no upload exato", () => {
    expect(() => validateProxyPath(photo, new URLSearchParams(), "PUT")).not.toThrow();
    expect(() => validateProxyPath([...photo, "destino"], new URLSearchParams(), "PUT")).toThrow();
    expect(() => validateProxyPath([...photo, "usar-na-pessoa"], new URLSearchParams(), "POST")).not.toThrow();
  });
});
