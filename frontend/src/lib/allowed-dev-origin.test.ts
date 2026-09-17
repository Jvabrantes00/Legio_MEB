import { describe, expect, it } from "vitest";

import { allowedDevOriginsFromAppOrigin } from "./allowed-dev-origin";

describe("allowedDevOriginsFromAppOrigin", () => {
  it("permite somente o hostname da origem HTTPS configurada", () => {
    expect(allowedDevOriginsFromAppOrigin("https://tunnel.example.test:443")).toEqual([
      "tunnel.example.test",
    ]);
  });

  it("preserva HTTP apenas para desenvolvimento local explícito", () => {
    expect(allowedDevOriginsFromAppOrigin("http://localhost:3000")).toEqual(["localhost"]);
    expect(allowedDevOriginsFromAppOrigin("http://tunnel.example.test")).toEqual([]);
  });

  it("não permite URL inválida, caminho, credenciais ou wildcard", () => {
    expect(allowedDevOriginsFromAppOrigin(undefined)).toEqual([]);
    expect(allowedDevOriginsFromAppOrigin("not a URL")).toEqual([]);
    expect(allowedDevOriginsFromAppOrigin("https://tunnel.example.test/path")).toEqual([]);
    expect(allowedDevOriginsFromAppOrigin("https://user:pass@tunnel.example.test")).toEqual([]);
    expect(allowedDevOriginsFromAppOrigin("https://*.example.test")).toEqual([]);
  });
});
