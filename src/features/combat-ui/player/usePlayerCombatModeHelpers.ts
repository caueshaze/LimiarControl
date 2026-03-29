import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import { getBaseSpells, loadSpellCatalog } from "../../../entities/dnd-base";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import type { CombatSpellMode } from "../../../shared/api/combatRepo";
import {
  getCombatSpellAutomation,
  resolveCombatSpellActionCost,
} from "../spellAutomation";
import type { CombatSpellOption } from "./usePlayerCombatMode.types";

export const normalizeSavingThrow = (value?: string | null): AbilityName | "" => {
  const normalized = value?.trim().toLowerCase();
  switch (normalized) {
    case "str":
    case "strength":
      return "strength";
    case "dex":
    case "dexterity":
      return "dexterity";
    case "con":
    case "constitution":
      return "constitution";
    case "int":
    case "intelligence":
      return "intelligence";
    case "wis":
    case "wisdom":
      return "wisdom";
    case "cha":
    case "charisma":
      return "charisma";
    default:
      return "";
  }
};

export const buildSpellOptions = (
  playerSheet?: CharacterSheet | null,
  campaignId?: string | null,
  inventory?: InventoryItem[] | null,
  itemsById?: Record<string, Item>,
): CombatSpellOption[] => {
  const catalog = getBaseSpells(campaignId);
  const byCanonicalKey = new Map(
    catalog.map((spell) => [spell.canonicalKey.toLowerCase(), spell] as const),
  );
  const byName = new Map(catalog.map((spell) => [spell.name.toLowerCase(), spell] as const));
  const spellcasting = playerSheet?.spellcasting;
  const availableSlotLevels = Object.entries(spellcasting?.slots ?? {})
    .map(([level, slot]) => ({ level: Number(level), slot }))
    .filter(({ level, slot }) => Number.isInteger(level) && level > 0 && Boolean(slot?.max))
    .map(({ level }) => level)
    .sort((left, right) => left - right);
  const resolveSuggestedMode = (
    canonicalKey: string | null,
    catalogSpell?: (typeof catalog)[number] | undefined,
  ): CombatSpellMode | null => {
    const automation = getCombatSpellAutomation(canonicalKey);
    return automation?.defaultMode
      ?? (catalogSpell?.resolutionType === "heal"
        ? "heal"
        : catalogSpell?.resolutionType === "damage" && catalogSpell?.savingThrow
          ? "saving_throw"
          : catalogSpell?.resolutionType === "damage"
            ? "spell_attack"
            : (catalogSpell?.resolutionType === "control" || catalogSpell?.resolutionType === "debuff") && catalogSpell?.savingThrow
              ? "saving_throw"
              : "utility");
  };

  const sheetOptions = spellcasting
    ? spellcasting.spells
        .filter((spell) => spell.level === 0 || spell.prepared || spellcasting.mode === "known")
        .map((spell) => {
          const catalogSpell = spell.canonicalKey
            ? byCanonicalKey.get(spell.canonicalKey.toLowerCase()) ?? byName.get(spell.name.toLowerCase())
            : byName.get(spell.name.toLowerCase());
          const canonicalKey = spell.canonicalKey ?? catalogSpell?.canonicalKey ?? null;
          return {
            canonicalKey,
            actionCost: resolveCombatSpellActionCost(catalogSpell?.castingTimeType ?? null),
            damageType: catalogSpell?.damageType ?? null,
            id: spell.id,
            sourceType: "sheet" as const,
            level: spell.level,
            name: spell.name,
            prepared: spell.prepared,
            range: catalogSpell?.range ?? "",
            saveSuccessOutcome: catalogSpell?.saveSuccessOutcome ?? null,
            savingThrow: catalogSpell?.savingThrow ?? null,
            suggestedMode: resolveSuggestedMode(canonicalKey, catalogSpell),
            availableSlotLevels: spell.level > 0
              ? availableSlotLevels.filter((slotLevel) => slotLevel >= spell.level)
              : [],
            upcast: catalogSpell?.upcast ?? null,
          };
        })
    : [];

  const itemSpellOptions = (inventory ?? []).flatMap((entry) => {
    const item = entry.itemId ? itemsById?.[entry.itemId] ?? null : null;
    const magicEffect = item?.magicEffect;
    if (!item || magicEffect?.type !== "cast_spell") {
      return [];
    }
    const chargesMax = item.chargesMax ?? null;
    const chargesCurrent = entry.chargesCurrent ?? chargesMax;
    if (typeof chargesCurrent === "number" && chargesCurrent <= 0) {
      return [];
    }
    const catalogSpell = byCanonicalKey.get(magicEffect.spellCanonicalKey.toLowerCase());
    if (!catalogSpell) {
      return [];
    }
    return [{
      canonicalKey: catalogSpell.canonicalKey,
      actionCost: resolveCombatSpellActionCost(catalogSpell.castingTimeType ?? null),
      chargesCurrent,
      chargesMax,
      damageType: catalogSpell.damageType ?? null,
      fixedCastLevel: magicEffect.castLevel,
      id: `magic-item:${entry.id}`,
      ignoreComponents: Boolean(magicEffect.ignoreComponents),
      inventoryItemId: entry.id,
      level: magicEffect.castLevel,
      name: catalogSpell.name,
      noFreeHandRequired: Boolean(magicEffect.noFreeHandRequired),
      prepared: true,
      range: catalogSpell.range ?? "",
      saveSuccessOutcome: catalogSpell.saveSuccessOutcome ?? null,
      savingThrow: catalogSpell.savingThrow ?? null,
      sourceItemName: item.name,
      sourceType: "magic_item" as const,
      suggestedMode: resolveSuggestedMode(catalogSpell.canonicalKey, catalogSpell),
      availableSlotLevels: magicEffect.castLevel > 0 ? [magicEffect.castLevel] : [],
      upcast: null,
    }];
  });

  return [...sheetOptions, ...itemSpellOptions]
    .sort((left, right) => left.level - right.level || left.name.localeCompare(right.name));
};

export const buildHealingLabel = (item: Pick<Item, "healDice" | "healBonus">) => {
  if (!item.healDice && typeof item.healBonus !== "number") {
    return null;
  }
  if (!item.healDice) {
    return `${item.healBonus ?? 0}`;
  }
  if (typeof item.healBonus !== "number" || item.healBonus === 0) {
    return item.healDice;
  }
  return `${item.healDice} ${item.healBonus > 0 ? "+" : "-"} ${Math.abs(item.healBonus)}`;
};

export { loadSpellCatalog };

export const withActionState = async (callback: () => Promise<void>) => {
  try {
    await callback();
  } catch (err: any) {
    throw new Error(err?.data?.detail || err?.message || "Combat action failed");
  }
};
