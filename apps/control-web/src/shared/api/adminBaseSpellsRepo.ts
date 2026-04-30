import type {
  BaseSpell,
  BaseSpellFilters,
  BaseSpellWritePayload,
} from "../../entities/base-spell";
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
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (typeof filters.isActive === "boolean") {
    params.set("is_active", String(filters.isActive));
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
};

interface SeedSyncResult {
  inserted: number;
  updated: number;
  deactivated: number;
  total: number;
}

export const adminBaseSpellsRepo = {
  list: (filters?: BaseSpellFilters) =>
    http.get<BaseSpell[]>(`/admin/base-spells${toQueryString(filters)}`),
  get: (baseSpellId: string) =>
    http.get<BaseSpell>(`/admin/base-spells/${baseSpellId}`),
  create: (payload: BaseSpellWritePayload) =>
    http.post<BaseSpell>("/admin/base-spells", payload),
  update: (baseSpellId: string, payload: BaseSpellWritePayload) =>
    http.put<BaseSpell>(`/admin/base-spells/${baseSpellId}`, payload),
  delete: (baseSpellId: string) =>
    http.del(`/admin/base-spells/${baseSpellId}`),
  syncSeed: () =>
    http.post<SeedSyncResult>("/admin/base-spells/sync-seed", {}),
  exportSeed: () =>
    http.post<SeedSyncResult>("/admin/base-spells/export-seed", {}),
};
