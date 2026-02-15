const TOKEN_KEY = "limiar:authToken";

let cachedToken: string | null | undefined;

const readStorageToken = () => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(TOKEN_KEY);
};

export const getToken = () => {
  if (cachedToken === undefined) {
    cachedToken = readStorageToken();
  }
  return cachedToken;
};

export const setToken = (token: string) => {
  cachedToken = token;
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(TOKEN_KEY, token);
};

export const clearToken = () => {
  cachedToken = null;
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(TOKEN_KEY);
};
