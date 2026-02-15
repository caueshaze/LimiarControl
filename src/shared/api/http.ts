import { getToken } from "../auth/tokenStore";

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

export type HttpError = {
  status: number;
  message: string;
};

const baseUrl = import.meta.env.VITE_API_BASE_URL;

const request = async <T>(method: HttpMethod, path: string, body?: unknown) => {
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
    try {
      const data = (await response.json()) as {
        error?: string;
        message?: string;
      };
      if (data?.error) {
        message = data.error;
      } else if (data?.message) {
        message = data.message;
      }
    } catch {
      // ignore JSON errors
    }
    throw { status: response.status, message } satisfies HttpError;
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
