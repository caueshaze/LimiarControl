import { describe, expect, it } from "vitest";
import { buildSpiritualWeaponFollowUpAction } from "./spiritualWeapon";
import type { CombatSpellAnchor } from "../../../shared/api/combatRepo";

const makeAnchor = (override: Partial<CombatSpellAnchor> = {}): CombatSpellAnchor => ({
  id: "anchor-1",
  source_spell_key: "spiritual_weapon",
  source_spell_name: "Arma Espiritual",
  owner_participant_id: "p1",
  created_by_participant_id: "p1",
  position: { x: 5, y: 5 },
  duration_type: "rounds",
  remaining_rounds: 8,
  expires_on: "turn_start",
  expires_at_participant_id: "p1",
  render_kind: "spiritual_weapon",
  movement: { max_meters_per_follow_up: 6 },
  metadata: {},
  ...override,
});

describe("buildSpiritualWeaponFollowUpAction", () => {
  it("returns action when owned spiritual_weapon anchor exists", () => {
    const action = buildSpiritualWeaponFollowUpAction([makeAnchor()], "p1");
    expect(action).not.toBeNull();
    expect(action?.anchorId).toBe("anchor-1");
    expect(action?.position).toEqual({ x: 5, y: 5 });
    expect(action?.remainingRounds).toBe(8);
    expect(action?.maxMovementMeters).toBe(6);
  });

  it("returns null when there are no anchors", () => {
    expect(buildSpiritualWeaponFollowUpAction([], "p1")).toBeNull();
    expect(buildSpiritualWeaponFollowUpAction(null, "p1")).toBeNull();
    expect(buildSpiritualWeaponFollowUpAction(undefined, "p1")).toBeNull();
  });

  it("returns null when participant has no spiritual_weapon anchor", () => {
    const anchor = makeAnchor({ source_spell_key: "hunters_mark" });
    expect(buildSpiritualWeaponFollowUpAction([anchor], "p1")).toBeNull();
  });

  it("returns null when anchor belongs to a different owner", () => {
    const anchor = makeAnchor({ owner_participant_id: "p2" });
    expect(buildSpiritualWeaponFollowUpAction([anchor], "p1")).toBeNull();
  });

  it("returns null when myParticipantId is null or undefined", () => {
    expect(buildSpiritualWeaponFollowUpAction([makeAnchor()], null)).toBeNull();
    expect(buildSpiritualWeaponFollowUpAction([makeAnchor()], undefined)).toBeNull();
  });

  it("uses default 6m movement when movement field is absent", () => {
    const anchor = makeAnchor({ movement: null });
    const action = buildSpiritualWeaponFollowUpAction([anchor], "p1");
    expect(action?.maxMovementMeters).toBe(6);
  });

  it("picks the correct anchor when multiple anchors exist", () => {
    const otherAnchor = makeAnchor({
      id: "anchor-other",
      source_spell_key: "hunters_mark",
    });
    const action = buildSpiritualWeaponFollowUpAction([otherAnchor, makeAnchor()], "p1");
    expect(action?.anchorId).toBe("anchor-1");
  });
});
