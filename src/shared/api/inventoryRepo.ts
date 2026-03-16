import type { InventoryItem } from "../../entities/inventory";
import { http } from "./http";

export type CurrencyWallet = {
  cp: number;
  sp: number;
  ep: number;
  gp: number;
  pp: number;
};

type InventoryUpdatePayload = {
  quantity?: number;
  isEquipped?: boolean;
  notes?: string | null;
};

type InventoryBuyPayload = {
  itemId: string;
  quantity?: number;
};

type InventorySellPayload = {
  inventoryItemId: string;
  quantity?: number;
};

export type InventorySellResult = {
  inventoryItem: InventoryItem | null;
  itemId: string;
  itemName: string;
  soldQuantity: number;
  refundCurrency: CurrencyWallet;
  refundLabel: string;
  currentCurrency: CurrencyWallet;
};

export const inventoryRepo = {
  list: (campaignId: string, memberId?: string | null, partyId?: string | null) => {
    const params = new URLSearchParams();
    if (memberId) params.set("memberId", memberId);
    if (partyId) params.set("partyId", partyId);
    const qs = params.toString();
    return http.get<InventoryItem[]>(`/campaigns/${campaignId}/inventory${qs ? `?${qs}` : ""}`);
  },
  buy: (sessionId: string, payload: InventoryBuyPayload) =>
    http.post<InventoryItem>(`/sessions/${sessionId}/shop/buy`, payload),
  sell: (sessionId: string, payload: InventorySellPayload) =>
    http.post<InventorySellResult>(`/sessions/${sessionId}/shop/sell`, payload),
  update: (campaignId: string, invId: string, payload: InventoryUpdatePayload) =>
    http.patch<InventoryItem>(`/campaigns/${campaignId}/inventory/${invId}`, payload),
  remove: (campaignId: string, invId: string) =>
    http.del<void>(`/campaigns/${campaignId}/inventory/${invId}`),
};
