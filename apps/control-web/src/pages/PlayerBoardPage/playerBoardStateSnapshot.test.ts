import { describe, expect, it } from "vitest";
import { INITIAL_SHEET } from "../../features/character-sheet/model/initialSheet";
import { parsePlayerBoardStateSnapshot } from "./playerBoardStateSnapshot";

describe("parsePlayerBoardStateSnapshot", () => {
  const baseState = {
    ...INITIAL_SHEET,
    name: "Ayla",
    class: "cleric",
    level: 5,
    background: "acolyte",
    playerName: "Player",
    race: "human",
    alignment: "NG",
    experiencePoints: 0,
    pendingLevelUp: false,
    abilities: {
      ...INITIAL_SHEET.abilities,
      strength: 10,
      wisdom: 16,
    },
    currency: {
      cp: 1,
      sp: 2,
      gp: 3,
      ep: 0,
      pp: 0,
    },
  };

  it("derives pending spell preparation and concentration from realtime session state", () => {
    const snapshot = parsePlayerBoardStateSnapshot({
      state: {
        ...baseState,
        active_spell_effects: [
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "until_long_rest",
            created_at: "2026-01-01T00:00:00+00:00",
            metadata: {
              concentration: true,
              concentration_group: "grp-1",
              source_spell_key: "bless",
              source_spell_name: "Bless",
              selected_variant_key: "base",
              selected_variant_label: "Base",
            },
          },
          {
            id: "eff-2",
            kind: "spell_effect",
            duration_type: "until_long_rest",
            created_at: "2026-01-01T00:00:00+00:00",
            metadata: {
              concentration: true,
              concentration_group: "grp-1",
            },
          },
        ],
        pending_spell_preparation: {
          source: "long_rest",
          class_key: "cleric",
          prepared_limit: 8,
          current_prepared_spell_ids: ["s1", "s2"],
          created_at: "2026-01-01T00:00:00+00:00",
          available_during_rest: true,
        },
      },
    });

    expect(snapshot).not.toBeNull();
    expect(snapshot?.pendingSpellPreparation).toEqual({
      source: "long_rest",
      classKey: "cleric",
      preparedLimit: 8,
      currentPreparedSpellIds: ["s1", "s2"],
      createdAt: "2026-01-01T00:00:00+00:00",
      availableDuringRest: true,
    });
    expect(snapshot?.activeSpellEffects).toHaveLength(2);
    expect(snapshot?.activeConcentration).toEqual({
      spellKey: "bless",
      spellName: "Bless",
      variantKey: "base",
      variantLabel: "Base",
      concentrationGroup: "grp-1",
      effectIds: ["eff-1", "eff-2"],
    });
    expect(snapshot?.playerWallet.copperValue).toBe(321);
  });

  it("respects explicit top-level null fields when a state update clears them", () => {
    const snapshot = parsePlayerBoardStateSnapshot({
      state: {
        ...baseState,
        currency: {
          cp: 0,
          sp: 0,
          gp: 0,
          ep: 0,
          pp: 0,
        },
      },
      activeConcentration: null,
      activeSpellEffects: null,
      pendingSpellPreparation: null,
    });

    expect(snapshot).not.toBeNull();
    expect(snapshot?.pendingSpellPreparation).toBeNull();
    expect(snapshot?.activeSpellEffects).toBeNull();
    expect(snapshot?.activeConcentration).toBeNull();
  });
});
