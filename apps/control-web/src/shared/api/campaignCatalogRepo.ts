import type { Item } from "../../entities/item";
import { http } from "./http";

type CatalogSeedResult = {
  inserted: number;
  existing: number;
};

export const campaignCatalogRepo = {
  seed: (campaignId: string) =>
    http.post<CatalogSeedResult>(
      `/campaigns/${campaignId}/catalog/seed`,
      {},
    ),

  list: (campaignId: string, filters?: { itemKind?: string; search?: string }) => {
    const params = new URLSearchParams();
    if (filters?.itemKind) params.set("item_kind", filters.itemKind);
    if (filters?.search) params.set("search", filters.search);
    const qs = params.toString();
    return http.get<Item[]>(
      `/campaigns/${campaignId}/catalog${qs ? `?${qs}` : ""}`,
    );
  },
};
