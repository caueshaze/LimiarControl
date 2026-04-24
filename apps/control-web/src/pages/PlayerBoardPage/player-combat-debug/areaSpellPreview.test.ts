import { beforeEach, describe, expect, it, vi } from "vitest";
import { combatRepo } from "../../../shared/api/combatRepo";
import { http } from "../../../shared/api/http";
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
});
