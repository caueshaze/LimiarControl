import type {
  CastingTimeType,
  ResolutionType,
  SaveSuccessOutcome,
  SpellSchool,
  SpellSource,
  TargetMode,
  UpcastMode,
} from "../../../entities/base-spell";
import { localizeDamageAdminFallback } from "./damage";
import {
  displayLabel,
  label,
  normalizeLookup,
  type LabelEntry,
  type LocaleLike,
} from "./shared";

const SPELL_SCHOOL_LABELS: Record<SpellSchool, LabelEntry> = {
  abjuration: label("Abjuration", "Abjuração"),
  conjuration: label("Conjuration", "Conjuração"),
  divination: label("Divination", "Adivinhação"),
  enchantment: label("Enchantment", "Encantamento"),
  evocation: label("Evocation", "Evocação"),
  illusion: label("Illusion", "Ilusão"),
  necromancy: label("Necromancy", "Necromancia"),
  transmutation: label("Transmutation", "Transmutação"),
};

const CASTING_TIME_TYPE_LABELS: Record<CastingTimeType, LabelEntry> = {
  action: label("Action", "Ação"),
  bonus_action: label("Bonus action", "Ação bônus"),
  reaction: label("Reaction", "Reação"),
  "1_minute": label("1 minute", "1 minuto"),
  "10_minutes": label("10 minutes", "10 minutos"),
  "1_hour": label("1 hour", "1 hora"),
  "8_hours": label("8 hours", "8 horas"),
  "12_hours": label("12 hours", "12 horas"),
  "24_hours": label("24 hours", "24 horas"),
  special: label("Special", "Especial"),
};

const TARGET_MODE_LABELS: Record<TargetMode, LabelEntry> = {
  self: label("Self", "Pessoal"),
  touch: label("Touch", "Toque"),
  ranged: label("Ranged", "À distância"),
  cone: label("Cone", "Cone"),
  cube: label("Cube", "Cubo"),
  sphere: label("Sphere", "Esfera"),
  line: label("Line", "Linha"),
  cylinder: label("Cylinder", "Cilindro"),
  special: label("Special", "Especial"),
};

const RESOLUTION_TYPE_LABELS: Record<ResolutionType, LabelEntry> = {
  damage: label("Damage", "Dano"),
  heal: label("Healing", "Cura"),
  buff: label("Buff", "Benefício"),
  debuff: label("Debuff", "Penalidade"),
  control: label("Control", "Controle"),
  utility: label("Utility", "Utilidade"),
};

const SAVE_SUCCESS_OUTCOME_LABELS: Record<SaveSuccessOutcome, LabelEntry> = {
  none: label("None", "Nenhum"),
  half_damage: label("Half damage", "Metade do dano"),
};

const SPELL_ADMIN_VALUE_LABELS: Record<string, LabelEntry> = {
  saving_throw: label("Saving throw", "Teste de resistência"),
};

const UPCAST_MODE_LABELS: Record<UpcastMode, LabelEntry> = {
  extra_damage_dice: label("Extra damage dice", "Dados de dano extras"),
  extra_heal_dice: label("Extra heal dice", "Dados de cura extras"),
  flat_bonus: label("Flat bonus", "Bônus fixo"),
  additional_targets: label("Additional targets", "Alvos adicionais"),
  duration_scaling: label("Duration scaling", "Escalada de duração"),
  effect_scaling: label("Effect scaling", "Escalada de efeito"),
  extra_effect: label("Extra effect", "Efeito extra"),
};

const SPELL_SOURCE_LABELS: Record<SpellSource, LabelEntry> = {
  admin_panel: label("Admin panel", "Painel admin"),
  seed_json_bootstrap: label("Seed bootstrap", "Carga inicial por seed"),
};

const SPELL_CLASS_LABELS: Record<string, LabelEntry> = {
  Bard: label("Bard", "Bardo"),
  Cleric: label("Cleric", "Clérigo"),
  Druid: label("Druid", "Druida"),
  Paladin: label("Paladin", "Paladino"),
  Ranger: label("Ranger", "Patrulheiro"),
  Sorcerer: label("Sorcerer", "Feiticeiro"),
  Warlock: label("Warlock", "Bruxo"),
  Wizard: label("Wizard", "Mago"),
};

export const localizeSpellSchool = (value: SpellSchool, locale: LocaleLike) =>
  displayLabel(SPELL_SCHOOL_LABELS[value], locale);

export const localizeCastingTimeType = (value: CastingTimeType, locale: LocaleLike) =>
  displayLabel(CASTING_TIME_TYPE_LABELS[value], locale);

export const localizeTargetMode = (value: TargetMode, locale: LocaleLike) =>
  displayLabel(TARGET_MODE_LABELS[value], locale);

export const localizeResolutionType = (value: ResolutionType, locale: LocaleLike) =>
  displayLabel(RESOLUTION_TYPE_LABELS[value], locale);

export const localizeSaveSuccessOutcome = (
  value: SaveSuccessOutcome,
  locale: LocaleLike,
) => displayLabel(SAVE_SUCCESS_OUTCOME_LABELS[value], locale);

export const localizeUpcastMode = (value: UpcastMode, locale: LocaleLike) =>
  displayLabel(UPCAST_MODE_LABELS[value], locale);

export const localizeSpellSource = (value: SpellSource, locale: LocaleLike) =>
  displayLabel(SPELL_SOURCE_LABELS[value], locale);

export const localizeSpellClass = (value: string, locale: LocaleLike) =>
  SPELL_CLASS_LABELS[value] ? displayLabel(SPELL_CLASS_LABELS[value], locale) : value;

export const localizeSpellAdminValue = (value: string, locale: LocaleLike) => {
  const normalized = normalizeLookup(value).replace(/\s+/g, "_");
  const maps: Record<string, LabelEntry>[] = [
    SPELL_ADMIN_VALUE_LABELS,
    SPELL_SCHOOL_LABELS as Record<string, LabelEntry>,
    CASTING_TIME_TYPE_LABELS as Record<string, LabelEntry>,
    TARGET_MODE_LABELS as Record<string, LabelEntry>,
    RESOLUTION_TYPE_LABELS as Record<string, LabelEntry>,
    UPCAST_MODE_LABELS as Record<string, LabelEntry>,
    SAVE_SUCCESS_OUTCOME_LABELS as Record<string, LabelEntry>,
    SPELL_SOURCE_LABELS as Record<string, LabelEntry>,
  ];

  for (const map of maps) {
    if (map[normalized]) {
      return displayLabel(map[normalized], locale);
    }
  }

  if (SPELL_CLASS_LABELS[value]) {
    return displayLabel(SPELL_CLASS_LABELS[value], locale);
  }

  return localizeDamageAdminFallback(value, locale);
};
