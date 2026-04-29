import type {
  AreaShape,
  CastingTimeType,
  ResolutionType,
  SaveSuccessOutcome,
  SpellAttackType,
  SpellEffectTiming,
  SpellOriginType,
  SpellRangeKind,
  SpellSchool,
  SpellSelectionType,
  SpellSource,
  SpellTargetAnchor,
  TargetType,
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

const TARGET_TYPE_LABELS: Record<TargetType, LabelEntry> = {
  self: label("Self", "Pessoal"),
  touch: label("Touch", "Toque"),
  ranged: label("Ranged", "À distância"),
  special: label("Special", "Especial"),
};

const SPELL_SELECTION_TYPE_LABELS: Record<SpellSelectionType, LabelEntry> = {
  none: label("None", "Nenhuma"),
  self: label("Self", "Pessoal"),
  creature: label("Creature", "Criatura"),
  object: label("Object", "Objeto"),
  creature_or_object: label("Creature or object", "Criatura ou objeto"),
  point: label("Point", "Ponto"),
  direction: label("Direction", "Direção"),
};

const SPELL_ORIGIN_TYPE_LABELS: Record<SpellOriginType, LabelEntry> = {
  caster: label("Caster", "Conjurador"),
  selected_target: label("Selected target", "Alvo selecionado"),
  selected_point: label("Selected point", "Ponto selecionado"),
};

const SPELL_TARGET_ANCHOR_LABELS: Record<SpellTargetAnchor, LabelEntry> = {
  caster: label("Caster", "Conjurador"),
  selected_target: label("Selected target", "Alvo selecionado"),
  selected_point: label("Selected point", "Ponto selecionado"),
  trigger_target: label("Trigger target", "Alvo do gatilho"),
};

const SPELL_ATTACK_TYPE_LABELS: Record<SpellAttackType, LabelEntry> = {
  none: label("None", "Nenhum"),
  melee_spell: label("Melee spell", "Magia corpo a corpo"),
  ranged_spell: label("Ranged spell", "Magia à distância"),
};

const SPELL_RANGE_KIND_LABELS: Record<SpellRangeKind, LabelEntry> = {
  self: label("Self", "Pessoal"),
  touch: label("Touch", "Toque"),
  distance: label("Distance", "Distância"),
};

const SPELL_EFFECT_TIMING_LABELS: Record<SpellEffectTiming, LabelEntry> = {
  immediate: label("Immediate", "Imediato"),
  persistent: label("Persistent", "Persistente"),
  triggered: label("Triggered", "Acionado"),
};

const AREA_SHAPE_LABELS: Record<AreaShape, LabelEntry> = {
  cone: label("Cone", "Cone"),
  cube: label("Cube", "Cubo"),
  sphere: label("Sphere", "Esfera"),
  line: label("Line", "Linha"),
  cylinder: label("Cylinder", "Cilindro"),
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
  physical: label("Physical", "Física"),
};

const UPCAST_MODE_LABELS: Record<UpcastMode, LabelEntry> = {
  extra_damage_dice: label("Extra damage dice", "Dados de dano extras"),
  extra_heal_dice: label("Extra heal dice", "Dados de cura extras"),
  flat_bonus: label("Flat bonus", "Bônus fixo"),
  additional_effect_instances: label("Additional effect instances", "Instâncias extras de efeito"),
  additional_targets: label("Additional targets", "Alvos adicionais"),
  duration_scaling: label("Duration scaling", "Escalada de duração"),
  effect_scaling: label("Effect scaling", "Escalada de efeito"),
  extra_effect: label("Extra effect", "Efeito extra"),
};

const UPCAST_MODE_DESCRIPTIONS: Record<UpcastMode, LabelEntry> = {
  extra_damage_dice: label(
    "Adds damage dice per slot level above base",
    "Adiciona dados de dano por nível de espaço acima do base",
  ),
  extra_heal_dice: label(
    "Adds healing dice per slot level above base",
    "Adiciona dados de cura por nível de espaço acima do base",
  ),
  flat_bonus: label(
    "Adds a flat numeric bonus per slot level",
    "Adiciona um bônus numérico fixo por nível de espaço",
  ),
  additional_effect_instances: label(
    "Adds more effect instances, like Magic Missile darts",
    "Adiciona instâncias extras de efeito, como dardos de Magic Missile",
  ),
  additional_targets: label(
    "Adds more targets per higher slot level",
    "Adiciona alvos extras por nível de espaço acima do base",
  ),
  duration_scaling: label(
    "Increases spell duration when upcast",
    "Aumenta a duração da magia quando conjurada em nível superior",
  ),
  effect_scaling: label(
    "Increases an effect value, such as radius",
    "Aumenta um valor de efeito, como o raio de área",
  ),
  extra_effect: label(
    "Unlocks an additional effect at higher levels",
    "Desbloqueia um efeito adicional em níveis superiores",
  ),
};

const UPCAST_MODE_EXAMPLES: Record<UpcastMode, LabelEntry> = {
  extra_damage_dice: label(
    "Ex.: Fireball uses +1d6 per slot level above 3rd.",
    "Ex.: Fireball usa +1d6 por nível de espaço acima do 3º.",
  ),
  extra_heal_dice: label(
    "Ex.: Cure Wounds uses +1d8 per slot level above 1st.",
    "Ex.: Cure Wounds usa +1d8 por nível de espaço acima do 1º.",
  ),
  flat_bonus: label("", ""),
  additional_effect_instances: label(
    "Ex.: Magic Missile adds 1 extra dart per slot level above 1st.",
    "Ex.: Magic Missile adiciona 1 dardo extra por nível de espaço acima do 1º.",
  ),
  additional_targets: label(
    "Ex.: Hold Person adds 1 extra target per slot level above 2nd.",
    "Ex.: Hold Person adiciona 1 alvo extra por nível de espaço acima do 2º.",
  ),
  duration_scaling: label("", ""),
  effect_scaling: label(
    "Ex.: Fog Cloud increases radius by 6 m per slot level above 1st.",
    "Ex.: Fog Cloud aumenta o raio em 6 m por nível de espaço acima do 1º.",
  ),
  extra_effect: label("", ""),
};

const SPELL_SOURCE_LABELS: Record<SpellSource, LabelEntry> = {
  admin_panel: label("Admin panel", "Painel admin"),
  seed_json_bootstrap: label("Seed bootstrap", "Carga inicial por seed"),
};

const SPELL_CLASS_LABELS: Record<string, LabelEntry> = {
  Bard: label("Bard", "Bardo"),
  Cleric: label("Cleric", "Clérigo"),
  Druid: label("Druid", "Druida"),
  Guardian: label("Guardian", "Guardião"),
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

export const localizeTargetType = (value: TargetType, locale: LocaleLike) =>
  displayLabel(TARGET_TYPE_LABELS[value], locale);

export const localizeAreaShape = (value: AreaShape, locale: LocaleLike) =>
  displayLabel(AREA_SHAPE_LABELS[value], locale);

export const localizeResolutionType = (value: ResolutionType, locale: LocaleLike) =>
  displayLabel(RESOLUTION_TYPE_LABELS[value], locale);

export const localizeSaveSuccessOutcome = (
  value: SaveSuccessOutcome,
  locale: LocaleLike,
) => displayLabel(SAVE_SUCCESS_OUTCOME_LABELS[value], locale);

export const localizeUpcastMode = (value: UpcastMode, locale: LocaleLike) =>
  displayLabel(UPCAST_MODE_LABELS[value], locale);

export const localizeUpcastModeDescription = (value: UpcastMode, locale: LocaleLike) =>
  displayLabel(UPCAST_MODE_DESCRIPTIONS[value], locale);

export const localizeUpcastModeExample = (value: UpcastMode, locale: LocaleLike) =>
  displayLabel(UPCAST_MODE_EXAMPLES[value], locale);

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
    TARGET_TYPE_LABELS as Record<string, LabelEntry>,
    SPELL_SELECTION_TYPE_LABELS as Record<string, LabelEntry>,
    SPELL_ORIGIN_TYPE_LABELS as Record<string, LabelEntry>,
    SPELL_TARGET_ANCHOR_LABELS as Record<string, LabelEntry>,
    SPELL_ATTACK_TYPE_LABELS as Record<string, LabelEntry>,
    SPELL_RANGE_KIND_LABELS as Record<string, LabelEntry>,
    SPELL_EFFECT_TIMING_LABELS as Record<string, LabelEntry>,
    AREA_SHAPE_LABELS as Record<string, LabelEntry>,
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
