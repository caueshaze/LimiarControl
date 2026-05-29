import type { CampaignSystemType } from "../campaign";

export const SpellSchool = {
  ABJURATION: "abjuration",
  CONJURATION: "conjuration",
  DIVINATION: "divination",
  ENCHANTMENT: "enchantment",
  EVOCATION: "evocation",
  ILLUSION: "illusion",
  NECROMANCY: "necromancy",
  TRANSMUTATION: "transmutation"
} as const;

export type SpellSchool = (typeof SpellSchool)[keyof typeof SpellSchool];

export const CastingTimeType = {
  ACTION: "action",
  BONUS_ACTION: "bonus_action",
  REACTION: "reaction",
  MINUTE_1: "1_minute",
  MINUTES_10: "10_minutes",
  HOUR_1: "1_hour",
  HOURS_8: "8_hours",
  HOURS_12: "12_hours",
  HOURS_24: "24_hours",
  SPECIAL: "special"
} as const;

export type CastingTimeType =
  (typeof CastingTimeType)[keyof typeof CastingTimeType];

export const TargetType = {
  SELF: "self",
  TOUCH: "touch",
  RANGED: "ranged",
  SPECIAL: "special"
} as const;

export type TargetType = (typeof TargetType)[keyof typeof TargetType];

export const SpellSelectionType = {
  NONE: "none",
  SELF: "self",
  CREATURE: "creature",
  OBJECT: "object",
  CREATURE_OR_OBJECT: "creature_or_object",
  POINT: "point",
  DIRECTION: "direction"
} as const;

export type SpellSelectionType =
  (typeof SpellSelectionType)[keyof typeof SpellSelectionType];

export const SpellOriginType = {
  CASTER: "caster",
  SELECTED_TARGET: "selected_target",
  SELECTED_POINT: "selected_point"
} as const;

export type SpellOriginType =
  (typeof SpellOriginType)[keyof typeof SpellOriginType];

export const SpellTargetAnchor = {
  CASTER: "caster",
  SELECTED_TARGET: "selected_target",
  SELECTED_POINT: "selected_point",
  TRIGGER_TARGET: "trigger_target"
} as const;

export type SpellTargetAnchor =
  (typeof SpellTargetAnchor)[keyof typeof SpellTargetAnchor];

export const SpellAttackType = {
  NONE: "none",
  MELEE_SPELL: "melee_spell",
  RANGED_SPELL: "ranged_spell"
} as const;

export type SpellAttackType =
  (typeof SpellAttackType)[keyof typeof SpellAttackType];

export const SpellRangeKind = {
  SELF: "self",
  TOUCH: "touch",
  DISTANCE: "distance"
} as const;

export type SpellRangeKind =
  (typeof SpellRangeKind)[keyof typeof SpellRangeKind];

export const SpellEffectTiming = {
  IMMEDIATE: "immediate",
  PERSISTENT: "persistent",
  TRIGGERED: "triggered"
} as const;

export type SpellEffectTiming =
  (typeof SpellEffectTiming)[keyof typeof SpellEffectTiming];

export const AreaShape = {
  CONE: "cone",
  CUBE: "cube",
  SPHERE: "sphere",
  LINE: "line",
  CYLINDER: "cylinder"
} as const;

export type AreaShape = (typeof AreaShape)[keyof typeof AreaShape];

export const ResolutionType = {
  DAMAGE: "damage",
  HEAL: "heal",
  BUFF: "buff",
  DEBUFF: "debuff",
  CONTROL: "control",
  UTILITY: "utility"
} as const;

export type ResolutionType =
  (typeof ResolutionType)[keyof typeof ResolutionType];

export const UpcastMode = {
  EXTRA_DAMAGE_DICE: "extra_damage_dice",
  EXTRA_HEAL_DICE: "extra_heal_dice",
  FLAT_BONUS: "flat_bonus",
  ADDITIONAL_EFFECT_INSTANCES: "additional_effect_instances",
  ADDITIONAL_TARGETS: "additional_targets",
  DURATION_SCALING: "duration_scaling",
  EFFECT_SCALING: "effect_scaling",
  EXTRA_EFFECT: "extra_effect"
} as const;

export type UpcastMode = (typeof UpcastMode)[keyof typeof UpcastMode];

export type SpellUpcast = {
  mode: UpcastMode;
  dice?: string | null;
  flat?: number | null;
  perLevel?: number | null;
  baseEffectInstances?: number | null;
  maxLevel?: number | null;
  scalingKey?: string | null;
  scalingSummary?: string | null;
  scalingEditorial?: string | null;
  unlockKey?: string | null;
  unlockSummary?: string | null;
  unlockEditorial?: string | null;
};

export const CantripScalingEffectType = {
  DAMAGE_DICE: "damage_dice",
  EFFECT_INSTANCES: "effect_instances",
} as const;

export type CantripScalingEffectType =
  (typeof CantripScalingEffectType)[keyof typeof CantripScalingEffectType];

export type CantripScalingThresholdDamage = {
  characterLevel: number;
  damage: { dice: string };
};

export type CantripScalingThresholdInstances = {
  characterLevel: number;
  instances: number;
  instanceDamage: { dice: string };
};

export type CantripScalingThreshold =
  | CantripScalingThresholdDamage
  | CantripScalingThresholdInstances;

export type SpellCantripScaling = {
  /** "mode" is the legacy field; new records use "scalingMode". */
  mode?: "character_level";
  scalingMode?: "character_level";
  scalingEffectType: CantripScalingEffectType;
  thresholds: CantripScalingThreshold[];
};

export const SpellSource = {
  ADMIN_PANEL: "admin_panel",
  SEED_JSON_BOOTSTRAP: "seed_json_bootstrap"
} as const;

export type SpellSource = (typeof SpellSource)[keyof typeof SpellSource];

export const SpellSavingThrow = {
  STR: "STR",
  DEX: "DEX",
  CON: "CON",
  INT: "INT",
  WIS: "WIS",
  CHA: "CHA"
} as const;

export type SpellSavingThrow =
  (typeof SpellSavingThrow)[keyof typeof SpellSavingThrow];

export const SpellDamageType = {
  ACID: "Acid",
  BLUDGEONING: "Bludgeoning",
  COLD: "Cold",
  FIRE: "Fire",
  FORCE: "Force",
  LIGHTNING: "Lightning",
  NECROTIC: "Necrotic",
  PIERCING: "Piercing",
  POISON: "Poison",
  PSYCHIC: "Psychic",
  RADIANT: "Radiant",
  SLASHING: "Slashing",
  THUNDER: "Thunder"
} as const;

export type SpellDamageType =
  (typeof SpellDamageType)[keyof typeof SpellDamageType];

export const SaveSuccessOutcome = {
  NONE: "none",
  HALF_DAMAGE: "half_damage"
} as const;

export type SaveSuccessOutcome =
  (typeof SaveSuccessOutcome)[keyof typeof SaveSuccessOutcome];

export const SpellDeclarativeEffectType = {
  APPLY_CONDITION: "apply_condition",
  MODIFY_STAT: "modify_stat",
  MODIFY_WEAPON_DAMAGE: "modify_weapon_damage",
  ARMOR_CLASS_FORMULA: "armor_class_formula",
  ADVANTAGE_ON_CHECKS: "advantage_on_checks",
  DISADVANTAGE_ON_CHECKS: "disadvantage_on_checks",
  ADVANTAGE_ON_SAVES: "advantage_on_saves",
  DISADVANTAGE_ON_SAVES: "disadvantage_on_saves",
  SIZE_MODIFIER: "size_modifier",
  RESTRICT_ACTION: "restrict_action",
} as const;

export type SpellDeclarativeEffectType =
  (typeof SpellDeclarativeEffectType)[keyof typeof SpellDeclarativeEffectType];

export const SpellDeclarativeEffectTarget = {
  SELECTED_TARGET: "selected_target",
  CASTER: "caster",
} as const;

export type SpellDeclarativeEffectTarget =
  (typeof SpellDeclarativeEffectTarget)[keyof typeof SpellDeclarativeEffectTarget];

export const SpellDeclarativeDurationType = {
  MANUAL: "manual",
  ROUNDS: "rounds",
  UNTIL_TURN_START: "until_turn_start",
  UNTIL_TURN_END: "until_turn_end",
  TIMED: "timed",
} as const;

export type SpellDeclarativeDurationType =
  (typeof SpellDeclarativeDurationType)[keyof typeof SpellDeclarativeDurationType];

export const SpellDeclarativeDurationAnchor = {
  TARGET: "target",
  CASTER: "caster",
} as const;

export type SpellDeclarativeDurationAnchor =
  (typeof SpellDeclarativeDurationAnchor)[keyof typeof SpellDeclarativeDurationAnchor];

export type SpellDeclarativeDuration = {
  type: SpellDeclarativeDurationType;
  rounds?: number | null;
  seconds?: number | null;
  anchor?: SpellDeclarativeDurationAnchor | null;
};

export type SpellOutOfCombatTimedDuration = {
  type: "timed";
  seconds: number;
};

export const SpellDeclarativeConditionType = {
  BLINDED: "blinded",
  CHARMED: "charmed",
  DEAFENED: "deafened",
  FRIGHTENED: "frightened",
  GRAPPLED: "grappled",
  HOSTILE_TO_CASTER: "hostile_to_caster",
  INCAPACITATED: "incapacitated",
  INVISIBLE: "invisible",
  PARALYZED: "paralyzed",
  PETRIFIED: "petrified",
  POISONED: "poisoned",
  PRONE: "prone",
  RESTRAINED: "restrained",
  STUNNED: "stunned",
  UNCONSCIOUS: "unconscious",
} as const;

export type SpellDeclarativeConditionType =
  (typeof SpellDeclarativeConditionType)[keyof typeof SpellDeclarativeConditionType];

export const SpellDeclarativeModifyStat = {
  TEMP_AC_BONUS: "temp_ac_bonus",
  ATTACK_BONUS: "attack_bonus",
  DAMAGE_BONUS: "damage_bonus",
} as const;

export type SpellDeclarativeModifyStat =
  (typeof SpellDeclarativeModifyStat)[keyof typeof SpellDeclarativeModifyStat];

export const SpellDeclarativeRestrictActionKind = {
  ACTIONS: "actions",
  BONUS_ACTIONS: "bonus_actions",
  REACTIONS: "reactions",
  MOVEMENT: "movement",
} as const;

export type SpellDeclarativeRestrictActionKind =
  (typeof SpellDeclarativeRestrictActionKind)[keyof typeof SpellDeclarativeRestrictActionKind];

export type SpellDeclarativeEffect =
  | {
      type: "apply_condition";
      target: SpellDeclarativeEffectTarget;
      duration?: SpellDeclarativeDuration | null;
      out_of_combat_duration?: SpellOutOfCombatTimedDuration | null;
      params: { condition: SpellDeclarativeConditionType };
      stacking?: "stack" | "replace" | null;
    }
  | {
      type: "modify_stat";
      target: SpellDeclarativeEffectTarget;
      duration?: SpellDeclarativeDuration | null;
      out_of_combat_duration?: SpellOutOfCombatTimedDuration | null;
      params: { stat: SpellDeclarativeModifyStat; value: number };
      stacking?: "stack" | "replace" | null;
    }
  | {
      type: "modify_weapon_damage";
      target: SpellDeclarativeEffectTarget;
      duration?: SpellDeclarativeDuration | null;
      out_of_combat_duration?: SpellOutOfCombatTimedDuration | null;
      params: { dice: string; operation?: "add" | "subtract"; minimum_total_damage?: number | null };
      stacking?: "stack" | "replace" | null;
    }
  | {
      type: "armor_class_formula";
      target: SpellDeclarativeEffectTarget;
      duration?: SpellDeclarativeDuration | null;
      out_of_combat_duration?: SpellOutOfCombatTimedDuration | null;
      params: {
        base_value: number;
        ability: "strength" | "dexterity" | "constitution" | "intelligence" | "wisdom" | "charisma";
        requires_unarmored?: boolean | null;
      };
      stacking?: "stack" | "replace" | null;
    }
  | {
      type: "advantage_on_checks" | "disadvantage_on_checks";
      target: SpellDeclarativeEffectTarget;
      duration?: SpellDeclarativeDuration | null;
      out_of_combat_duration?: SpellOutOfCombatTimedDuration | null;
      params: { ability: "strength" | "dexterity" | "constitution" | "intelligence" | "wisdom" | "charisma"; against?: "any" | "effect_target" | "selected_target" };
      stacking?: "stack" | "replace" | null;
    }
  | {
      type: "advantage_on_saves" | "disadvantage_on_saves";
      target: SpellDeclarativeEffectTarget;
      duration?: SpellDeclarativeDuration | null;
      out_of_combat_duration?: SpellOutOfCombatTimedDuration | null;
      params: { abilities: Array<"strength" | "dexterity" | "constitution" | "intelligence" | "wisdom" | "charisma"> };
      stacking?: "stack" | "replace" | null;
    }
  | {
      type: "size_modifier";
      target: SpellDeclarativeEffectTarget;
      duration?: SpellDeclarativeDuration | null;
      out_of_combat_duration?: SpellOutOfCombatTimedDuration | null;
      params: { value: -1 | 1 };
      stacking?: "stack" | "replace" | null;
    }
  | {
      type: "restrict_action";
      target: SpellDeclarativeEffectTarget;
      duration?: SpellDeclarativeDuration | null;
      out_of_combat_duration?: SpellOutOfCombatTimedDuration | null;
      params: { action: SpellDeclarativeRestrictActionKind };
      stacking?: "stack" | "replace" | null;
    };

export const SpellPersistentAreaKind = {
  OBSCUREMENT: "obscurement",
  HAZARD: "hazard",
  NO_SEMANTIC_EFFECT: "no_semantic_effect",
} as const;

export type SpellPersistentAreaKind =
  (typeof SpellPersistentAreaKind)[keyof typeof SpellPersistentAreaKind];

export const SpellPersistentAreaObscurement = {
  HEAVILY_OBSCURED: "heavily_obscured",
} as const;

export type SpellPersistentAreaObscurement =
  (typeof SpellPersistentAreaObscurement)[keyof typeof SpellPersistentAreaObscurement];

export const SpellPersistentAreaTerrainEffect = {
  DIFFICULT_TERRAIN: "difficult_terrain",
} as const;

export type SpellPersistentAreaTerrainEffect =
  (typeof SpellPersistentAreaTerrainEffect)[keyof typeof SpellPersistentAreaTerrainEffect];

export type SpellPersistentAreaEffect =
  | {
      kind: "obscurement";
      params: { obscurement: SpellPersistentAreaObscurement };
    }
  | {
      kind: "hazard";
      params: {
        terrainEffect?: SpellPersistentAreaTerrainEffect | null;
        movementDamageDice?: string | null;
        damageType?: SpellDamageType | null;
        damagePerMeters?: number | null;
      };
    }
  | {
      kind: "no_semantic_effect";
      params?: Record<string, never> | null;
    };

export type SpellVariantManualNote = {
  key: string;
  label: string;
  description: string;
};

export type SpellVariant = {
  key: string;
  labelEn?: string | null;
  labelPt: string;
  descriptionEn?: string | null;
  descriptionPt?: string | null;
  effects?: SpellDeclarativeEffect[] | null;
  onEndEffects?: SpellDeclarativeEffect[] | null;
  manualNotes?: SpellVariantManualNote[] | null;
};

export type BaseSpellAlias = {
  id: string;
  alias: string;
  locale?: string | null;
  aliasType?: string | null;
};

export type SpellConsumableMaterialOption = {
  key: string;
  nameEn?: string | null;
  namePt?: string | null;
  quantity?: number | null;
};

export type BaseSpell = {
  id: string;
  system: CampaignSystemType;
  canonicalKey: string;
  nameEn: string;
  namePt?: string | null;
  descriptionEn: string;
  descriptionPt?: string | null;
  level: number;
  school: SpellSchool;
  classesJson?: string[] | null;

  // Casting
  castingTimeType?: CastingTimeType | null;
  castingTime?: string | null;
  rangeMeters?: number | null;
  rangeText?: string | null;
  targetType?: TargetType | null;
  maxTargets?: number | null;
  selectionType?: SpellSelectionType | null;
  originType?: SpellOriginType | null;
  targetAnchor?: SpellTargetAnchor | null;
  attackType?: SpellAttackType | null;
  rangeKind?: SpellRangeKind | null;
  effectTiming?: SpellEffectTiming | null;
  areaShape?: AreaShape | null;
  /** AoE radius in meters — sphere, cylinder. */
  radiusMeters?: number | null;
  /** AoE length in meters — cone, line. */
  lengthMeters?: number | null;
  /** AoE side length in meters — cube. */
  sideMeters?: number | null;
  duration?: string | null;
  componentsJson?: string[] | null;
  materialComponentText?: string | null;
  materialComponentConsumed?: boolean;
  consumableMaterialOptions?: SpellConsumableMaterialOption[] | null;
  concentration: boolean;
  ritual: boolean;

  // Resolution
  resolutionType?: ResolutionType | null;
  savingThrow?: SpellSavingThrow | null;
  saveSuccessOutcome?: SaveSuccessOutcome | null;
  attackMissOutcome?: SaveSuccessOutcome | null;
  coverAppliesToSave?: "physical" | "none" | null;

  // Effect
  damageDice?: string | null;
  damageType?: SpellDamageType | null;
  healDice?: string | null;
  effects?: SpellDeclarativeEffect[] | null;
  onEndEffects?: SpellDeclarativeEffect[] | null;
  variants?: SpellVariant[] | null;
  persistentArea?: SpellPersistentAreaEffect | null;

  // Targeting requirements
  requiresTargetSight?: boolean | null;
  requiresTargetEffect?: boolean | null;
  requiresPointSight?: boolean | null;
  requiresPointEffect?: boolean | null;

  // Upcast
  upcast?: SpellUpcast | null;
  cantripScaling?: SpellCantripScaling | null;

  // Automation metadata (computed by backend — not stored in DB)
  automationMode?: string | null;
  defaultSpellMode?: string | null;
  requiresEffectInputs?: boolean | null;
  requiresMap?: boolean | null;
  handlerKey?: string | null;

  // Metadata
  source?: SpellSource | null;
  sourceRef?: string | null;
  isSrd: boolean;
  isActive: boolean;
  aliases: BaseSpellAlias[];
};

export type BaseSpellFilters = {
  system?: CampaignSystemType;
  level?: number;
  school?: SpellSchool;
  className?: string;
  canonicalKey?: string;
  search?: string;
  isActive?: boolean;
};

export type BaseSpellWritePayload = {
  system?: CampaignSystemType;
  canonicalKey?: string;
  nameEn?: string;
  namePt?: string | null;
  descriptionEn?: string;
  descriptionPt?: string | null;
  level?: number;
  school?: SpellSchool;
  classesJson?: string[] | null;
  castingTimeType?: CastingTimeType | null;
  castingTime?: string | null;
  rangeMeters?: number | null;
  rangeText?: string | null;
  targetType?: TargetType | null;
  maxTargets?: number | null;
  selectionType?: SpellSelectionType | null;
  originType?: SpellOriginType | null;
  targetAnchor?: SpellTargetAnchor | null;
  attackType?: SpellAttackType | null;
  rangeKind?: SpellRangeKind | null;
  effectTiming?: SpellEffectTiming | null;
  areaShape?: AreaShape | null;
  radiusMeters?: number | null;
  lengthMeters?: number | null;
  sideMeters?: number | null;
  duration?: string | null;
  componentsJson?: string[] | null;
  materialComponentText?: string | null;
  materialComponentConsumed?: boolean;
  consumableMaterialOptions?: SpellConsumableMaterialOption[] | null;
  concentration?: boolean;
  ritual?: boolean;
  resolutionType?: ResolutionType | null;
  savingThrow?: SpellSavingThrow | null;
  saveSuccessOutcome?: SaveSuccessOutcome | null;
  attackMissOutcome?: SaveSuccessOutcome | null;
  coverAppliesToSave?: "physical" | "none" | null;
  damageDice?: string | null;
  damageType?: SpellDamageType | null;
  healDice?: string | null;
  effects?: SpellDeclarativeEffect[] | null;
  onEndEffects?: SpellDeclarativeEffect[] | null;
  variants?: SpellVariant[] | null;
  persistentArea?: SpellPersistentAreaEffect | null;
  requiresTargetSight?: boolean | null;
  requiresTargetEffect?: boolean | null;
  requiresPointSight?: boolean | null;
  requiresPointEffect?: boolean | null;
  upcast?: SpellUpcast | null;
  cantripScaling?: SpellCantripScaling | null;
  source?: SpellSource | null;
  sourceRef?: string | null;
  isSrd?: boolean;
  isActive?: boolean;
};
