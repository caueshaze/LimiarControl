const DEFAULT_SESSION_ID = "demo-session";

function readSearchParam(name: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return new URLSearchParams(window.location.search).get(name);
}

export function getMapSessionId(): string {
  const sessionId = readSearchParam("sessionId");
  return sessionId && sessionId.trim().length > 0 ? sessionId.trim() : DEFAULT_SESSION_ID;
}

export function isEmbeddedMapView(): boolean {
  const embedded = readSearchParam("embedded");
  return embedded === "1" || embedded === "true";
}

export { DEFAULT_SESSION_ID };
