import type { Item } from "../../entities/item";
import { http } from "./http";

type CreateItemPayload = Omit<Item, "id">;
type UpdateItemPayload = Omit<Item, "id">;

export const itemsRepo = {
  list: (campaignId: string) =>
    http.get<Item[]>(`/campaigns/${campaignId}/items`),
  listBySession: (sessionId: string) =>
    http.get<Item[]>(`/sessions/${sessionId}/shop/items`),
  create: (campaignId: string, payload: CreateItemPayload) =>
    http.post<Item>(`/campaigns/${campaignId}/items`, payload),
  update: (campaignId: string, itemId: string, payload: UpdateItemPayload) =>
    http.put<Item>(`/campaigns/${campaignId}/items/${itemId}`, payload),
  remove: (campaignId: string, itemId: string) =>
    http.del<void>(`/campaigns/${campaignId}/items/${itemId}`),
};
