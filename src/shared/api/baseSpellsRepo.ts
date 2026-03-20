import type { BaseSpell, BaseSpellFilters } from "../../entities/base-spell";
import { http } from "./http";

const toQueryString = (filters?: BaseSpellFilters) => {
  if (!filters) {
    return "";
  }

  const params = new URLSearchParams();
  if (filters.system) {
    params.set("system", filters.system);
  }
  if (filters.level !== undefined && filters.level !== null) {
    params.set("level", String(filters.level));
  }
  if (filters.school) {
    params.set("school", filters.school);
  }
  if (filters.className) {
    params.set("class_name", filters.className);
  }
  if (filters.canonicalKey) {
    params.set("canonical_key", filters.canonicalKey);
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
};

export type BaseSpellUpdatePayload = {
  nameEn?: string;
  namePt?: string | null;
  descriptionEn?: string;
  descriptionPt?: string | null;
  level?: number;
  school?: BaseSpell["school"];
  classesJson?: string[] | null;
  castingTime?: string | null;
  rangeText?: string | null;
  duration?: string | null;
  componentsJson?: string[] | null;
  materialComponentText?: string | null;
  concentration?: boolean;
  ritual?: boolean;
  damageType?: string | null;
  savingThrow?: string | null;
};

export const baseSpellsRepo = {
  list: (filters?: BaseSpellFilters) =>
    http.get<BaseSpell[]>(`/base-spells${toQueryString(filters)}`),
  get: (baseSpellId: string) =>
    http.get<BaseSpell>(`/base-spells/${baseSpellId}`),
  update: (baseSpellId: string, payload: BaseSpellUpdatePayload) =>
    http.put<BaseSpell>(`/base-spells/${baseSpellId}`, payload),
  delete: (baseSpellId: string) =>
    http.del(`/base-spells/${baseSpellId}`),
};
