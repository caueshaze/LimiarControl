export type InventoryItem = {
  id: string;
  memberId: string;
  itemId: string;
  quantity: number;
  isEquipped: boolean;
  notes?: string;
};
