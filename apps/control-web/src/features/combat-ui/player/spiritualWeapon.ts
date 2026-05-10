import type { CombatMapPreviewToken, CombatParticipant, CombatSpellAnchor } from "../../../shared/api/combatRepo";
import { METERS_PER_CELL } from "../hooks/useTargetingPreview";
import type { SpellMapHighlight } from "../map/combatMapHighlight.types";

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

// Chebyshev: matches tactical engine (coordinates.ts) and spellMapPreviewModel.ts
const chebyshevCells = (ax: number, ay: number, bx: number, by: number): number =>
  Math.max(Math.abs(bx - ax), Math.abs(by - ay));

export const buildSpiritualWeaponReachableCells = (
  origin: { x: number; y: number },
  maxMeters: number,
): Array<{ x: number; y: number }> => {
  const maxCells = Math.floor(maxMeters / METERS_PER_CELL);
  const cells: Array<{ x: number; y: number }> = [];
  for (let dx = -maxCells; dx <= maxCells; dx++) {
    for (let dy = -maxCells; dy <= maxCells; dy++) {
      if (chebyshevCells(0, 0, dx, dy) <= maxCells) {
        cells.push({ x: origin.x + dx, y: origin.y + dy });
      }
    }
  }
  return cells;
};

export const buildSpiritualWeaponHighlights = (
  anchorPosition: { x: number; y: number },
  selectedDestination: { x: number; y: number } | null,
  validTargets: CombatParticipant[],
): SpellMapHighlight[] => {
  const highlights: SpellMapHighlight[] = [
    { kind: "area-cell", status: "partial", cell: anchorPosition },
  ];
  if (selectedDestination) {
    highlights.push({ kind: "area-cell", status: "valid", cell: selectedDestination });
  }
  for (const target of validTargets) {
    highlights.push({ kind: "affected-token", status: "valid", targetRefId: target.ref_id });
  }
  return highlights;
};

export const buildSpiritualWeaponValidTargets = ({
  participants,
  finalAnchorPosition,
  actorParticipantId,
  mapTokens,
}: {
  participants: CombatParticipant[];
  finalAnchorPosition: { x: number; y: number };
  actorParticipantId: string | null | undefined;
  mapTokens: CombatMapPreviewToken[];
}): CombatParticipant[] => {
  const adjacentRefIds = new Set(
    mapTokens
      .filter(
        (t) =>
          t.combatant_id != null &&
          chebyshevCells(t.position.x, t.position.y, finalAnchorPosition.x, finalAnchorPosition.y) <= 1,
      )
      .map((t) => t.combatant_id!),
  );
  return participants.filter(
    (p) =>
      p.id !== actorParticipantId &&
      p.status !== "dead" &&
      p.status !== "defeated" &&
      adjacentRefIds.has(p.ref_id),
  );
};
