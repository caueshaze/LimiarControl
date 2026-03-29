import { env } from "../../app/config";

const stripTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const isLocalDevelopmentApi = (baseUrl: string) => {
  if (!import.meta.env.DEV) {
    return false;
  }

  try {
    const parsedUrl = new URL(baseUrl);
    return (
      (parsedUrl.hostname === "localhost" || parsedUrl.hostname === "127.0.0.1") &&
      parsedUrl.port === "3000" &&
      stripTrailingSlash(parsedUrl.pathname) === "/api"
    );
  } catch {
    return false;
  }
};

export const getApiBaseUrl = () => {
  const configuredBaseUrl = env.VITE_API_BASE_URL?.trim() ?? "";
  if (!configuredBaseUrl) {
    return "";
  }

  const normalizedBaseUrl = stripTrailingSlash(configuredBaseUrl);
  if (isLocalDevelopmentApi(normalizedBaseUrl)) {
    return "/api";
  }

  return normalizedBaseUrl;
};

export const buildApiUrl = (path: string) => {
  const baseUrl = getApiBaseUrl();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
};
