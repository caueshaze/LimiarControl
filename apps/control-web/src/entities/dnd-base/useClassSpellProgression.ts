import { useEffect, useMemo, useState } from "react";

import type { ClassSpellProgression } from "./spellProgressionBackendAdapter";
import { fetchFromBackend, fromLocalTables } from "./spellProgressionBackendAdapter";

const USE_BACKEND = import.meta.env.VITE_USE_BACKEND_PROGRESSION === "true";

export type SpellProgressionResult = {
  progression: ClassSpellProgression | null;
  source: "local" | "backend";
  isLoading: boolean;
  error: Error | null;
};

export function resolveProgressionState(
  localData: ClassSpellProgression | null,
  backendData: ClassSpellProgression | null,
  backendError: Error | null,
  useBackend: boolean,
  isLoading: boolean
): SpellProgressionResult {
  if (!useBackend) {
    return { progression: localData, source: "local", isLoading: false, error: null };
  }

  if (isLoading) {
    return { progression: localData, source: "local", isLoading: true, error: null };
  }

  if (backendError) {
    return { progression: localData, source: "local", isLoading: false, error: backendError };
  }

  if (backendData !== null) {
    return { progression: backendData, source: "backend", isLoading: false, error: null };
  }

  return { progression: localData, source: "local", isLoading: false, error: null };
}

export function useClassSpellProgression(
  className: string,
  level: number
): SpellProgressionResult {
  const localData = useMemo(
    () => fromLocalTables(className, level),
    [className, level]
  );

  const [backendData, setBackendData] = useState<ClassSpellProgression | null>(null);
  const [backendError, setBackendError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(USE_BACKEND);

  useEffect(() => {
    if (!USE_BACKEND) return;

    setBackendData(null);
    setBackendError(null);
    setIsLoading(true);

    let cancelled = false;

    fetchFromBackend(className, level)
      .then((data) => {
        if (cancelled) return;
        setBackendData(data);
        setBackendError(null);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setBackendData(null);
        setBackendError(err instanceof Error ? err : new Error(String(err)));
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [className, level]);

  return resolveProgressionState(localData, backendData, backendError, USE_BACKEND, isLoading);
}
