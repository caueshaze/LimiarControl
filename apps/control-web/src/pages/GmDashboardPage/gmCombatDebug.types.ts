import type {
  ActiveEffectConditionType,
  ActiveEffectDurationType,
  ActiveEffectKind,
  StandardActionType,
} from "../../shared/api/combatRepo";
import type { LocaleKey } from "../../shared/i18n";

export const EFFECT_KINDS: { value: ActiveEffectKind; label: LocaleKey }[] = [
  { value: "condition", label: "combatUi.effect.condition" },
  { value: "temp_ac_bonus", label: "combatUi.effect.temp_ac_bonus" },
  { value: "attack_bonus", label: "combatUi.effect.attack_bonus" },
  { value: "damage_bonus", label: "combatUi.effect.damage_bonus" },
  { value: "advantage_on_attacks", label: "combatUi.effect.advantage_on_attacks" },
  { value: "disadvantage_on_attacks", label: "combatUi.effect.disadvantage_on_attacks" },
];

export const CONDITION_TYPES: { value: ActiveEffectConditionType; label: LocaleKey }[] = [
  { value: "prone", label: "combatUi.condition.prone" },
  { value: "poisoned", label: "combatUi.condition.poisoned" },
  { value: "restrained", label: "combatUi.condition.restrained" },
  { value: "blinded", label: "combatUi.condition.blinded" },
  { value: "frightened", label: "combatUi.condition.frightened" },
];

export const DURATION_TYPES: { value: ActiveEffectDurationType; label: LocaleKey }[] = [
  { value: "manual", label: "combatUi.duration.manual" },
  { value: "rounds", label: "combatUi.duration.rounds" },
  { value: "until_turn_start", label: "combatUi.duration.until_turn_start" },
  { value: "until_turn_end", label: "combatUi.duration.until_turn_end" },
];

export const NUMERIC_KINDS = new Set<ActiveEffectKind>(["temp_ac_bonus", "attack_bonus", "damage_bonus"]);

export const STANDARD_ACTIONS: { value: StandardActionType; label: LocaleKey }[] = [
  { value: "dodge", label: "combatUi.dodge" },
  { value: "help", label: "combatUi.help" },
  { value: "hide", label: "combatUi.hide" },
  { value: "use_object", label: "combatUi.useObject" },
  { value: "dash", label: "combatUi.dash" },
  { value: "disengage", label: "combatUi.disengage" },
];
