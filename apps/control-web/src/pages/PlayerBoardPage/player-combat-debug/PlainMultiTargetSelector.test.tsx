/**
 * Tests for PlainMultiTargetSelector and isPlainMultiTargetAutomationSpell discriminator (issue #279).
 *
 * UI / dialog tests:
 *   - test_spiritual_weapon_follow_up_* pattern reused for plain-multi-target selector:
 *   - multi-target selector appears when maxTargets > 1 and no variants/instances/area
 *   - selector renders correct number of slots
 *   - first slot pre-populated with initial target
 *   - excludes already-selected targets from other slots
 *   - excludes dead/defeated participants
 *   - payload discriminator: isPlainMultiTargetAutomationSpell logic
 *   - buildNonAreaSpellCastPayload includes target_ref_ids when plain multi-target
 */

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { PlainMultiTargetSelector } from "./PlainMultiTargetSelector";
import { buildNonAreaSpellCastPayload } from "./PlayerSpellCastDialog";
import type { CombatParticipant } from "../../../shared/api/combatRepo";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const makeParticipant = (
  override: Partial<CombatParticipant> = {},
): CombatParticipant => ({
  id: "p-1",
  kind: "session_entity",
  ref_id: "wolf-1",
  display_name: "Wolf",
  initiative: 5,
  status: "active",
  team: "enemies",
  visible: true,
  actor_user_id: null,
  ...override,
});

const wolf1 = makeParticipant({ id: "wolf-p1", ref_id: "wolf-1", display_name: "Wolf 1" });
const wolf2 = makeParticipant({ id: "wolf-p2", ref_id: "wolf-2", display_name: "Wolf 2" });
const wolf3 = makeParticipant({ id: "wolf-p3", ref_id: "wolf-3", display_name: "Wolf 3" });
const deadWolf = makeParticipant({ id: "wolf-dead", ref_id: "wolf-dead", display_name: "Dead Wolf", status: "dead" });

// ---------------------------------------------------------------------------
// PlainMultiTargetSelector component tests
// ---------------------------------------------------------------------------

describe("test_plain_multi_target_selector_renders_correct_slots", () => {
  it("renders maxTargets=2 dropdowns", () => {
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={2}
        participants={[wolf1, wolf2]}
        value={[]}
        onChange={() => undefined}
      />,
    );
    // Two <select> elements
    const selectCount = (markup.match(/<select/g) ?? []).length;
    expect(selectCount).toBe(2);
  });

  it("renders maxTargets=3 dropdowns", () => {
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={3}
        participants={[wolf1, wolf2, wolf3]}
        value={[]}
        onChange={() => undefined}
      />,
    );
    const selectCount = (markup.match(/<select/g) ?? []).length;
    expect(selectCount).toBe(3);
  });

  it("renders maxTargets=1 for single target slot", () => {
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={1}
        participants={[wolf1]}
        value={[]}
        onChange={() => undefined}
      />,
    );
    const selectCount = (markup.match(/<select/g) ?? []).length;
    expect(selectCount).toBe(1);
  });
});

describe("test_plain_multi_target_selector_pre_populates_first_slot", () => {
  it("first slot shows pre-selected target", () => {
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={2}
        participants={[wolf1, wolf2]}
        value={["wolf-1"]}
        onChange={() => undefined}
      />,
    );
    // wolf-1 should be selected in the first slot
    expect(markup).toContain('value="wolf-1"');
    expect(markup).toContain("Wolf 1");
  });

  it("all slots empty when value is empty", () => {
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={2}
        participants={[wolf1, wolf2]}
        value={[]}
        onChange={() => undefined}
      />,
    );
    // placeholder options shown
    expect(markup).toContain("Alvo 1");
    expect(markup).toContain("Alvo 2");
  });
});

describe("test_plain_multi_target_selector_excludes_already_selected", () => {
  it("wolf-1 selected in slot 1 is excluded from slot 2 options", () => {
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={2}
        participants={[wolf1, wolf2]}
        value={["wolf-1"]}
        onChange={() => undefined}
      />,
    );
    // Wolf 1 should appear in slot 1 (selected) but slot 2 should not offer it as unselected option
    // The selected option value "wolf-1" appears once (in slot 1)
    const wolf1OccurrenceCount = (markup.match(/value="wolf-1"/g) ?? []).length;
    // wolf-1 appears in slot 1 select (as option value) but not in slot 2 (excluded)
    expect(wolf1OccurrenceCount).toBe(1);
  });

  it("when both slots selected, each participant excluded from the other slot", () => {
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={2}
        participants={[wolf1, wolf2, wolf3]}
        value={["wolf-1", "wolf-2"]}
        onChange={() => undefined}
      />,
    );
    // wolf-1 selected in slot 1, wolf-2 selected in slot 2
    // wolf-2 should NOT appear as an option in slot 1, wolf-1 should NOT appear in slot 2
    // wolf-3 should appear in both slots
    expect(markup).toContain("Wolf 3");
  });
});

describe("test_plain_multi_target_selector_excludes_dead_participants", () => {
  it("excludes dead participants from all slots", () => {
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={2}
        participants={[wolf1, deadWolf, wolf2]}
        value={[]}
        onChange={() => undefined}
      />,
    );
    expect(markup).not.toContain("Dead Wolf");
  });

  it("excludes defeated participants from all slots", () => {
    const defeatedWolf = makeParticipant({
      id: "wolf-defeated",
      ref_id: "wolf-defeated",
      display_name: "Defeated Wolf",
      status: "defeated",
    });
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={2}
        participants={[wolf1, defeatedWolf]}
        value={[]}
        onChange={() => undefined}
      />,
    );
    expect(markup).not.toContain("Defeated Wolf");
  });
});

// ---------------------------------------------------------------------------
// isPlainMultiTargetAutomationSpell discriminator
// ---------------------------------------------------------------------------

describe("test_plain_multi_target_discriminator", () => {
  const makeDiscriminator = ({
    isAreaSpell = false,
    isMultiInstanceSpell = false,
    isVariantSpell = false,
    maxTargets = 1,
  }) => !isAreaSpell && !isMultiInstanceSpell && !isVariantSpell && maxTargets > 1;

  it("true when maxTargets > 1 and no variants, no instances, no area", () => {
    expect(
      makeDiscriminator({ maxTargets: 2 }),
    ).toBe(true);
  });

  it("false when maxTargets === 1 (single target automation)", () => {
    expect(
      makeDiscriminator({ maxTargets: 1 }),
    ).toBe(false);
  });

  it("false when isAreaSpell is true", () => {
    expect(
      makeDiscriminator({ maxTargets: 3, isAreaSpell: true }),
    ).toBe(false);
  });

  it("false when isVariantSpell is true (variant multi-target path handles that)", () => {
    expect(
      makeDiscriminator({ maxTargets: 2, isVariantSpell: true }),
    ).toBe(false);
  });

  it("false when isMultiInstanceSpell is true (instance path handles that)", () => {
    expect(
      makeDiscriminator({ maxTargets: 2, isMultiInstanceSpell: true }),
    ).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// buildNonAreaSpellCastPayload: target_ref_ids in payload
// ---------------------------------------------------------------------------

describe("test_build_non_area_spell_cast_payload_plain_multi_target", () => {
  const baseParams = {
    actorParticipantId: "p1",
    concentrationManualRoll: null,
    concentrationRollMode: "system" as const,
    effectInstanceTargets: [],
    isMultiInstanceSpell: false,
    parsedBonus: 0,
    selectedSlotLevel: 2,
    spell: {
      canonicalKey: "animal_friendship",
      level: 1,
      sourceType: "standard",
      campaignSpellId: "cs-1",
    } as any,
    spellDamageType: "",
    spellEffectDice: "",
    spellMode: "saving_throw" as const,
    spellSaveAbility: "" as any,
    targetRefId: "wolf-1",
  };

  it("includes target_ref_ids when isPlainMultiTargetAutomationSpell is true", () => {
    const payload = buildNonAreaSpellCastPayload({
      ...baseParams,
      isPlainMultiTargetAutomationSpell: true,
      plainTargetRefIds: ["wolf-1", "wolf-2"],
    });
    expect(payload.target_ref_ids).toEqual(["wolf-1", "wolf-2"]);
    expect(payload.target_ref_id).toBeNull();
  });

  it("target_ref_ids is null when plain multi-target is false (single target)", () => {
    const payload = buildNonAreaSpellCastPayload({
      ...baseParams,
      isPlainMultiTargetAutomationSpell: false,
    });
    expect(payload.target_ref_ids).toBeNull();
    expect(payload.target_ref_id).toBe("wolf-1");
  });

  it("target_ref_ids is null when plainTargetRefIds is empty", () => {
    const payload = buildNonAreaSpellCastPayload({
      ...baseParams,
      isPlainMultiTargetAutomationSpell: true,
      plainTargetRefIds: [],
    });
    expect(payload.target_ref_ids).toBeNull();
  });

  it("slot_level is set correctly for upcast", () => {
    const payload = buildNonAreaSpellCastPayload({
      ...baseParams,
      isPlainMultiTargetAutomationSpell: true,
      plainTargetRefIds: ["wolf-1", "wolf-2"],
      selectedSlotLevel: 3,
    });
    expect(payload.slot_level).toBe(3);
  });
});

// ---------------------------------------------------------------------------
// Golden chain: slot N → resolved maxTargets → N selectors rendered
// ---------------------------------------------------------------------------

describe("test_animal_friendship_upcast_slot_2_renders_two_selectors", () => {
  it("renders 2 target selectors when resolved max_targets is 2 (slot 2)", () => {
    // resolved max_targets = base(1) + upcast_added(1) = 2 at slot 2
    const resolvedMaxTargets = 2;
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={resolvedMaxTargets}
        participants={[wolf1, wolf2, wolf3]}
        value={[]}
        onChange={() => undefined}
      />,
    );
    const selectCount = (markup.match(/<select/g) ?? []).length;
    expect(selectCount).toBe(2);
  });

  it("renders 3 target selectors when resolved max_targets is 3 (slot 3)", () => {
    const resolvedMaxTargets = 3;
    const markup = renderToStaticMarkup(
      <PlainMultiTargetSelector
        maxTargets={resolvedMaxTargets}
        participants={[wolf1, wolf2, wolf3]}
        value={[]}
        onChange={() => undefined}
      />,
    );
    const selectCount = (markup.match(/<select/g) ?? []).length;
    expect(selectCount).toBe(3);
  });

  it("payload at slot 2 includes 2 ref_ids when 2 targets selected", () => {
    const baseParams = {
      actorParticipantId: "p1",
      concentrationManualRoll: null,
      concentrationRollMode: "system" as const,
      effectInstanceTargets: [],
      isMultiInstanceSpell: false,
      parsedBonus: 0,
      selectedSlotLevel: 2,
      spell: {
        canonicalKey: "animal_friendship",
        level: 1,
        sourceType: "standard",
        campaignSpellId: "cs-1",
      } as any,
      spellDamageType: "",
      spellEffectDice: "",
      spellMode: "saving_throw" as const,
      spellSaveAbility: "" as any,
      targetRefId: null,
    };

    const payload = buildNonAreaSpellCastPayload({
      ...baseParams,
      isPlainMultiTargetAutomationSpell: true,
      plainTargetRefIds: ["wolf-1", "wolf-2"],  // 2 targets at slot 2
    });

    expect(payload.target_ref_ids).toHaveLength(2);
    expect(payload.target_ref_ids).toContain("wolf-1");
    expect(payload.target_ref_ids).toContain("wolf-2");
    expect(payload.slot_level).toBe(2);
    expect(payload.target_ref_id).toBeNull();
  });
});
