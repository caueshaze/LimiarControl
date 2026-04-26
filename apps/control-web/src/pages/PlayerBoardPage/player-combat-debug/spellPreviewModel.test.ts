import { describe, expect, it } from "vitest";
import { buildSpellPreviewModel } from "./spellPreviewModel";
import type { CombatResolvedSpellContext } from "../../../shared/api/combatRepo";

const baseFallbackSpell = {
  areaShape: null,
  cantripScaling: null,
  characterLevel: 5,
  damageType: "Force",
  level: 1,
  rangeMeters: 36,
  savingThrow: null,
  selectionType: "creature" as const,
  targetType: "ranged" as const,
  upcast: null,
};

const resolvedContextDefaults: CombatResolvedSpellContext = {
  spell_name: "Magic Missile",
  spell_level: 1,
  resolution_type: "direct_damage",
  requires_attack_roll: false,
  requires_saving_throw: false,
  effect_instance_count: 1,
  upcast_applied: false,
  upcast_added_instances: 0,
};

describe("buildSpellPreviewModel", () => {
  it("uses Magic Missile slot 3 effect_instance_count = 5 from resolvedContext", () => {
    const model = buildSpellPreviewModel(
      {
        ...resolvedContextDefaults,
        slot_level: 3,
        effect_instance_count: 5,
        effect_instance_dice: "1d4+1",
        damage_preview: "5d4+5",
        damage_type: "force",
        target_type: "ranged",
        range_meters: 36,
        upcast_applied: true,
        upcast_added_instances: 2,
      },
      {
        spell: {
          ...baseFallbackSpell,
          upcast: {
            mode: "additional_effect_instances",
            dice: "1d4+1",
            perLevel: 1,
            baseEffectInstances: 3,
          },
        },
        selectedSlotLevel: 3,
        spellMode: "direct_damage",
        spellEffectDice: "3d4+3",
      },
    );

    expect(model.source).toBe("resolved");
    expect(model.effectInstanceCount).toBe(5);
    expect(model.effectInstanceDice).toBe("1d4+1");
    expect(model.damagePreview).toBe("5d4+5");
    expect(model.rangeMeters).toBe(36);
  });

  it("uses Eldritch Blast caster level 5 effect_instance_count = 2 from resolvedContext", () => {
    const model = buildSpellPreviewModel(
      {
        ...resolvedContextDefaults,
        spell_name: "Eldritch Blast",
        spell_level: 0,
        slot_level: null,
        resolution_type: "spell_attack",
        requires_attack_roll: true,
        effect_instance_count: 2,
        effect_instance_dice: "1d10",
        damage_preview: "2d10",
        damage_type: "force",
      },
      {
        spell: {
          ...baseFallbackSpell,
          level: 0,
          damageType: "Force",
          targetType: "ranged",
          cantripScaling: {
            scalingMode: "character_level",
            scalingEffectType: "effect_instances",
            thresholds: [
              { characterLevel: 1, instances: 1, instanceDamage: { dice: "1d10" } },
              { characterLevel: 5, instances: 2, instanceDamage: { dice: "1d10" } },
            ],
          },
        },
        selectedSlotLevel: null,
        spellMode: "spell_attack",
        spellEffectDice: "1d10",
      },
    );

    expect(model.effectInstanceCount).toBe(2);
    expect(model.effectInstanceDice).toBe("1d10");
    expect(model.damagePreview).toBe("2d10");
    expect(model.requiresAttackRoll).toBe(true);
    expect(model.resolutionType).toBe("spell_attack");
  });

  it("uses Acid Splash resolution_type = saving_throw and effect_instance_count = 1", () => {
    const model = buildSpellPreviewModel(
      {
        ...resolvedContextDefaults,
        spell_name: "Acid Splash",
        spell_level: 0,
        slot_level: null,
        resolution_type: "saving_throw",
        requires_attack_roll: false,
        requires_saving_throw: true,
        save_ability: "dexterity",
        damage_preview: "2d6",
        damage_type: "acid",
        effect_instance_count: 1,
        effect_instance_dice: null,
      },
      {
        spell: {
          ...baseFallbackSpell,
          level: 0,
          damageType: "Acid",
          savingThrow: "DEX",
        },
        selectedSlotLevel: null,
        spellMode: "saving_throw",
        spellEffectDice: "1d6",
      },
    );

    expect(model.resolutionType).toBe("saving_throw");
    expect(model.requiresSavingThrow).toBe(true);
    expect(model.requiresAttackRoll).toBe(false);
    expect(model.saveAbility).toBe("dexterity");
    expect(model.effectInstanceCount).toBe(1);
    expect(model.effectInstanceDice).toBeNull();
    expect(model.damagePreview).toBe("2d6");
  });

  it("does not let fallback override fields present on resolvedContext", () => {
    const model = buildSpellPreviewModel(
      {
        ...resolvedContextDefaults,
        effect_instance_count: 3,
        effect_instance_dice: "1d4+1",
        damage_preview: "3d4+3",
        damage_type: "force",
        target_type: "ranged",
        range_meters: 30,
        area_shape: null,
        area_size_meters: null,
      },
      {
        spell: {
          ...baseFallbackSpell,
          rangeMeters: 999,
          damageType: "ShouldNotWin",
          areaShape: "sphere",
          upcast: {
            mode: "additional_effect_instances",
            dice: "9d9",
            perLevel: 9,
            baseEffectInstances: 9,
          },
        },
        selectedSlotLevel: 9,
        spellMode: "direct_damage",
        spellEffectDice: "shouldNotWin",
      },
    );

    expect(model.effectInstanceCount).toBe(3);
    expect(model.effectInstanceDice).toBe("1d4+1");
    expect(model.damagePreview).toBe("3d4+3");
    expect(model.damageType).toBe("force");
    expect(model.rangeMeters).toBe(30);
    expect(model.areaShape).toBeNull();
  });

  it("does not recalculate scaling when resolvedContext is provided", () => {
    const model = buildSpellPreviewModel(
      {
        ...resolvedContextDefaults,
        effect_instance_count: 3,
        effect_instance_dice: "1d4+1",
      },
      {
        spell: {
          ...baseFallbackSpell,
          upcast: {
            mode: "additional_effect_instances",
            dice: "1d4+1",
            perLevel: 1,
            baseEffectInstances: 3,
          },
        },
        selectedSlotLevel: 9,
        spellMode: "direct_damage",
        spellEffectDice: "3d4+3",
      },
    );

    expect(model.effectInstanceCount).toBe(3);
  });

  it("falls back to spell metadata when resolvedContext is null", () => {
    const model = buildSpellPreviewModel(null, {
      spell: {
        ...baseFallbackSpell,
        upcast: {
          mode: "additional_effect_instances",
          dice: "1d4+1",
          perLevel: 1,
          baseEffectInstances: 3,
        },
      },
      selectedSlotLevel: 3,
      spellMode: "direct_damage",
      spellEffectDice: "3d4+3",
    });

    expect(model.source).toBe("fallback");
    expect(model.effectInstanceCount).toBe(5);
    expect(model.effectInstanceDice).toBe("1d4+1");
    expect(model.damagePreview).toBe("3d4+3");
    expect(model.rangeMeters).toBe(36);
    expect(model.resolutionType).toBe("direct_damage");
  });

  it("exposes area_shape and area_size_meters from resolvedContext when present", () => {
    const model = buildSpellPreviewModel(
      {
        ...resolvedContextDefaults,
        spell_name: "Fireball",
        spell_level: 3,
        slot_level: 3,
        resolution_type: "saving_throw",
        requires_saving_throw: true,
        save_ability: "dexterity",
        area_shape: "sphere",
        area_size_meters: 6,
        range_meters: 45,
        damage_preview: "8d6",
        damage_type: "fire",
      },
      {
        spell: {
          ...baseFallbackSpell,
          level: 3,
          damageType: "Fire",
          areaShape: "sphere",
          rangeMeters: 45,
          savingThrow: "DEX",
          selectionType: "point",
        },
        selectedSlotLevel: 3,
        spellMode: "saving_throw",
        spellEffectDice: "8d6",
      },
    );

    expect(model.areaShape).toBe("sphere");
    expect(model.areaSizeMeters).toBe(6);
    expect(model.rangeMeters).toBe(45);
    expect(model.saveAbility).toBe("dexterity");
  });
});
