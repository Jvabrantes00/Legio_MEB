const LOCAL_HTTP_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

export function allowedDevOriginsFromAppOrigin(value: string | undefined): string[] {
  if (!value) return [];

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return [];
  }

  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash ||
    url.hostname.includes("*") ||
    (url.protocol === "http:" && !LOCAL_HTTP_HOSTS.has(url.hostname))
  ) {
    return [];
  }

  return [url.hostname];
}
