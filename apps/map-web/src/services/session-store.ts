import type { EncounterSnapshotResponse } from "@limiarmap/shared-contracts";
import { useSyncExternalStore } from "react";

type Listener = () => void;

export class SessionStore {
  private snapshot: EncounterSnapshotResponse | null = null;
  private readonly listeners = new Set<Listener>();

  getSnapshot(): EncounterSnapshotResponse | null {
    return this.snapshot;
  }

  setSnapshot(snapshot: EncounterSnapshotResponse): void {
    this.snapshot = snapshot;
    this.emit();
  }

  clearSnapshot(): void {
    if (this.snapshot === null) {
      return;
    }
    this.snapshot = null;
    this.emit();
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(): void {
    this.listeners.forEach((listener) => listener());
  }
}

export const sessionStore = new SessionStore();

export function useEncounterSnapshot(): EncounterSnapshotResponse | null {
  return useSyncExternalStore(
    (listener: Listener) => sessionStore.subscribe(listener),
    () => sessionStore.getSnapshot(),
    () => sessionStore.getSnapshot()
  );
}
