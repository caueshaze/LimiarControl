import { useEffect, useMemo, useState } from "react";
import type { NPC } from "../../../entities/npc";
import { npcsRepo } from "../../../shared/api/npcsRepo";
import { useCampaigns } from "../../campaign-select";

export const useNpcs = () => {
  const { selectedCampaignId } = useCampaigns();
  const [npcs, setNpcs] = useState<NPC[]>([]);
  const [npcsLoading, setNpcsLoading] = useState(false);
  const [npcsError, setNpcsError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!selectedCampaignId) {
      setNpcs([]);
      setNpcsError(null);
      return;
    }
    let active = true;
    setNpcsLoading(true);
    npcsRepo
      .list(selectedCampaignId)
      .then((data) => {
        if (!active) return;
        setNpcs(Array.isArray(data) ? data : []);
        setNpcsError(null);
      })
      .catch((error: { message?: string }) => {
        if (!active) return;
        setNpcs([]);
        setNpcsError(error?.message ?? "Failed to load NPCs");
      })
      .finally(() => {
        if (!active) return;
        setNpcsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedCampaignId]);

  const filteredNpcs = useMemo(() => {
    if (!query.trim()) {
      return npcs;
    }

    const lower = query.trim().toLowerCase();
    return npcs.filter((npc) => npc.name.toLowerCase().includes(lower));
  }, [npcs, query]);

  const saveNpc = (payload: Omit<NPC, "id" | "createdAt">) => {
    if (!selectedCampaignId) {
      return Promise.resolve();
    }
    return npcsRepo.create(selectedCampaignId, payload).then((npc) => {
      setNpcs((current) => [npc, ...current]);
    });
  };

  const updateNpc = (npcId: string, payload: Omit<NPC, "id" | "createdAt">) => {
    if (!selectedCampaignId) {
      return Promise.resolve();
    }
    return npcsRepo.update(selectedCampaignId, npcId, payload).then((npc) => {
      setNpcs((current) =>
        current.map((entry) => (entry.id === npcId ? npc : entry))
      );
    });
  };

  const removeNpc = (npcId: string) => {
    if (!selectedCampaignId) {
      return Promise.resolve();
    }
    return npcsRepo.remove(selectedCampaignId, npcId).then(() => {
      setNpcs((current) => current.filter((entry) => entry.id !== npcId));
    });
  };

  return {
    npcs: filteredNpcs,
    rawNpcs: npcs,
    npcsLoading,
    npcsError,
    query,
    setQuery,
    saveNpc,
    updateNpc,
    removeNpc,
    selectedCampaignId,
  };
};
