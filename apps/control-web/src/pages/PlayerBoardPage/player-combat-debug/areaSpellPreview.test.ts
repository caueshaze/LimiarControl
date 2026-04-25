import { beforeEach, describe, expect, it, vi } from "vitest";
import { combatRepo } from "../../../shared/api/combatRepo";
import { http } from "../../../shared/api/http";
import { toCombatMapFrameAreaEffects } from "../../../features/combat-ui/map/CombatMapFrame";
import { buildAreaCastPayload, buildAreaPreviewPayload } from "./areaTargetingUi";

vi.mock("../../../shared/api/http", () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
  },
}));

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

describe("combatRepo area-spell endpoints", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("posts area preview requests to the cast/preview endpoint", async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      is_valid: true,
      reason: null,
      shape: "sphere",
      affected_cells: [{ x: 5, y: 5 }],
      affected_target_ref_ids: ["enemy-1"],
      affected_token_ids: ["tok_1"],
    } as never);

    const payload = buildAreaPreviewPayload({
      actorParticipantId: "participant-1",
      spell: baseSpell,
      spellMode: "saving_throw",
      selectedSlotLevel: 3,
      originCell: { x: 1, y: 1 },
      anchorCell: { x: 5, y: 5 },
      targetRefId: "enemy-1",
    });
    await combatRepo.previewAreaSpell("session-1", payload);

    expect(http.post).toHaveBeenCalledWith(
      "/sessions/session-1/combat/action/cast/preview",
      payload,
    );
  });

  it("posts confirmed area casts to the cast endpoint", async () => {
    vi.mocked(http.post).mockResolvedValueOnce({ action_kind: "saving_throw" } as never);

    const payload = buildAreaCastPayload({
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
    await combatRepo.castSpell("session-1", payload);

    expect(http.post).toHaveBeenCalledWith(
      "/sessions/session-1/combat/action/cast",
      payload,
    );
  });
});

describe("area preview/cast payload parity", () => {
  it("preview and cast payloads share the same targeting fields for identical inputs", () => {
    const commonArgs = {
      actorParticipantId: "participant-1",
      spell: baseSpell,
      spellMode: "saving_throw" as const,
      selectedSlotLevel: 4,
      originCell: { x: 2, y: 2 },
      anchorCell: { x: 7, y: 9 },
      targetRefId: "enemy-2",
    };

    const preview = buildAreaPreviewPayload(commonArgs);
    const cast = buildAreaCastPayload({
      ...commonArgs,
      spellEffectDice: "8d6",
      spellEffectBonus: 0,
      spellDamageType: "fire",
      spellSaveAbility: "dexterity",
      concentrationRollSource: "system",
    });

    expect(cast.actor_participant_id).toBe(preview.actor_participant_id);
    expect(cast.origin_cell).toEqual(preview.origin_cell);
    expect(cast.anchor_cell).toEqual(preview.anchor_cell);
    expect(cast.target_ref_id).toBe(preview.target_ref_id);
    expect(cast.spell_canonical_key).toBe(preview.spell_canonical_key);
    expect(cast.spell_mode).toBe(preview.spell_mode);
    expect(cast.slot_level).toBe(preview.slot_level);
    expect(cast.inventory_item_id).toBe(preview.inventory_item_id);
  });
});

describe("area targeting confirmation gate", () => {
  const canSubmitArea = (
    anchorCell: unknown,
    originCell: unknown,
    preview: { is_valid: boolean } | null,
  ) => Boolean(anchorCell && originCell && preview?.is_valid);

  it("blocks confirmation until anchor, origin, and a valid preview are all present", () => {
    expect(canSubmitArea(null, { x: 1, y: 1 }, { is_valid: true })).toBe(false);
    expect(canSubmitArea({ x: 5, y: 5 }, null, { is_valid: true })).toBe(false);
    expect(canSubmitArea({ x: 5, y: 5 }, { x: 1, y: 1 }, null)).toBe(false);
    expect(canSubmitArea({ x: 5, y: 5 }, { x: 1, y: 1 }, { is_valid: false })).toBe(false);
    expect(canSubmitArea({ x: 5, y: 5 }, { x: 1, y: 1 }, { is_valid: true })).toBe(true);
  });

  it("blocks when preview is invalid (is_valid: false)", () => {
    expect(canSubmitArea({ x: 5, y: 5 }, { x: 1, y: 1 }, { is_valid: false })).toBe(false);
  });

  it("blocks when preview is null (still loading)", () => {
    expect(canSubmitArea({ x: 5, y: 5 }, { x: 1, y: 1 }, null)).toBe(false);
  });

  it("blocks when anchor is cleared after a valid preview", () => {
    expect(canSubmitArea(null, { x: 1, y: 1 }, { is_valid: true })).toBe(false);
  });
});

describe("persistent area overlays", () => {
  it("maps Control active area effects to embedded map overlay payloads", () => {
    const effects = toCombatMapFrameAreaEffects([
      {
        id: "area_effect:1",
        source_spell_canonical_key: "fog_cloud",
        source_spell_name: "Fog Cloud",
        caster_participant_id: "p1",
        caster_ref_id: "player-1",
        origin_point: { x: 10, y: 10 },
        anchor_cell: { x: 10, y: 10 },
        area_shape: "sphere",
        size_meters: 6,
        radius_meters: 6,
        affected_cells: [{ x: 10, y: 10 }],
        effect_kind: "obscurement",
        obscurement: "heavily_obscured",
      },
    ]);

    expect(effects).toEqual([
      expect.objectContaining({
        id: "area_effect:1",
        sourceSpellCanonicalKey: "fog_cloud",
        sourceSpellName: "Fog Cloud",
        anchorCell: { x: 10, y: 10 },
        affectedCells: [{ x: 10, y: 10 }],
        effectKind: "obscurement",
      }),
    ]);
  });
});

describe("area preview/cast payload parity for cone and cube", () => {
  const coneSpell = {
    ...baseSpell,
    canonicalKey: "burning_hands",
    name: "Burning Hands",
    level: 1,
    areaShape: "cone" as const,
  };

  const cubeSpell = {
    ...baseSpell,
    canonicalKey: "thunderwave",
    name: "Thunderwave",
    level: 1,
    areaShape: "cube" as const,
  };

  it("preview and cast payloads share targeting fields for cone", () => {
    const commonArgs = {
      actorParticipantId: "participant-1",
      spell: coneSpell,
      spellMode: "saving_throw" as const,
      selectedSlotLevel: 1,
      originCell: { x: 2, y: 2 },
      anchorCell: { x: 3, y: 2 },
      targetRefId: null,
    };
    const preview = buildAreaPreviewPayload(commonArgs);
    const cast = buildAreaCastPayload({
      ...commonArgs,
      spellEffectDice: "3d6",
      spellEffectBonus: 0,
      spellDamageType: "fire",
      spellSaveAbility: "dexterity",
      concentrationRollSource: "system",
    });
    expect(cast.origin_cell).toEqual(preview.origin_cell);
    expect(cast.anchor_cell).toEqual(preview.anchor_cell);
    expect(cast.spell_canonical_key).toBe(preview.spell_canonical_key);
  });

  it("preview and cast payloads share targeting fields for cube", () => {
    const commonArgs = {
      actorParticipantId: "participant-1",
      spell: cubeSpell,
      spellMode: "saving_throw" as const,
      selectedSlotLevel: 1,
      originCell: { x: 5, y: 5 },
      anchorCell: { x: 6, y: 6 },
      targetRefId: null,
    };
    const preview = buildAreaPreviewPayload(commonArgs);
    const cast = buildAreaCastPayload({
      ...commonArgs,
      spellEffectDice: "2d8",
      spellEffectBonus: 0,
      spellDamageType: "thunder",
      spellSaveAbility: "constitution",
      concentrationRollSource: "system",
    });
    expect(cast.origin_cell).toEqual(preview.origin_cell);
    expect(cast.anchor_cell).toEqual(preview.anchor_cell);
    expect(cast.spell_canonical_key).toBe(preview.spell_canonical_key);
  });
});
