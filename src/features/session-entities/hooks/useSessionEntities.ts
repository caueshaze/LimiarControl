import { useCallback, useEffect, useRef, useState } from "react";
import type { SessionEntity } from "../../../entities/session-entity";
import { sessionEntitiesRepo } from "../../../shared/api/sessionEntitiesRepo";

export const useSessionEntities = (sessionId: string | null | undefined) => {
  const [entities, setEntities] = useState<SessionEntity[]>([]);
  const [loading, setLoading] = useState(false);
  const requestIdRef = useRef(0);

  const invalidatePendingRequests = useCallback(() => {
    requestIdRef.current += 1;
    setLoading(false);
  }, []);

  const refresh = useCallback(() => {
    if (!sessionId) {
      invalidatePendingRequests();
      setEntities([]);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setLoading(true);
    sessionEntitiesRepo
      .list(sessionId)
      .then((data) => {
        if (requestIdRef.current !== requestId) return;
        setEntities(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (requestIdRef.current !== requestId) return;
        setEntities([]);
      })
      .finally(() => {
        if (requestIdRef.current === requestId) {
          setLoading(false);
        }
      });
  }, [invalidatePendingRequests, sessionId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const addEntity = async (campaignEntityId: string, label?: string | null, currentHp?: number | null) => {
    if (!sessionId) return;
    const se = await sessionEntitiesRepo.add(sessionId, {
      campaignEntityId,
      label: label ?? undefined,
      currentHp: currentHp ?? undefined,
    });
    invalidatePendingRequests();
    setEntities((current) => [...current, se]);
    return se;
  };

  const removeEntity = async (sessionEntityId: string) => {
    if (!sessionId) return;
    await sessionEntitiesRepo.remove(sessionId, sessionEntityId);
    invalidatePendingRequests();
    setEntities((current) => current.filter((e) => e.id !== sessionEntityId));
  };

  const toggleVisibility = async (sessionEntityId: string) => {
    if (!sessionId) return;
    const target = entities.find((e) => e.id === sessionEntityId);
    if (!target) return;
    const updated = target.visibleToPlayers
      ? await sessionEntitiesRepo.hide(sessionId, sessionEntityId)
      : await sessionEntitiesRepo.reveal(sessionId, sessionEntityId);
    invalidatePendingRequests();
    setEntities((current) =>
      current.map((e) => (e.id === sessionEntityId ? updated : e))
    );
  };

  const updateHp = async (sessionEntityId: string, hp: number | null) => {
    if (!sessionId) return;
    const updated = await sessionEntitiesRepo.update(sessionId, sessionEntityId, {
      currentHp: hp,
    });
    invalidatePendingRequests();
    setEntities((current) =>
      current.map((e) => (e.id === sessionEntityId ? updated : e))
    );
  };

  const updateLabel = async (sessionEntityId: string, label: string) => {
    if (!sessionId) return;
    const updated = await sessionEntitiesRepo.update(sessionId, sessionEntityId, {
      label,
    });
    invalidatePendingRequests();
    setEntities((current) =>
      current.map((e) => (e.id === sessionEntityId ? updated : e))
    );
  };

  return {
    entities,
    loading,
    refresh,
    addEntity,
    removeEntity,
    toggleVisibility,
    updateHp,
    updateLabel,
  };
};
