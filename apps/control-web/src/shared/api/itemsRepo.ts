import type { Item, ItemInput } from "../../entities/item";
import { http } from "./http";

export const itemsRepo = {
  list: (campaignId: string) =>
    http.get<Item[]>(`/campaigns/${campaignId}/items`),
  listBySession: (sessionId: string) =>
    http.get<Item[]>(`/sessions/${sessionId}/shop/items`),
  create: (campaignId: string, payload: ItemInput) =>
    http.post<Item>(`/campaigns/${campaignId}/items`, payload),
  update: (campaignId: string, itemId: string, payload: ItemInput) =>
    http.put<Item>(`/campaigns/${campaignId}/items/${itemId}`, payload),
  remove: (campaignId: string, itemId: string) =>
    http.del<void>(`/campaigns/${campaignId}/items/${itemId}`),
};
