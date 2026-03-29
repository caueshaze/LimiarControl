import type {
  ActiveEffectConditionType,
  ActiveEffectDurationType,
  ActiveEffectKind,
  StandardActionType,
} from "../../shared/api/combatRepo";

export const EFFECT_KINDS: { value: ActiveEffectKind; label: string }[] = [
  { value: "condition", label: "Condition" },
  { value: "temp_ac_bonus", label: "Temp AC Bonus" },
  { value: "attack_bonus", label: "Attack Bonus" },
  { value: "damage_bonus", label: "Damage Bonus" },
  { value: "advantage_on_attacks", label: "Advantage on Attacks" },
  { value: "disadvantage_on_attacks", label: "Disadvantage on Attacks" },
];

export const CONDITION_TYPES: { value: ActiveEffectConditionType; label: string }[] = [
  { value: "prone", label: "Prone" },
  { value: "poisoned", label: "Poisoned" },
  { value: "restrained", label: "Restrained" },
  { value: "blinded", label: "Blinded" },
  { value: "frightened", label: "Frightened" },
];

export const DURATION_TYPES: { value: ActiveEffectDurationType; label: string }[] = [
  { value: "manual", label: "Manual (remove manually)" },
  { value: "rounds", label: "Rounds" },
  { value: "until_turn_start", label: "Until Turn Start" },
  { value: "until_turn_end", label: "Until Turn End" },
];

export const NUMERIC_KINDS = new Set<ActiveEffectKind>(["temp_ac_bonus", "attack_bonus", "damage_bonus"]);

export const STANDARD_ACTIONS: { value: StandardActionType; label: string }[] = [
  { value: "dodge", label: "Dodge" },
  { value: "help", label: "Help" },
  { value: "hide", label: "Hide" },
  { value: "use_object", label: "Use Object" },
  { value: "dash", label: "Dash" },
  { value: "disengage", label: "Disengage" },
];
