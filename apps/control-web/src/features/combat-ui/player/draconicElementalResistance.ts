import { getDraconicLineageState } from "../../character-sheet/data/draconicAncestry";
import type { CharacterSheet } from "../../character-sheet/model/characterSheet.types";
import type { ActiveEffect } from "../../../shared/api/combatRepo";

export const DRACONIC_ELEMENTAL_RESISTANCE_ACTION_ID = "draconic_elemental_resistance";
export const SORCERY_POINTS_RESOURCE_KEY = "sorceryPoints";
export const ELEMENTAL_AFFINITY_RESISTANCE_EFFECT_KIND = "elemental_affinity_resistance";

export type DraconicElementalResistanceAction = {
  id: typeof DRACONIC_ELEMENTAL_RESISTANCE_ACTION_ID;
  damageType: string;
  sorceryPointsMax: number;
  sorceryPointsRemaining: number;
};

/**
 * Elemental Affinity (Draconic Bloodline 6+): the character may spend 1 sorcery
 * point to gain resistance to the lineage damage type for 1 minute. Returns null
 * when the feature is unavailable (not a draconic sorcerer, below level 6, or no
 * ancestry chosen).
 */
export const buildDraconicElementalResistanceAction = (
  playerSheet?: CharacterSheet | null,
): DraconicElementalResistanceAction | null => {
  if (!playerSheet) {
    return null;
  }
  if (playerSheet.wildShape?.active) {
    return null;
  }

  const lineage = getDraconicLineageState({
    classId: playerSheet.class,
    subclass: playerSheet.subclass,
    level: playerSheet.level,
    subclassConfig: playerSheet.subclassConfig,
  });

  if (!lineage.hasElementalAffinity || !lineage.resistanceType) {
    return null;
  }

  const resource = playerSheet.classResources?.[SORCERY_POINTS_RESOURCE_KEY];
  const sorceryPointsMax = Math.max(0, resource?.usesMax ?? 0);
  const sorceryPointsRemaining = Math.max(
    0,
    Math.min(resource?.usesRemaining ?? sorceryPointsMax, sorceryPointsMax),
  );

  return {
    id: DRACONIC_ELEMENTAL_RESISTANCE_ACTION_ID,
    damageType: lineage.resistanceType,
    sorceryPointsMax,
    sorceryPointsRemaining,
  };
};

export type ActiveElementalResistance = {
  damageType: string;
  expiresAtGameTimeSeconds: number | null;
  secondsRemaining: number | null;
};

/**
 * Resolve the currently active Elemental Affinity resistance (if any) from the
 * player's active spell effects, computing the seconds remaining against the
 * current game time when both are known.
 */
export const resolveActiveElementalResistance = (
  activeSpellEffects?: ActiveEffect[] | null,
  gameTimeSeconds?: number | null,
): ActiveElementalResistance | null => {
  if (!activeSpellEffects?.length) {
    return null;
  }
  const effect = activeSpellEffects.find(
    (candidate) => candidate.kind === ELEMENTAL_AFFINITY_RESISTANCE_EFFECT_KIND,
  );
  if (!effect) {
    return null;
  }
  const record = effect as ActiveEffect & {
    damage_type?: string | null;
    expires_at_game_time_seconds?: number | null;
  };
  const expiresAt =
    typeof record.expires_at_game_time_seconds === "number"
      ? record.expires_at_game_time_seconds
      : null;
  const secondsRemaining =
    expiresAt != null && typeof gameTimeSeconds === "number"
      ? Math.max(0, expiresAt - gameTimeSeconds)
      : null;
  return {
    damageType: String(record.damage_type ?? "").trim().toLowerCase(),
    expiresAtGameTimeSeconds: expiresAt,
    secondsRemaining,
  };
};
