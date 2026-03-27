import { ITEM_TYPES, resolveItemPropertySlug, type Item } from "../../entities/item";
import type { InventoryItem } from "../../entities/inventory";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { getModifier, getProficiencyBonus } from "../../features/character-sheet/utils/calculations";
import { localizedItemName } from "../../features/shop/utils/localizedItemName";
import { formatDamageLabel } from "../../shared/i18n/domainLabels";
import type { PlayerBoardWeaponSummary } from "./playerBoard.types";

const SPECIFIC_WEAPON_PROFICIENCY_ALIASES: Record<string, string[]> = {
  club: ["clava", "clavas", "club", "clubs"],
  dagger: ["adaga", "adagas", "dagger", "daggers"],
  dart: ["dardo", "dardos", "dart", "darts"],
  hand_crossbow: ["besta de mao", "bestas de mao", "hand crossbow", "hand crossbows"],
  javelin: ["azagaia", "azagaias", "javelin", "javelins"],
  light_crossbow: ["besta leve", "bestas leves", "light crossbow", "light crossbows"],
  longsword: ["espada longa", "espadas longas", "longsword", "longswords"],
  mace: ["maca", "macas", "maça", "maças", "mace", "maces"],
  quarterstaff: ["cajado", "cajados", "quarterstaff", "quarterstaffs", "staff"],
  rapier: ["rapieira", "rapieiras", "rapier", "rapiers"],
  scimitar: ["cimitarra", "cimitarras", "scimitar", "scimitars"],
  shortsword: ["espada curta", "espadas curtas", "shortsword", "shortswords"],
  sickle: ["foice", "foices", "sickle", "sickles"],
  sling: ["funda", "fundas", "sling", "slings"],
  spear: ["lanca", "lancas", "lança", "lanças", "spear", "spears"],
} as const;

const normalizeLookup = (value: string | null | undefined) =>
  String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");

const chooseWeaponAbility = (sheet: CharacterSheet, item: Item) => {
  const hasFinesse = (item.properties ?? []).some(
    (property) => resolveItemPropertySlug(property) === "finesse",
  );
  if (hasFinesse) {
    return getModifier(sheet.abilities.dexterity) >= getModifier(sheet.abilities.strength)
      ? "dexterity"
      : "strength";
  }
  return item.weaponRangeType === "ranged" ? "dexterity" : "strength";
};

const isWeaponProficient = (sheet: CharacterSheet, item: Item) => {
  const proficiencies = new Set(sheet.weaponProficiencies.map((entry) => normalizeLookup(entry)));
  const category = normalizeLookup(item.weaponCategory ?? "");
  if (category === "simple" && (proficiencies.has("simples") || proficiencies.has("simple"))) {
    return true;
  }
  if (
    category === "martial" &&
    (proficiencies.has("marciais") || proficiencies.has("martial"))
  ) {
    return true;
  }

  const candidates = new Set<string>([
    normalizeLookup(item.name),
    normalizeLookup(item.namePtSnapshot ?? null),
    normalizeLookup(item.nameEnSnapshot ?? null),
  ]);
  const canonicalKey = normalizeLookup(item.canonicalKeySnapshot ?? null).replace(/\s+/g, "_");
  if (canonicalKey) {
    const aliases = SPECIFIC_WEAPON_PROFICIENCY_ALIASES[canonicalKey];
    if (aliases?.some((alias) => proficiencies.has(normalizeLookup(alias)))) {
      return true;
    }
  }

  for (const candidate of candidates) {
    if (candidate && proficiencies.has(candidate)) {
      return true;
    }
  }

  return false;
};

const findLegacyWeaponProfile = (sheet: CharacterSheet, item: Item) => {
  const candidates = new Set<string>([
    normalizeLookup(item.name),
    normalizeLookup(item.namePtSnapshot ?? null),
    normalizeLookup(item.nameEnSnapshot ?? null),
  ]);
  const canonicalKey = normalizeLookup(item.canonicalKeySnapshot ?? null).replace(/\s+/g, "_");
  if (canonicalKey) {
    const aliases = SPECIFIC_WEAPON_PROFICIENCY_ALIASES[canonicalKey];
    aliases?.forEach((alias) => candidates.add(normalizeLookup(alias)));
  }

  return sheet.weapons.find((weapon) => {
    const weaponName = normalizeLookup(weapon.name);
    return weaponName.length > 0 && candidates.has(weaponName);
  }) ?? null;
};

export const buildPlayerBoardWeaponSummary = ({
  inventory,
  itemsById,
  locale,
  playerSheet,
}: {
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  locale: string;
  playerSheet: CharacterSheet | null;
}): PlayerBoardWeaponSummary | null => {
  if (!playerSheet?.currentWeaponId) {
    return null;
  }

  const selectedEntry = (inventory ?? []).find((entry) => entry.id === playerSheet.currentWeaponId);
  if (!selectedEntry) {
    return null;
  }

  const item = itemsById[selectedEntry.itemId];
  if (!item || item.type !== ITEM_TYPES.WEAPON) {
    return null;
  }

  const legacyWeapon = findLegacyWeaponProfile(playerSheet, item);
  const proficient = isWeaponProficient(playerSheet, item) || legacyWeapon?.proficient === true;
  const attackAbility = chooseWeaponAbility(playerSheet, item);
  const magicBonus = legacyWeapon?.magicBonus ?? 0;
  const attackBonus =
    getModifier(playerSheet.abilities[attackAbility]) +
    (proficient ? getProficiencyBonus(playerSheet.level) : 0) +
    magicBonus;
  return {
    attackBonus,
    damageLabel: formatDamageLabel(item.damageDice, item.damageType, locale) ?? "—",
    name: localizedItemName(item, locale),
    proficient,
  };
};
