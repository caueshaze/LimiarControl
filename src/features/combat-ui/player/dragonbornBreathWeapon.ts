import type { CharacterSheet } from "../../character-sheet/model/characterSheet.types";
import {
  getDragonbornBreathWeaponDC,
  getDragonbornBreathWeaponDamageDice,
  resolveDragonbornLineageState,
} from "../../character-sheet/data/dragonbornAncestries";

export const DRAGONBORN_BREATH_WEAPON_ACTION_ID = "dragonborn_breath_weapon";
export const DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY = "dragonbornBreathWeapon";

export type DragonbornBreathWeaponAction = {
  id: typeof DRAGONBORN_BREATH_WEAPON_ACTION_ID;
  ancestry: string;
  ancestryLabel: string | null;
  damageType: string;
  saveAbility: "dexterity" | "constitution";
  damageDice: string;
  dc: number;
  usesMax: number;
  usesRemaining: number;
};

export const buildDragonbornBreathWeaponAction = (
  playerSheet?: CharacterSheet | null,
): DragonbornBreathWeaponAction | null => {
  if (!playerSheet) {
    return null;
  }

  const lineage = resolveDragonbornLineageState({
    raceId: playerSheet.race,
    raceConfig: playerSheet.raceConfig,
  });

  if (!lineage.ancestry || !lineage.damageType || !lineage.breathWeaponSaveType) {
    return null;
  }

  const resource = playerSheet.classResources?.[DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY];
  const usesMax = Math.max(1, resource?.usesMax ?? 1);
  const usesRemaining = Math.max(0, Math.min(resource?.usesRemaining ?? usesMax, usesMax));

  return {
    id: DRAGONBORN_BREATH_WEAPON_ACTION_ID,
    ancestry: lineage.ancestry,
    ancestryLabel: lineage.ancestryLabel,
    damageType: lineage.damageType,
    saveAbility: lineage.breathWeaponSaveType,
    damageDice: getDragonbornBreathWeaponDamageDice(playerSheet.level),
    dc: getDragonbornBreathWeaponDC(playerSheet),
    usesMax,
    usesRemaining,
  };
};

