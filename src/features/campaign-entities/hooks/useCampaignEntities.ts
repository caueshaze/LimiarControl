import { useEffect, useMemo, useState } from "react";
import type { CampaignEntity, CampaignEntityPayload, EntityCategory } from "../../../entities/campaign-entity";
import { campaignEntitiesRepo } from "../../../shared/api/campaignEntitiesRepo";
import { useCampaigns } from "../../campaign-select";

type ApiLikeError = {
  status?: number;
  message?: string;
};

export const useCampaignEntities = (enabled = true) => {
  const { selectedCampaignId } = useCampaigns();
  const [entities, setEntities] = useState<CampaignEntity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<EntityCategory | "all">("all");

  useEffect(() => {
    if (!selectedCampaignId || !enabled) {
      setEntities([]);
      setError(null);
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    campaignEntitiesRepo
      .list(selectedCampaignId)
      .then((data) => {
        if (!active) return;
        setEntities(Array.isArray(data) ? data : []);
        setError(null);
      })
      .catch((err: ApiLikeError) => {
        if (!active) return;
        if (err?.status === 404) {
          setEntities([]);
          setError(null);
          return;
        }
        setEntities([]);
        setError(err?.message ?? "Failed to load entities");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [enabled, selectedCampaignId]);

  const filteredEntities = useMemo(() => {
    let result = entities;
    if (categoryFilter !== "all") {
      result = result.filter((e) => e.category === categoryFilter);
    }
    if (query.trim()) {
      const lower = query.trim().toLowerCase();
      result = result.filter((e) => e.name.toLowerCase().includes(lower));
    }
    return result;
  }, [entities, query, categoryFilter]);

  const saveEntity = (payload: CampaignEntityPayload) => {
    if (!selectedCampaignId) return Promise.resolve();
    return campaignEntitiesRepo.create(selectedCampaignId, payload).then((entity) => {
      setEntities((current) => [entity, ...current]);
    });
  };

  const updateEntity = (entityId: string, payload: CampaignEntityPayload) => {
    if (!selectedCampaignId) return Promise.resolve();
    return campaignEntitiesRepo.update(selectedCampaignId, entityId, payload).then((entity) => {
      setEntities((current) =>
        current.map((e) => (e.id === entityId ? entity : e))
      );
    });
  };

  const removeEntity = (entityId: string) => {
    if (!selectedCampaignId) return Promise.resolve();
    return campaignEntitiesRepo.remove(selectedCampaignId, entityId).then(() => {
      setEntities((current) => current.filter((e) => e.id !== entityId));
    });
  };

  return {
    entities: filteredEntities,
    rawEntities: entities,
    loading,
    error,
    query,
    setQuery,
    categoryFilter,
    setCategoryFilter,
    saveEntity,
    updateEntity,
    removeEntity,
    selectedCampaignId,
  };
};
