import { useCallback, useEffect, useState } from "react";
import type { SessionEntity } from "../../../entities/session-entity";
import { sessionEntitiesRepo } from "../../../shared/api/sessionEntitiesRepo";

export const useSessionEntities = (sessionId: string | null | undefined) => {
  const [entities, setEntities] = useState<SessionEntity[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(() => {
    if (!sessionId) {
      setEntities([]);
      return;
    }
    setLoading(true);
    sessionEntitiesRepo
      .list(sessionId)
      .then((data) => setEntities(Array.isArray(data) ? data : []))
      .catch(() => setEntities([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

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
    setEntities((current) => [...current, se]);
    return se;
  };

  const removeEntity = async (sessionEntityId: string) => {
    if (!sessionId) return;
    await sessionEntitiesRepo.remove(sessionId, sessionEntityId);
    setEntities((current) => current.filter((e) => e.id !== sessionEntityId));
  };

  const toggleVisibility = async (sessionEntityId: string) => {
    if (!sessionId) return;
    const target = entities.find((e) => e.id === sessionEntityId);
    if (!target) return;
    const updated = target.visibleToPlayers
      ? await sessionEntitiesRepo.hide(sessionId, sessionEntityId)
      : await sessionEntitiesRepo.reveal(sessionId, sessionEntityId);
    setEntities((current) =>
      current.map((e) => (e.id === sessionEntityId ? updated : e))
    );
  };

  const updateHp = async (sessionEntityId: string, hp: number | null) => {
    if (!sessionId) return;
    const updated = await sessionEntitiesRepo.update(sessionId, sessionEntityId, {
      currentHp: hp,
    });
    setEntities((current) =>
      current.map((e) => (e.id === sessionEntityId ? updated : e))
    );
  };

  const updateLabel = async (sessionEntityId: string, label: string) => {
    if (!sessionId) return;
    const updated = await sessionEntitiesRepo.update(sessionId, sessionEntityId, {
      label,
    });
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
