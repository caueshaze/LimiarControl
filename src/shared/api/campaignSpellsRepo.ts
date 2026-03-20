import type { BaseSpell, BaseSpellFilters } from "../../entities/base-spell";
import type { BaseSpellUpdatePayload } from "./baseSpellsRepo";
import { http } from "./http";

const toQueryString = (filters?: BaseSpellFilters) => {
  if (!filters) {
    return "";
  }

  const params = new URLSearchParams();
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

export const campaignSpellsRepo = {
  list: (campaignId: string, filters?: BaseSpellFilters) =>
    http.get<BaseSpell[]>(`/campaigns/${campaignId}/spells${toQueryString(filters)}`),
  get: (campaignId: string, spellId: string) =>
    http.get<BaseSpell>(`/campaigns/${campaignId}/spells/${spellId}`),
  update: (campaignId: string, spellId: string, payload: BaseSpellUpdatePayload) =>
    http.put<BaseSpell>(`/campaigns/${campaignId}/spells/${spellId}`, payload),
  delete: (campaignId: string, spellId: string) =>
    http.del(`/campaigns/${campaignId}/spells/${spellId}`),
};
