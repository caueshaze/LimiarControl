import type { NavigateFunction } from "react-router-dom";

export const canNavigateBack = () => {
  if (typeof window === "undefined") {
    return false;
  }

  const historyState = window.history.state as { idx?: number } | null;
  return typeof historyState?.idx === "number" && historyState.idx > 0;
};

type NavigateBackOptions = {
  fallbackTo?: string | null;
  replace?: boolean;
};

export const navigateBackOrFallback = (
  navigate: NavigateFunction,
  { fallbackTo = null, replace = false }: NavigateBackOptions = {},
) => {
  if (canNavigateBack()) {
    navigate(-1);
    return;
  }

  if (fallbackTo) {
    navigate(fallbackTo, replace ? { replace: true } : undefined);
  }
};
