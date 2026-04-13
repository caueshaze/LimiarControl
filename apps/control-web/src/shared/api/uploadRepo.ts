import { getToken } from "../auth/tokenStore";
import { buildApiUrl, getApiBaseUrl } from "./apiBaseUrl";

export type UploadImageResult = { url: string };
export type UploadImageKind = "campaign_map" | "campaign_entity";

type UploadImageParams = {
  file: File;
  kind: UploadImageKind;
  campaignId: string;
  entityId?: string | null;
};

export const uploadRepo = {
  uploadImage: async ({
    file,
    kind,
    campaignId,
    entityId,
  }: UploadImageParams): Promise<UploadImageResult> => {
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
    body.append("kind", kind);
    body.append("campaignId", campaignId);
    if (entityId) {
      body.append("entityId", entityId);
    }

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
          ? "Unable to reach the API. Make sure the current app origin is serving /api or that the backend is running on http://localhost:8000."
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
