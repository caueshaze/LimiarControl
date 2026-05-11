import { describe, expect, it } from "vitest";
import {
  buildActiveEffectGroupTitle,
  formatActiveEffectLabel,
  formatCreatureSize,
  formatEffectiveCreatureSize,
  getActiveEffectLifecycleBadges,
  groupActiveEffectsForDisplay,
} from "./activeEffectDisplay";

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

  it("returns until-long-rest badge for until_long_rest duration", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "until_long_rest",
      metadata: {},
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges.map((b) => b.key)).toEqual(["until-long-rest"]);
  });

  it("returns until-short-rest badge for until_short_rest duration", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "until_short_rest",
      metadata: {},
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges.map((b) => b.key)).toEqual(["until-short-rest"]);
  });

  it("returns until-removed badge for until_removed duration", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "until_removed",
      metadata: {},
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges.map((b) => b.key)).toEqual(["until-removed"]);
  });

  it("returns empty array for timed duration without dedicated UI badge", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "timed",
      expires_at_game_time_seconds: 7200,
      metadata: {},
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges).toHaveLength(0);
  });

  it("returns manual + long-rest badges for legacy manual duration", () => {
    const effect = {
      id: "eff-1",
      kind: "spell_effect",
      duration_type: "manual",
      metadata: {},
    };
    const badges = getActiveEffectLifecycleBadges(effect);
    expect(badges.map((b) => b.key)).toEqual(["manual", "long-rest"]);
  });
});

describe("groupActiveEffectsForDisplay", () => {
  const makeEffect = (id: string, groupId: string, type: string, params: Record<string, unknown>) => ({
    id,
    kind: type === "size_modifier" ? "size_modifier" : "spell_effect",
    duration_type: "timed",
    created_at: "2026-05-01T00:00:00Z",
    metadata: {
      source_spell_name: "Aumentar/Reduzir",
      selected_variant_label: "Aumentar",
      declarative_effect_group_id: groupId,
      declarative_effect: { type, params },
    },
  });

  it("groups declarative effects by group id and summarizes children", () => {
    const groups = groupActiveEffectsForDisplay([
      makeEffect("size", "group-a", "size_modifier", { value: 1 }),
      makeEffect("save", "group-a", "advantage_on_saves", { abilities: ["strength"] }),
      makeEffect("damage", "group-a", "modify_weapon_damage", { dice: "1d4", operation: "add" }),
    ]);

    expect(groups).toHaveLength(1);
    expect(groups[0].title).toBe("Aumentar/Reduzir — Aumentar");
    expect(groups[0].summaryLines).toEqual([
      "Tamanho aumentado",
      "Vantagem em salvaguardas de Força",
      "Dano de arma +1d4",
    ]);
  });

  it("does not merge distinct groups from the same spell and variant", () => {
    const groups = groupActiveEffectsForDisplay([
      makeEffect("size-a", "group-a", "size_modifier", { value: 1 }),
      makeEffect("size-b", "group-b", "size_modifier", { value: 1 }),
    ]);

    expect(groups).toHaveLength(2);
    expect(groups.map((group) => group.groupKey)).toEqual(["declarative:group-a", "declarative:group-b"]);
  });

  it("builds group title with graceful fallbacks", () => {
    expect(buildActiveEffectGroupTitle({ effects: [{ metadata: { source_spell_name: "Bless" } }] })).toBe("Bless");
    expect(buildActiveEffectGroupTitle({ effects: [{ metadata: { selected_variant_label: "Aumentar" } }] })).toBe("Aumentar");
    expect(buildActiveEffectGroupTitle({ effects: [{ display_label: "Legacy" }] })).toBe("Legacy");
  });
});

describe("formatCreatureSize", () => {
  it("localizes creature sizes and hides unchanged effective size", () => {
    expect(formatCreatureSize("large", "pt")).toBe("Grande");
    expect(formatEffectiveCreatureSize({ base_size: "medium", effective_size: "large" }, "pt")).toBe(
      "Tamanho atual: Grande (base Médio)",
    );
    expect(formatEffectiveCreatureSize({ base_size: "medium", effective_size: "medium" }, "pt")).toBeNull();
  });
});
