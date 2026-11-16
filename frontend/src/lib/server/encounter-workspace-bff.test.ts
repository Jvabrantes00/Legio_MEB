import { describe, expect, it } from "vitest";

import { isAllowedEncounterWorkspaceRequest } from "./encounter-workspace-bff";
import { validateProxyPath } from "./sia-proxy";

const base = ["encontros", "12", "workspace"] as const;

describe("allowlist BFF do Workspace do Encontro", () => {
  it("permite GET no recurso exato de equipes", () => {
    const path = [...base, "equipes"];
    expect(isAllowedEncounterWorkspaceRequest("GET", path)).toBe(true);
    expect(() => validateProxyPath(path, new URLSearchParams(), "GET")).not.toThrow();
  });

  it.each(["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])(
    "nega %s em equipes",
    (method) => {
      const path = [...base, "equipes"];
      expect(isAllowedEncounterWorkspaceRequest(method, path)).toBe(false);
      expect(() => validateProxyPath(path, new URLSearchParams(), method)).toThrow();
    },
  );

  it.each(["encontro=1", "page=1", "url=https://example.test"])(
    "nega query em equipes: %s",
    (query) => {
      const path = [...base, "equipes"];
      const params = new URLSearchParams(query);
      expect(isAllowedEncounterWorkspaceRequest("GET", path, params)).toBe(false);
      expect(() => validateProxyPath(path, params, "GET")).toThrow();
    },
  );

  it.each([
    [...base, "equipes", "1"],
    [...base, "equipes", "roles"],
    [...base, "Equipes"],
    [...base, "EQUIPES"],
    [...base, "equipes-encontros"],
    ...["0", "01", "-1", "abc", "1.5"].map((id) => ["encontros", id, "workspace", "equipes"]),
  ])("nega caminho de equipes inválido: %j", (...path) => {
    expect(isAllowedEncounterWorkspaceRequest("GET", path)).toBe(false);
    expect(() => validateProxyPath(path, new URLSearchParams(), "GET")).toThrow();
  });

  it.each([
    [[...base]],
    [[...base, "capabilities"]],
    [[...base, "encontristas"]],
  ])("permite GET somente nos três recursos exatos", (path) => {
    expect(isAllowedEncounterWorkspaceRequest("GET", path)).toBe(true);
    expect(() => validateProxyPath(path, new URLSearchParams(), "GET")).not.toThrow();
  });

  it.each(["page=2", "search=ana", "situacao=APTO", "origem=INSCRICAO"]) (
    "repassa query conhecida: %s",
    (query) => {
      const params = new URLSearchParams(query);
      expect(isAllowedEncounterWorkspaceRequest("GET", [...base, "encontristas"], params)).toBe(true);
      expect(() => validateProxyPath([...base, "encontristas"], params, "GET")).not.toThrow();
    },
  );

  it.each(["POST", "PUT", "PATCH", "DELETE"])("nega método %s", (method) => {
    expect(isAllowedEncounterWorkspaceRequest(method, base)).toBe(false);
    expect(() => validateProxyPath(base, new URLSearchParams(), method)).toThrow();
  });

  it("permite somente os métodos do singleton de configuração", () => {
    const path = [...base, "inscricoes", "configuracao"];
    for (const method of ["GET", "POST", "PATCH"]) {
      expect(isAllowedEncounterWorkspaceRequest(method, path)).toBe(true);
      expect(() => validateProxyPath(path, new URLSearchParams(), method)).not.toThrow();
    }
    for (const method of ["PUT", "DELETE"]) {
      expect(isAllowedEncounterWorkspaceRequest(method, path)).toBe(false);
    }
    expect(isAllowedEncounterWorkspaceRequest("GET", [...path, "1"])).toBe(false);
    expect(isAllowedEncounterWorkspaceRequest(
      "GET",
      path,
      new URLSearchParams("url=https://example.test"),
    )).toBe(false);
  });

  it.each([
    [["encontros", "12", "workspace", "qualquer"]],
    [["encontros", "12", "workspace", "..", "encontristas"]],
    [["https://evil.example", "encontros", "12", "workspace"]],
    [["encontros", "12", "workspace", "encontristas", "extra"]],
  ])("nega path arbitrário/absoluto/traversal: %j", (path) => {
    expect(isAllowedEncounterWorkspaceRequest("GET", path)).toBe(false);
    expect(() => validateProxyPath(path, new URLSearchParams(), "GET")).toThrow();
  });

  it("nega wildcard e parâmetros não allowlisted", () => {
    expect(isAllowedEncounterWorkspaceRequest("GET", ["encontros", "12", "workspace", "*"])).toBe(false);
    expect(() => validateProxyPath(
      [...base, "encontristas"],
      new URLSearchParams("fields=cpf&token=jwt"),
      "GET",
    )).toThrow();
  });

  it("não permite query em summary/capabilities nem página inválida", () => {
    expect(isAllowedEncounterWorkspaceRequest("GET", base, new URLSearchParams("page=1"))).toBe(false);
    expect(isAllowedEncounterWorkspaceRequest("GET", [...base, "capabilities"], new URLSearchParams("search=x"))).toBe(false);
    expect(isAllowedEncounterWorkspaceRequest("GET", [...base, "encontristas"], new URLSearchParams("page=0"))).toBe(false);
  });
});
