import { useCallback, useEffect, useState } from "react";
import type { SessionEntityPlayer } from "../../../entities/session-entity";
import { sessionEntitiesRepo } from "../../../shared/api/sessionEntitiesRepo";

export const useVisibleEntities = (sessionId: string | null | undefined) => {
  const [entities, setEntities] = useState<SessionEntityPlayer[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(() => {
    if (!sessionId) {
      setEntities([]);
      return;
    }
    setLoading(true);
    sessionEntitiesRepo
      .listVisible(sessionId)
      .then((data) => setEntities(Array.isArray(data) ? data : []))
      .catch(() => setEntities([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { entities, loading, refresh };
};
