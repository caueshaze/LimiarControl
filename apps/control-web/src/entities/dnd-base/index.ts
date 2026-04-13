export type { DndItemNormalization } from "./itemCanonicalization";
export {
  canonicalizeDndItemName,
  DND_ITEM_NORMALIZATIONS,
  getDndItemAliases,
  getDndItemCanonicalKey,
  getDndItemCanonicalization,
  getDndItemLookupNames,
  normalizeDndItemKey
} from "./itemCanonicalization";
export type { BaseSpell } from "./spellCatalogApi";
export type {
  SpellAuthorityCandidate,
  SpellAuthorityReference
} from "./spellAuthority";
export {
  getSpellAuthorityKey,
  getSpellAuthorityReference,
  isSameSpellAuthority,
  normalizeSpellAuthorityName,
  resolveSpellByAuthority,
} from "./spellAuthority";
export {
  getBaseSpells,
  findBaseSpell,
  getBaseSpellsForClass,
  loadSpellCatalog,
  isSpellCatalogLoaded,
  resolveSpellSourceClassId,
  seedSpellCatalogCache
} from "./spellCatalogApi";
