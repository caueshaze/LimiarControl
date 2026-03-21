import { ITEM_TYPES, resolveItemPropertySlug, type Item } from "../../entities/item";
import type { InventoryItem } from "../../entities/inventory";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { getModifier, getProficiencyBonus } from "../../features/character-sheet/utils/calculations";
import type { PlayerBoardWeaponSummary } from "./playerBoard.types";

const DAMAGE_TYPE_LABELS = {
  acid: { en: "acid", pt: "ácido" },
  bludgeoning: { en: "bludgeoning", pt: "esmagamento" },
  cold: { en: "cold", pt: "frio" },
  fire: { en: "fire", pt: "fogo" },
  force: { en: "force", pt: "força" },
  lightning: { en: "lightning", pt: "elétrico" },
  necrotic: { en: "necrotic", pt: "necrótico" },
  piercing: { en: "piercing", pt: "perfurante" },
  poison: { en: "poison", pt: "veneno" },
  psychic: { en: "psychic", pt: "psíquico" },
  radiant: { en: "radiant", pt: "radiante" },
  slashing: { en: "slashing", pt: "cortante" },
  thunder: { en: "thunder", pt: "trovejante" },
} as const;

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

const localizeDamageType = (damageType: string | null | undefined, locale: string) => {
  const normalized = normalizeLookup(damageType);
  if (!normalized) {
    return null;
  }
  const labels = DAMAGE_TYPE_LABELS[normalized as keyof typeof DAMAGE_TYPE_LABELS];
  if (labels) {
    return locale === "pt" ? labels.pt : labels.en;
  }
  return damageType?.trim() ?? null;
};

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

  const proficient = isWeaponProficient(playerSheet, item);
  const attackAbility = chooseWeaponAbility(playerSheet, item);
  const attackBonus =
    getModifier(playerSheet.abilities[attackAbility]) +
    (proficient ? getProficiencyBonus(playerSheet.level) : 0);
  const damageTypeLabel = localizeDamageType(item.damageType, locale);

  return {
    attackBonus,
    damageLabel: item.damageDice
      ? `${item.damageDice}${damageTypeLabel ? ` ${damageTypeLabel}` : ""}`
      : (damageTypeLabel ?? "—"),
    name: item.name,
    proficient,
  };
};
