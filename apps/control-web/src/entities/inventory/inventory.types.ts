export type InventoryItem = {
  id: string;
  campaignId?: string;
  partyId?: string | null;
  memberId: string;
  itemId: string;
  quantity: number;
  chargesCurrent?: number | null;
  isEquipped: boolean;
  notes?: string;
  sourceSpellCanonicalKey?: string | null;
  expiresAt?: string | null;
  createdAt?: string;
  updatedAt?: string | null;
};
