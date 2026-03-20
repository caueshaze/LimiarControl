import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";

export type PlayerPartySelectedItem = {
  item: Item;
  inv: InventoryItem;
};
