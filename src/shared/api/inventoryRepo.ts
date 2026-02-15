import type { InventoryItem } from "../../entities/inventory";
import { http } from "./http";

type InventoryUpdatePayload = {
  quantity?: number;
  isEquipped?: boolean;
  notes?: string | null;
};

type InventoryBuyPayload = {
  itemId: string;
  quantity?: number;
};

export const inventoryRepo = {
  list: (campaignId: string, memberId?: string | null) =>
    http.get<InventoryItem[]>(
      `/campaigns/${campaignId}/inventory${memberId ? `?memberId=${memberId}` : ""}`
    ),
  buy: (sessionId: string, payload: InventoryBuyPayload) =>
    http.post<InventoryItem>(`/sessions/${sessionId}/shop/buy`, payload),
  update: (campaignId: string, invId: string, payload: InventoryUpdatePayload) =>
    http.patch<InventoryItem>(`/campaigns/${campaignId}/inventory/${invId}`, payload),
  remove: (campaignId: string, invId: string) =>
    http.del<void>(`/campaigns/${campaignId}/inventory/${invId}`),
};
