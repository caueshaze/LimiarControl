import type { BaseItem, BaseItemFilters } from "../../entities/base-item";
import { http } from "./http";

const toQueryString = (filters?: BaseItemFilters) => {
  if (!filters) {
    return "";
  }

  const params = new URLSearchParams();
  if (filters.system) {
    params.set("system", filters.system);
  }
  if (filters.itemKind) {
    params.set("item_kind", filters.itemKind);
  }
  if (filters.canonicalKey) {
    params.set("canonical_key", filters.canonicalKey);
  }
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.equipmentCategory) {
    params.set("equipment_category", filters.equipmentCategory);
  }
  if (typeof filters.isActive === "boolean") {
    params.set("is_active", String(filters.isActive));
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
};

export const baseItemsRepo = {
  list: (filters?: BaseItemFilters) =>
    http.get<BaseItem[]>(`/base-items${toQueryString(filters)}`),
  get: (baseItemId: string) => http.get<BaseItem>(`/base-items/${baseItemId}`),
};
