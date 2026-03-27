export type { Item, ItemInput, ItemType } from "./item.types";
export { ItemType as ITEM_TYPES } from "./item.types";
export type { ItemPropertySlug } from "./itemProperties";
export {
  ITEM_PROPERTY_SLUGS,
  WEAPON_PROPERTY_SLUGS,
  getItemPropertyLabel,
  getItemPropertyLabels,
  normalizeItemProperties,
  parseItemPropertiesInput,
  resolveItemPropertySlug,
} from "./itemProperties";
