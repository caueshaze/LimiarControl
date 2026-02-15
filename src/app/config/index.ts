export const env = {
  VITE_APP_ENV: import.meta.env.VITE_APP_ENV ?? "development",
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL ?? "",
  VITE_ENABLE_MUSIC: import.meta.env.VITE_ENABLE_MUSIC === "true",
  VITE_ENABLE_MAPS: import.meta.env.VITE_ENABLE_MAPS === "true",
};
export { APP_NAME } from "./appConfig";
