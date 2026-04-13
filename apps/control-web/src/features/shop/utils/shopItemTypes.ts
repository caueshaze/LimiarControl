import { ITEM_TYPES, type ItemType } from "../../../entities/item";
import type { LocaleKey } from "../../../shared/i18n";

export const SHOP_ITEM_TYPES = Object.values(ITEM_TYPES) as ItemType[];

const SHOP_ITEM_TYPE_LABEL_KEYS: Record<ItemType, LocaleKey> = {
  WEAPON: "shop.type.weapon",
  ARMOR: "shop.type.armor",
  CONSUMABLE: "shop.type.consumable",
  MISC: "shop.type.misc",
  MAGIC: "shop.type.magic",
};

export const getShopItemTypeLabelKey = (type: ItemType): LocaleKey =>
  SHOP_ITEM_TYPE_LABEL_KEYS[type];
