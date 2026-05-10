import type { CombatSpellAnchor } from "../../../shared/api/combatRepo";

export type SpiritualWeaponFollowUpAction = {
  anchorId: string;
  position: { x: number; y: number };
  remainingRounds: number | null | undefined;
  maxMovementMeters: number;
};

export const buildSpiritualWeaponFollowUpAction = (
  spellAnchors: CombatSpellAnchor[] | undefined | null,
  myParticipantId: string | undefined | null,
): SpiritualWeaponFollowUpAction | null => {
  if (!myParticipantId) return null;
  const anchor = spellAnchors?.find(
    (a) =>
      a.source_spell_key === "spiritual_weapon" &&
      a.owner_participant_id === myParticipantId,
  );
  if (!anchor) return null;
  return {
    anchorId: anchor.id,
    position: anchor.position,
    remainingRounds: anchor.remaining_rounds,
    maxMovementMeters: anchor.movement?.max_meters_per_follow_up ?? 6,
  };
};
