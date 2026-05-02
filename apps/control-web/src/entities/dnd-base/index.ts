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
  getSpellAvailabilityClassIds,
  loadSpellCatalog,
  isSpellCatalogLoaded,
  resolveSpellSourceClassId,
  seedSpellCatalogCache
} from "./spellCatalogApi";
export {
  FULL_CASTER_SLOTS,
  HALF_CASTER_SLOTS,
  WARLOCK_SLOTS,
  SLOT_TABLES_BY_CLASS,
  CANTRIPS_BY_CLASS,
  LEVELED_SPELLS_KNOWN_BY_CLASS,
  PREPARED_SPELL_LEVEL_DIVISOR_BY_CLASS,
  SPELLCASTING_TYPE_BY_CLASS,
  getSlotProgressionForLevel,
  getMaxUnlockedSpellLevel,
  getCantripCountForClassLevel,
} from "./spellProgression";
export type { ClassSpellProgression } from "./spellProgressionBackendAdapter";
export { fetchClassSpellProgression } from "./spellProgressionBackendAdapter";
