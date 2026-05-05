import { describe, expect, it } from "vitest";
import { formatActiveEffectLabel, getActiveEffectLifecycleBadges } from "./activeEffectDisplay";

describe("formatActiveEffectLabel", () => {
  it("returns spellName + variantLabel when both exist", () => {
    const result = formatActiveEffectLabel({
      metadata: { source_spell_name: "Bless", selected_variant_label: "Ally" },
    });
    expect(result).toBe("Bless — Ally");
  });

  it("falls back to variantLabel alone when spellName is missing", () => {
    const result = formatActiveEffectLabel({
      metadata: { selected_variant_label: "Ally" },
    });
    expect(result).toBe("Ally");
  });

  it("falls back to display_label when variantLabel is missing", () => {
    const result = formatActiveEffectLabel({
      display_label: "Owl's Wisdom",
    });
    expect(result).toBe("Owl's Wisdom");
  });

  it("falls back to spellName when display_label is missing", () => {
    const result = formatActiveEffectLabel({
      metadata: { source_spell_name: "Bless" },
    });
    expect(result).toBe("Bless");
  });

  it("falls back to spellKey when all names are missing", () => {
    const result = formatActiveEffectLabel({
      metadata: { source_spell_key: "bless" },
    });
    expect(result).toBe("bless");
  });

  it("returns null when nothing is available", () => {
    const result = formatActiveEffectLabel({});
    expect(result).toBeNull();
  });
});

describe("getActiveEffectLifecycleBadges", () => {
  it("returns concentration + manual + long-rest for concentration manual effect", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "manual",
      metadata: { concentration: true, concentration_group: "grp-1" },
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges.map((b) => b.key)).toEqual(["concentration", "manual", "long-rest"]);
  });

  it("returns manual + long-rest for non-concentration manual effect", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "manual",
      metadata: { source_spell_name: "Cat's Grace" },
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges.map((b) => b.key)).toEqual(["manual", "long-rest"]);
  });

  it("returns rounds badge with count when remaining_rounds is a number", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "rounds",
      remaining_rounds: 3,
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges).toHaveLength(1);
    expect(badges[0].key).toBe("rounds");
    expect(badges[0].params).toEqual({ count: 3 });
  });

  it("returns rounds-unknown badge when remaining_rounds is missing", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "rounds",
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges).toHaveLength(1);
    expect(badges[0].key).toBe("rounds-unknown");
    expect(badges[0].params).toBeUndefined();
  });

  it("returns until-turn-start badge for until_turn_start duration", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "until_turn_start",
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges).toHaveLength(1);
    expect(badges[0].key).toBe("until-turn-start");
  });

  it("returns until-turn-end badge for until_turn_end duration", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "until_turn_end",
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges).toHaveLength(1);
    expect(badges[0].key).toBe("until-turn-end");
  });

  it("returns empty array for unknown duration type", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "unknown",
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges).toHaveLength(0);
  });

  it("returns empty array when duration_type is missing", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges).toHaveLength(0);
  });

  it("returns concentration only for concentration effect without manual duration", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "rounds",
      remaining_rounds: 5,
      metadata: { concentration: true },
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges.map((b) => b.key)).toEqual(["concentration", "rounds"]);
  });
});
