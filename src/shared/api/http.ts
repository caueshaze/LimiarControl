import { env } from "../../app/config";
import { getToken } from "../auth/tokenStore";

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

export type HttpError = {
  status: number;
  message: string;
  data?: unknown;
};

const request = async <T>(method: HttpMethod, path: string, body?: unknown) => {
  const baseUrl = env.VITE_API_BASE_URL;
  if (!baseUrl) {
    throw { status: 0, message: "Missing API base URL" } satisfies HttpError;
  }

  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let message = response.statusText;
    let errorData: unknown;
    try {
      errorData = await response.json();
      const d = errorData as { error?: string; message?: string; detail?: unknown };
      if (typeof d?.detail === "string") message = d.detail;
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
