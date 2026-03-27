export type { DndItemNormalization } from "./itemCanonicalization";
export {
  canonicalizeDndItemName,
  DND_ITEM_NORMALIZATIONS,
  getDndItemAliases,
  getDndItemCanonicalKey,
  getDndItemCanonicalization,
  getDndItemLookupNames,
  normalizeDndItemKey,
} from "./itemCanonicalization";
export type { BaseSpell } from "./spellCatalogApi";
export { getBaseSpells, findBaseSpell, getBaseSpellsForClass, loadSpellCatalog, isSpellCatalogLoaded, seedSpellCatalogCache } from "./spellCatalogApi";
