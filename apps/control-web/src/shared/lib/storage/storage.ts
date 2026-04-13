export type StorageEnvelope<T> = {
  version: number;
  data: T;
};

const safeJsonParse = <T>(value: string): T | null => {
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
};

export const storage = {
  get<T>(key: string): StorageEnvelope<T> | null {
    if (typeof window === "undefined") {
      return null;
    }

    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }

    return safeJsonParse<StorageEnvelope<T>>(raw);
  },
  set<T>(key: string, value: StorageEnvelope<T>) {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(key, JSON.stringify(value));
  },
  remove(key: string) {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.removeItem(key);
  },
};
