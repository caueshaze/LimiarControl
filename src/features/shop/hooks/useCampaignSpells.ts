import { useCallback, useEffect, useState } from "react";
import type { BaseSpell, BaseSpellFilters } from "../../../entities/base-spell";
import { campaignSpellsRepo } from "../../../shared/api/campaignSpellsRepo";

type UseCampaignSpellsOptions = {
  campaignId?: string | null;
  level?: number;
  school?: string;
  className?: string;
  auto?: boolean;
};

export const useCampaignSpells = (options?: UseCampaignSpellsOptions) => {
  const { campaignId, level, school, className, auto = true } = options ?? {};
  const [spells, setSpells] = useState<BaseSpell[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!campaignId) {
      setSpells([]);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const filters: BaseSpellFilters = {};
      if (level !== undefined) filters.level = level;
      if (school) filters.school = school as BaseSpellFilters["school"];
      if (className) filters.className = className;
      const result = await campaignSpellsRepo.list(campaignId, filters);
      setSpells(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load spells");
    } finally {
      setLoading(false);
    }
  }, [campaignId, className, level, school]);

  useEffect(() => {
    if (auto) {
      void load();
    }
  }, [auto, load]);

  return { spells, loading, error, refetch: load };
};
