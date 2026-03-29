import { getToken } from "../auth/tokenStore";
import { buildApiUrl, getApiBaseUrl } from "./apiBaseUrl";

export type UploadImageResult = { url: string };

export const uploadRepo = {
  uploadImage: async (file: File): Promise<UploadImageResult> => {
    const baseUrl = getApiBaseUrl();
    if (!baseUrl) {
      throw new Error("Missing API base URL");
    }

    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const body = new FormData();
    body.append("file", file);

    let response: Response;
    try {
      response = await fetch(buildApiUrl("/upload/image"), {
        method: "POST",
        headers,
        body,
      });
    } catch {
      throw new Error(
        baseUrl === "/api"
          ? "Unable to reach the API. Make sure the backend is running on http://localhost:3000."
          : `Unable to reach the API at ${baseUrl}.`,
      );
    }

    if (!response.ok) {
      let message = response.statusText;
      try {
        const data = (await response.json()) as { detail?: string };
        if (data.detail) message = data.detail;
      } catch {
        // ignore
      }
      throw new Error(message);
    }

    return (await response.json()) as UploadImageResult;
  },
};
