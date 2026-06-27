import type { CharacterSheet } from "../../character-sheet/model/characterSheet.types";

export const DRAGON_WINGS_ACTION_ID = "dragon_wings";
export const DRAGON_WINGS_MIN_LEVEL = 14;

export type DragonWingsAction = {
  id: typeof DRAGON_WINGS_ACTION_ID;
  active: boolean;
  flySpeedMeters: number;
};

const isDraconicBloodlineSorcerer = (sheet: CharacterSheet): boolean =>
  String(sheet.class ?? "").trim().toLowerCase() === "sorcerer" &&
  String(sheet.subclass ?? "").trim().toLowerCase() === "draconic_bloodline";

/**
 * Dragon Wings (Draconic Bloodline 14+): bonus-action flight toggle. Returns
 * null when the feature is unavailable (not a draconic sorcerer or below
 * level 14), so the UI only surfaces it when eligible.
 */
export const buildDragonWingsAction = (
  playerSheet?: CharacterSheet | null,
): DragonWingsAction | null => {
  if (!playerSheet) {
    return null;
  }
  if (!isDraconicBloodlineSorcerer(playerSheet) || (playerSheet.level ?? 0) < DRAGON_WINGS_MIN_LEVEL) {
    return null;
  }

  const active = playerSheet.dragonWings?.active === true;
  const walkSpeed = Math.max(0, playerSheet.speedMeters ?? 0);

  return {
    id: DRAGON_WINGS_ACTION_ID,
    active,
    flySpeedMeters: active ? walkSpeed : 0,
  };
};
