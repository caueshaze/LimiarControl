import { getToken } from "../auth/tokenStore";
import { buildApiUrl, getApiBaseUrl } from "./apiBaseUrl";

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

export type HttpError = {
  status: number;
  message: string;
  data?: unknown;
};

const formatDetailMessage = (detail: unknown) => {
  if (typeof detail === "string") {
    return detail;
  }
  if (!detail || typeof detail !== "object") {
    return null;
  }

  const typedDetail = detail as {
    code?: string;
    message?: string;
    players?: Array<{ displayName?: string | null; userId?: string | null }>;
  };

  if (typeof typedDetail.message === "string") {
    return typedDetail.message;
  }

  if (
    typedDetail.code === "missing_character_sheets" &&
    Array.isArray(typedDetail.players) &&
    typedDetail.players.length > 0
  ) {
    const players = typedDetail.players
      .map((player) => player.displayName || player.userId)
      .filter((player): player is string => Boolean(player));
    if (players.length > 0) {
      return `Nao e possivel iniciar a sessao. Os seguintes jogadores ainda nao possuem ficha: ${players.join(", ")}.`;
    }
  }

  return null;
};

const request = async <T>(method: HttpMethod, path: string, body?: unknown) => {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    throw { status: 0, message: "Missing API base URL" } satisfies HttpError;
  }

  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let response: Response;
  try {
    response = await fetch(buildApiUrl(path), {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    const err = new Error(
      baseUrl === "/api"
        ? "Unable to reach the API. Make sure the current app origin is serving /api or that the backend is running on http://localhost:3000."
        : `Unable to reach the API at ${baseUrl}.`,
    ) as Error & HttpError;
    err.status = 0;
    err.data = error;
    throw err;
  }

  if (!response.ok) {
    let message = response.statusText;
    let errorData: unknown;
    try {
      errorData = await response.json();
      const d = errorData as { error?: string; message?: string; detail?: unknown };
      const detailMessage = formatDetailMessage(d?.detail);
      if (detailMessage) message = detailMessage;
      else if (d?.error) message = d.error as string;
      else if (d?.message) message = d.message as string;
    } catch {
      // ignore JSON errors
    }
    const err = new Error(message) as Error & HttpError;
    err.status = response.status;
    err.data = errorData;
    throw err;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
};

export const http = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
};
