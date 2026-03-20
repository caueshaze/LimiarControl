import { useCallback, useEffect, useState } from "react";
import type { BaseSpell, BaseSpellFilters } from "../../../entities/base-spell";
import { baseSpellsRepo } from "../../../shared/api/baseSpellsRepo";

type UseBaseSpellsOptions = {
  level?: number;
  school?: string;
  className?: string;
  auto?: boolean;
};

export const useBaseSpells = (options?: UseBaseSpellsOptions) => {
  const { level, school, className, auto = true } = options ?? {};
  const [spells, setSpells] = useState<BaseSpell[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const filters: BaseSpellFilters = {};
      if (level !== undefined) filters.level = level;
      if (school) filters.school = school as BaseSpellFilters["school"];
      if (className) filters.className = className;
      const result = await baseSpellsRepo.list(filters);
      setSpells(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load spells");
    } finally {
      setLoading(false);
    }
  }, [level, school, className]);

  useEffect(() => {
    if (auto) {
      load();
    }
  }, [auto, load]);

  return { spells, loading, error, refetch: load };
};
