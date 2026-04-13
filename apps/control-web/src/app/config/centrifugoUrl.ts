type BrowserLocationLike = {
  hostname: string;
  protocol: string;
};

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

const isLoopbackHost = (host: string) => LOOPBACK_HOSTS.has(host);

const normalizeLoopbackHost = (host: string) =>
  isLoopbackHost(host) ? "127.0.0.1" : host;

export const resolveCentrifugoUrl = (
  rawUrl: string | undefined,
  locationLike: BrowserLocationLike | undefined = typeof window !== "undefined"
    ? window.location
    : undefined,
) => {
  const runtimeHost = locationLike?.hostname?.trim() || "127.0.0.1";
  const runtimeProtocol = locationLike?.protocol === "https:" ? "wss:" : "ws:";
  const fallbackHost = normalizeLoopbackHost(runtimeHost);
  const fallbackUrl =
    `${runtimeProtocol}//${fallbackHost}:8001/connection/websocket`;
  const baseUrl = rawUrl?.trim() || fallbackUrl;

  let resolved: URL;
  try {
    resolved = new URL(baseUrl);
  } catch {
    return baseUrl;
  }

  if (isLoopbackHost(resolved.hostname)) {
    resolved.hostname = fallbackHost;
  }

  if (locationLike?.protocol === "https:" && resolved.protocol === "ws:") {
    resolved.protocol = "wss:";
  }

  return resolved.toString();
};
