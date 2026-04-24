import { describe, expect, it } from "vitest";
import {
  buildAreaCastPayload,
  buildAreaPreviewPayload,
  createInitialTargetingMode,
  formatAffectedTargetNames,
  getAnchorCombatantIdAtCell,
  isAreaShape,
  resolveAffectedTargetNames,
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
  targetType: "ranged" as const, areaShape: "sphere" as const,
};

const baseParticipant = {
  id: "participant-1",
  kind: "session_entity" as const,
  ref_id: "enemy-1",
  display_name: "Goblin A",
  initiative: 12,
  status: "active" as const,
  team: "enemies" as const,
  visible: true,
  actor_user_id: null,
};

describe("areaTargetingUi", () => {
  it("recognizes fireball as area targeting", () => {
    expect(isAreaShape("sphere")).toBe(true);
    expect(isAreaShape("cylinder")).toBe(true);
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

  it("returns null when actor has no token on the map", () => {
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
        [],
      ),
    ).toBeNull();
  });
});

describe("isAreaShape exhaustive coverage", () => {
  it("recognizes all five area shapes", () => {
    expect(isAreaShape("sphere")).toBe(true);
    expect(isAreaShape("cone")).toBe(true);
    expect(isAreaShape("cube")).toBe(true);
    expect(isAreaShape("cylinder")).toBe(true);
    expect(isAreaShape("line")).toBe(true);
  });

  it("rejects non-area values", () => {
    expect(isAreaShape(null)).toBe(false);
    expect(isAreaShape(undefined)).toBe(false);
    expect(isAreaShape("")).toBe(false);
    expect(isAreaShape("single")).toBe(false);
    expect(isAreaShape("self")).toBe(false);
  });
});

describe("createInitialTargetingMode for each shape", () => {
  it("enters area_target_select for every valid shape", () => {
    for (const shape of ["sphere", "cone", "cube", "cylinder", "line"] as const) {
      expect(createInitialTargetingMode(shape)).toBe("area_target_select");
    }
  });

  it("enters single_target_select for non-area", () => {
    expect(createInitialTargetingMode(null)).toBe("single_target_select");
    expect(createInitialTargetingMode(undefined)).toBe("single_target_select");
  });
});

describe("preview affected cell/target count derivation", () => {
  const deriveCounts = (preview: {
    affected_cells?: Array<{ x: number; y: number }>;
    affected_target_ref_ids?: string[];
    is_valid: boolean;
    reason?: string | null;
  }) => {
    if (!preview.is_valid) return { cellCount: 0, targetCount: 0, reason: preview.reason ?? null };
    return {
      cellCount: preview.affected_cells?.length ?? 0,
      targetCount: preview.affected_target_ref_ids?.length ?? 0,
      reason: null,
    };
  };

  it("derives cell and target counts from valid preview", () => {
    const counts = deriveCounts({
      is_valid: true,
      affected_cells: [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 6, y: 5 }],
      affected_target_ref_ids: ["enemy-1", "enemy-2"],
    });
    expect(counts.cellCount).toBe(3);
    expect(counts.targetCount).toBe(2);
    expect(counts.reason).toBeNull();
  });

  it("returns zero counts for invalid preview with reason", () => {
    const counts = deriveCounts({
      is_valid: false,
      reason: "Anchor out of range",
      affected_cells: [],
      affected_target_ref_ids: [],
    });
    expect(counts.cellCount).toBe(0);
    expect(counts.targetCount).toBe(0);
    expect(counts.reason).toBe("Anchor out of range");
  });

  it("returns zero counts for preview with empty arrays", () => {
    const counts = deriveCounts({
      is_valid: true,
      affected_cells: [],
      affected_target_ref_ids: [],
    });
    expect(counts.cellCount).toBe(0);
    expect(counts.targetCount).toBe(0);
  });
});

describe("affected target preview names", () => {
  it("maps visible affected target refs to token names", () => {
    const names = resolveAffectedTargetNames({
      affectedTargetRefIds: ["enemy-1", "enemy-2"],
      participants: [
        baseParticipant,
        {
          ...baseParticipant,
          id: "participant-2",
          ref_id: "enemy-2",
          display_name: "Orc Brute",
        },
      ],
      tokens: [
        {
          token_id: "token-1",
          label: "Goblin A",
          position: { x: 5, y: 5 },
          combatant_id: "enemy-1",
          controller_type: "session_entity",
        },
        {
          token_id: "token-2",
          label: "Orc Brute",
          position: { x: 6, y: 5 },
          combatant_id: "enemy-2",
          controller_type: "session_entity",
        },
      ],
    });

    expect(names).toEqual(["Goblin A", "Orc Brute"]);
    expect(formatAffectedTargetNames(names)).toBe("Afetados: Goblin A, Orc Brute");
  });

  it("formats empty target lists without crashing", () => {
    expect(
      resolveAffectedTargetNames({
        affectedTargetRefIds: [],
        participants: [baseParticipant],
        tokens: [],
      }),
    ).toEqual([]);
    expect(formatAffectedTargetNames([])).toBe("Nenhum alvo afetado");
  });

  it("uses a safe fallback for unresolved target refs", () => {
    const names = resolveAffectedTargetNames({
      affectedTargetRefIds: ["missing-ref"],
      participants: [baseParticipant],
      tokens: [],
    });

    expect(names).toEqual(["Alvo desconhecido"]);
    expect(formatAffectedTargetNames(names)).toBe("Afetados: Alvo desconhecido");
  });

  it("does not reveal hidden participants to players", () => {
    const names = resolveAffectedTargetNames({
      affectedTargetRefIds: ["enemy-1", "hidden-enemy"],
      participants: [
        baseParticipant,
        {
          ...baseParticipant,
          id: "participant-hidden",
          ref_id: "hidden-enemy",
          display_name: "Hidden Assassin",
          visible: false,
        },
      ],
      tokens: [
        {
          token_id: "token-hidden",
          label: "Hidden Assassin",
          position: { x: 7, y: 5 },
          combatant_id: "hidden-enemy",
          controller_type: "session_entity",
        },
      ],
    });

    expect(names).toEqual(["Goblin A"]);
    expect(names).toHaveLength(1);
    expect(formatAffectedTargetNames(names)).toBe("Afetados: Goblin A");
  });

  it("allows GM views to reveal hidden affected target names", () => {
    const names = resolveAffectedTargetNames({
      affectedTargetRefIds: ["hidden-enemy"],
      canRevealHiddenTargets: true,
      participants: [
        {
          ...baseParticipant,
          id: "participant-hidden",
          ref_id: "hidden-enemy",
          display_name: "Hidden Assassin",
          visible: false,
        },
      ],
      tokens: [
        {
          token_id: "token-hidden",
          label: "Hidden Assassin",
          position: { x: 7, y: 5 },
          combatant_id: "hidden-enemy",
          controller_type: "session_entity",
        },
      ],
    });

    expect(names).toEqual(["Hidden Assassin"]);
  });
});
