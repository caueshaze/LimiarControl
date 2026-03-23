import { useCallback, useEffect, useRef, useState } from "react";
import type { SessionEntityPlayer } from "../../../entities/session-entity";
import { sessionEntitiesRepo } from "../../../shared/api/sessionEntitiesRepo";

const buildCacheKey = (sessionId: string) => `limiar:visibleSessionEntities:${sessionId}`;

const readCachedEntities = (sessionId: string | null | undefined): SessionEntityPlayer[] => {
  if (!sessionId || typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.sessionStorage.getItem(buildCacheKey(sessionId));
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const writeCachedEntities = (
  sessionId: string | null | undefined,
  entities: SessionEntityPlayer[],
) => {
  if (!sessionId || typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(buildCacheKey(sessionId), JSON.stringify(entities));
};

export const useVisibleEntities = (sessionId: string | null | undefined) => {
  const [entities, setEntities] = useState<SessionEntityPlayer[]>(() => readCachedEntities(sessionId));
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(() => readCachedEntities(sessionId).length > 0);
  const requestIdRef = useRef(0);
  const entitiesRef = useRef<SessionEntityPlayer[]>(readCachedEntities(sessionId));

  const invalidatePendingRequests = useCallback(() => {
    requestIdRef.current += 1;
    setLoading(false);
  }, []);

  const replaceEntities = useCallback((nextEntities: SessionEntityPlayer[]) => {
    entitiesRef.current = nextEntities;
    setEntities(nextEntities);
    writeCachedEntities(sessionId, nextEntities);
  }, [sessionId]);

  const applyEntities = useCallback(
    (updater: (current: SessionEntityPlayer[]) => SessionEntityPlayer[]) => {
      setEntities((current) => {
        const nextEntities = updater(current);
        entitiesRef.current = nextEntities;
        writeCachedEntities(sessionId, nextEntities);
        return nextEntities;
      });
    },
    [sessionId],
  );

  useEffect(() => {
    if (!sessionId) {
      invalidatePendingRequests();
      replaceEntities([]);
      setLoaded(false);
      return;
    }

    const cached = readCachedEntities(sessionId);
    replaceEntities(cached);
    setLoaded(cached.length > 0);
  }, [invalidatePendingRequests, replaceEntities, sessionId]);

  const refresh = useCallback(() => {
    if (!sessionId) {
      invalidatePendingRequests();
      replaceEntities([]);
      setLoaded(false);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setLoading(true);
    sessionEntitiesRepo
      .listVisible(sessionId)
      .then((data) => {
        if (requestIdRef.current !== requestId) return;
        replaceEntities(Array.isArray(data) ? data : []);
        setLoaded(true);
      })
      .catch(() => {
        if (requestIdRef.current !== requestId) return;
        setLoaded(true);
      })
      .finally(() => {
        if (requestIdRef.current === requestId) {
          setLoading(false);
        }
      });
  }, [invalidatePendingRequests, replaceEntities, sessionId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        refresh();
      }
    }, 3000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [refresh, sessionId]);

  const updateHp = useCallback((sessionEntityId: string, currentHp: number | null | undefined) => {
    const entityExists = entitiesRef.current.some((entity) => entity.id === sessionEntityId);
    invalidatePendingRequests();
    setLoaded(true);
    applyEntities((current) => {
      const normalizedHp = currentHp ?? null;
      let changed = false;
      const nextEntities = current.map((entity) => {
        if (entity.id !== sessionEntityId) {
          return entity;
        }
        if ((entity.currentHp ?? null) === normalizedHp) {
          return entity;
        }
        changed = true;
        return { ...entity, currentHp: normalizedHp };
      });
      return changed ? nextEntities : current;
    });
    if (!entityExists) {
      refresh();
    }
  }, [applyEntities, invalidatePendingRequests, refresh]);

  const removeEntity = useCallback((sessionEntityId: string) => {
    const entityExists = entitiesRef.current.some((entity) => entity.id === sessionEntityId);
    invalidatePendingRequests();
    setLoaded(true);
    applyEntities((current) => {
      const nextEntities = current.filter((entity) => entity.id !== sessionEntityId);
      return nextEntities;
    });
    if (!entityExists) {
      refresh();
    }
  }, [applyEntities, invalidatePendingRequests, refresh]);

  const upsertEntity = useCallback((entity: SessionEntityPlayer) => {
    invalidatePendingRequests();
    setLoaded(true);
    applyEntities((current) => {
      const existing = current.find((entry) => entry.id === entity.id);
      if (!existing) {
        return [...current, entity];
      }
      return current.map((entry) =>
        entry.id === entity.id
          ? {
              ...entry,
              ...entity,
              entity: entity.entity ?? entry.entity,
            }
          : entry,
      );
    });
  }, [applyEntities, invalidatePendingRequests]);

  return { entities, loading, loaded, refresh, updateHp, removeEntity, upsertEntity };
};
