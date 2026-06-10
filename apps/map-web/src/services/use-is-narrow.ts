import { useSyncExternalStore } from "react";

/**
 * Reactive viewport breakpoint. Returns true when the viewport is at most
 * `maxWidth` CSS pixels wide. Backed by `matchMedia` via `useSyncExternalStore`
 * (same external-store pattern used for the battle-map store).
 */
export function useIsNarrow(maxWidth = 768): boolean {
  return useSyncExternalStore(
    (onChange) => {
      if (typeof window === "undefined" || !window.matchMedia) return () => {};
      const query = window.matchMedia(`(max-width: ${maxWidth}px)`);
      query.addEventListener("change", onChange);
      return () => query.removeEventListener("change", onChange);
    },
    () =>
      typeof window !== "undefined" && window.matchMedia
        ? window.matchMedia(`(max-width: ${maxWidth}px)`).matches
        : false,
    () => false
  );
}
