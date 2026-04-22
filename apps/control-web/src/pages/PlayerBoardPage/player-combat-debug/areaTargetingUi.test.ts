import { describe, expect, it } from "vitest";
import {
  buildAreaCastPayload,
  buildAreaPreviewPayload,
  createInitialTargetingMode,
  getAnchorCombatantIdAtCell,
  isAreaTargetMode,
  resolveActorOriginCell,
} from "./areaTargetingUi";

const baseSpell = {
  id: "spell-1",
  name: "Fireball",
  canonicalKey: "fireball",
  level: 3,
  prepared: true,
  actionCost: "action" as const,
  suggestedMode: "saving_throw" as const,
  damageType: "fire",
  savingThrow: "dexterity",
  availableSlotLevels: [3, 4, 5],
  targetMode: "sphere" as const,
};

describe("areaTargetingUi", () => {
  it("recognizes fireball as area targeting", () => {
    expect(isAreaTargetMode("sphere")).toBe(true);
    expect(isAreaTargetMode("cylinder")).toBe(true);
    expect(createInitialTargetingMode("sphere")).toBe("area_target_select");
    expect(createInitialTargetingMode("cylinder")).toBe("area_target_select");
    expect(createInitialTargetingMode("single")).toBe("single_target_select");
  });

  it("finds the combatant anchored on a clicked cell", () => {
    expect(
      getAnchorCombatantIdAtCell(
        [
          {
            token_id: "token-1",
            label: "Goblin",
            position: { x: 4, y: 6 },
            combatant_id: "enemy-1",
            controller_type: "session_entity",
          },
        ],
        { x: 4, y: 6 },
      ),
    ).toBe("enemy-1");
  });

  it("builds preview and cast payloads with explicit origin and anchor cells", () => {
    const preview = buildAreaPreviewPayload({
      actorParticipantId: "participant-1",
      spell: baseSpell,
      spellMode: "saving_throw",
      selectedSlotLevel: 3,
      originCell: { x: 1, y: 1 },
      anchorCell: { x: 5, y: 5 },
      targetRefId: "enemy-1",
    });
    expect(preview.origin_cell).toEqual({ x: 1, y: 1 });
    expect(preview.anchor_cell).toEqual({ x: 5, y: 5 });
    expect(preview.target_ref_id).toBe("enemy-1");

    const cast = buildAreaCastPayload({
      actorParticipantId: "participant-1",
      spell: baseSpell,
      spellMode: "saving_throw",
      selectedSlotLevel: 3,
      originCell: { x: 1, y: 1 },
      anchorCell: { x: 5, y: 5 },
      targetRefId: "enemy-1",
      spellEffectDice: "8d6",
      spellEffectBonus: 0,
      spellDamageType: "fire",
      spellSaveAbility: "dexterity",
      concentrationRollSource: "system",
    });
    expect(cast.origin_cell).toEqual({ x: 1, y: 1 });
    expect(cast.anchor_cell).toEqual({ x: 5, y: 5 });
    expect(cast.target_ref_id).toBe("enemy-1");
    expect(cast.spell_canonical_key).toBe("fireball");
  });

  it("buildAreaCastPayload forwards campaignSpellId", () => {
    const spellWithCampaignId = {
      ...baseSpell,
      campaignSpellId: "cs-fireball",
    };
    const cast = buildAreaCastPayload({
      actorParticipantId: "participant-1",
      spell: spellWithCampaignId,
      spellMode: "saving_throw",
      selectedSlotLevel: 3,
      originCell: { x: 1, y: 1 },
      anchorCell: { x: 5, y: 5 },
      targetRefId: "enemy-1",
      spellEffectDice: "8d6",
      spellEffectBonus: 0,
      spellDamageType: "fire",
      spellSaveAbility: "dexterity",
      concentrationRollSource: "system",
    });
    expect(cast.campaign_spell_id).toBe("cs-fireball");
    expect(cast.spell_canonical_key).toBe("fireball");
  });

  it("buildAreaCastPayload sends null campaignSpellId for legacy entries", () => {
    const cast = buildAreaCastPayload({
      actorParticipantId: "participant-1",
      spell: baseSpell,
      spellMode: "saving_throw",
      selectedSlotLevel: 3,
      originCell: { x: 1, y: 1 },
      anchorCell: { x: 5, y: 5 },
      targetRefId: "enemy-1",
      spellEffectDice: "8d6",
      spellEffectBonus: 0,
      spellDamageType: "fire",
      spellSaveAbility: "dexterity",
      concentrationRollSource: "system",
    });
    expect(cast.campaign_spell_id).toBeNull();
  });

  it("resolves the caster origin cell from the map snapshot", () => {
    expect(
      resolveActorOriginCell(
        {
          id: "participant-1",
          kind: "player",
          ref_id: "player-1",
          display_name: "Mage",
          initiative: 12,
          status: "active",
          team: "players",
          visible: true,
          actor_user_id: "user-1",
        },
        [
          {
            token_id: "token-player",
            label: "Mage",
            position: { x: 2, y: 3 },
            combatant_id: "player-1",
            controller_type: "player",
          },
        ],
      ),
    ).toEqual({ x: 2, y: 3 });
  });
});
