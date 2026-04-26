import type { BaseSpell, BaseSpellWritePayload, CastingTimeType } from "../../entities/base-spell";
import {
  SpellSource as SpellSourceValues,
  SpellSchool as SpellSchoolValues,
} from "../../entities/base-spell";
import type { FormState } from "./systemSpellCatalog.types";

const CASTING_TIME_LABELS: Record<CastingTimeType, string> = {
  action: "1 action",
  bonus_action: "1 bonus action",
  reaction: "1 reaction",
  "1_minute": "1 minute",
  "10_minutes": "10 minutes",
  "1_hour": "1 hour",
  "8_hours": "8 hours",
  "12_hours": "12 hours",
  "24_hours": "24 hours",
  special: "Special",
};

const deriveCastingTime = (castingTimeType: CastingTimeType | ""): string | null =>
  castingTimeType ? (CASTING_TIME_LABELS[castingTimeType] ?? null) : null;

const deriveRangeText = (targetType: string, rangeMeters: string): string | null => {
  if (targetType === "self") return "Self";
  if (targetType === "touch") return "Touch";
  const meters = Number(rangeMeters);
  if (Number.isFinite(meters) && meters >= 0) return `${meters} m`;
  return null;
};

export const normalizeOptionalText = (value: string) => {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
};

export const normalizeCanonicalKey = (value: string) =>
  value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");

export const parseOptionalInteger = (
  value: string,
  label: string,
): { value?: number; error?: string } => {
  const normalized = value.trim();
  if (!normalized) return {};
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || !Number.isInteger(parsed))
    return { error: `${label} precisa ser inteiro.` };
  return { value: parsed };
};

export const parseOptionalPositiveFloat = (
  value: string,
  label: string,
): { value?: number; error?: string } => {
  const normalized = value.trim();
  if (!normalized) return {};
  const parsed = parseFloat(normalized);
  if (!Number.isFinite(parsed))
    return { error: `${label} precisa ser um número válido.` };
  return { value: parsed };
};

const parseDiceParts = (value?: string | null) => {
  const match = value?.trim().match(/^(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?$/i);
  if (!match) {
    return { count: "", size: "", bonus: "" };
  }
  const sign = match[3] === "-" ? "-" : "";
  return {
    count: match[1] ?? "",
    size: match[2] ?? "",
    bonus: match[4] ? `${sign}${match[4]}` : "",
  };
};

const buildDiceExpression = (count: string, size: string, bonus: string) => {
  const parsedCount = parseOptionalInteger(count, "Quantidade de dados").value;
  const parsedSize = parseOptionalInteger(size, "Dado").value;
  const parsedBonus = parseOptionalInteger(bonus, "Bonus fixo").value;
  if (!parsedCount || !parsedSize || parsedCount < 1 || parsedSize < 1) {
    return null;
  }

  let expression = `${parsedCount}d${parsedSize}`;
  if (parsedBonus && parsedBonus > 0) {
    expression += `+${parsedBonus}`;
  } else if (parsedBonus && parsedBonus < 0) {
    expression += `${parsedBonus}`;
  }
  return expression;
};

export const toggleListValue = (current: string[], value: string) =>
  current.includes(value)
    ? current.filter((entry) => entry !== value)
    : [...current, value];

export const createEmptyForm = (): FormState => ({
  system: "DND5E",
  canonicalKey: "",
  nameEn: "",
  namePt: "",
  descriptionEn: "",
  descriptionPt: "",
  level: 0,
  school: SpellSchoolValues.EVOCATION,
  classesJson: [],
  castingTimeType: "action",
  rangeMeters: "",
  targetType: "",
  maxTargets: "",
  selectionType: "",
  originType: "",
  targetAnchor: "",
  attackType: "",
  rangeKind: "",
  effectTiming: "",
  areaShape: "",
  radiusMeters: "",
  lengthMeters: "",
  sideMeters: "",
  duration: "",
  componentsJson: [],
  materialComponentText: "",
  concentration: false,
  ritual: false,
  resolutionType: "",
  savingThrow: "",
  saveSuccessOutcome: "",
  damageDice: "",
  damageDiceCount: "",
  damageDieSize: "",
  damageFixedBonus: "",
  damageType: "",
  healDice: "",
  upcastMode: "",
  upcastDice: "",
  upcastDiceCount: "",
  upcastDieSize: "",
  upcastFixedBonus: "",
  upcastFlat: "",
  upcastPerLevel: "1",
  upcastMaxLevel: "",
  upcastScalingKey: "",
  upcastScalingSummary: "",
  upcastScalingEditorial: "",
  upcastUnlockKey: "",
  upcastUnlockSummary: "",
  upcastUnlockEditorial: "",
  source: SpellSourceValues.ADMIN_PANEL,
  sourceRef: "",
  isSrd: false,
  isActive: true,
});

export const formFromSpell = (spell: BaseSpell): FormState => ({
  ...(() => {
    const damageParts = parseDiceParts(spell.damageDice);
    const upcastParts = parseDiceParts(spell.upcast?.dice);
    return {
      damageDiceCount: damageParts.count,
      damageDieSize: damageParts.size,
      damageFixedBonus: damageParts.bonus,
      upcastDiceCount: upcastParts.count,
      upcastDieSize: upcastParts.size,
      upcastFixedBonus: upcastParts.bonus,
    };
  })(),
  system: spell.system,
  canonicalKey: spell.canonicalKey,
  nameEn: spell.nameEn,
  namePt: spell.namePt ?? "",
  descriptionEn: spell.descriptionEn,
  descriptionPt: spell.descriptionPt ?? "",
  level: spell.level,
  school: spell.school,
  classesJson: spell.classesJson ?? [],
  castingTimeType: spell.castingTimeType ?? "",
  rangeMeters: spell.rangeMeters != null ? String(spell.rangeMeters) : "",
  targetType: spell.targetType ?? "",
  maxTargets: spell.maxTargets != null ? String(spell.maxTargets) : "",
  selectionType: spell.selectionType ?? "",
  originType: spell.originType ?? "",
  targetAnchor: spell.targetAnchor ?? "",
  attackType: spell.attackType ?? "",
  rangeKind: spell.rangeKind ?? "",
  effectTiming: spell.effectTiming ?? "",
  areaShape: spell.areaShape ?? "",
  radiusMeters:
    spell.radiusMeters != null
      ? String(spell.radiusMeters)
      : "",
  lengthMeters:
    spell.lengthMeters != null
      ? String(spell.lengthMeters)
      : "",
  sideMeters:
    spell.sideMeters != null
      ? String(spell.sideMeters)
      : "",
  duration: spell.duration ?? "",
  componentsJson: spell.componentsJson ?? [],
  materialComponentText: spell.materialComponentText ?? "",
  concentration: spell.concentration,
  ritual: spell.ritual,
  resolutionType: spell.resolutionType ?? "",
  savingThrow: spell.savingThrow ?? "",
  saveSuccessOutcome: spell.saveSuccessOutcome ?? "",
  damageDice: spell.damageDice ?? "",
  damageType: spell.damageType ?? "",
  healDice: spell.healDice ?? "",
  upcastMode: spell.upcast?.mode ?? "",
  upcastDice: spell.upcast?.dice ?? "",
  upcastFlat: spell.upcast?.flat != null ? String(spell.upcast.flat) : "",
  upcastPerLevel: spell.upcast?.perLevel != null ? String(spell.upcast.perLevel) : "1",
  upcastMaxLevel: spell.upcast?.maxLevel != null ? String(spell.upcast.maxLevel) : "",
  upcastScalingKey: spell.upcast?.scalingKey ?? "",
  upcastScalingSummary: spell.upcast?.scalingSummary ?? "",
  upcastScalingEditorial: spell.upcast?.scalingEditorial ?? "",
  upcastUnlockKey: spell.upcast?.unlockKey ?? "",
  upcastUnlockSummary: spell.upcast?.unlockSummary ?? "",
  upcastUnlockEditorial: spell.upcast?.unlockEditorial ?? "",
  source: spell.source ?? SpellSourceValues.ADMIN_PANEL,
  sourceRef: spell.sourceRef ?? "",
  isSrd: spell.isSrd,
  isActive: spell.isActive,
});

export const buildPayload = (
  form: FormState,
  isNew: boolean,
): { payload?: BaseSpellWritePayload; error?: string } => {
  const canonicalKey = normalizeCanonicalKey(form.canonicalKey);
  if (!canonicalKey) return { error: "Canonical key é obrigatório." };

  const nameEn = normalizeOptionalText(form.nameEn);
  if (!nameEn) return { error: "Nome EN é obrigatório." };

  const descriptionEn = normalizeOptionalText(form.descriptionEn);
  if (!descriptionEn) return { error: "Descrição EN é obrigatória." };

  const rangeMeters = parseOptionalInteger(form.rangeMeters, "Alcance (m)");
  if (rangeMeters.error) return { error: rangeMeters.error };
  if (rangeMeters.value !== undefined && rangeMeters.value < 0)
    return { error: "Alcance (m) não pode ser negativo." };

  const maxTargets = parseOptionalInteger(form.maxTargets, "Max targets");
  if (maxTargets.error) return { error: maxTargets.error };
  if (maxTargets.value !== undefined && maxTargets.value < 1)
    return { error: "Max targets deve ser pelo menos 1." };

  const radiusMeters = parseOptionalPositiveFloat(form.radiusMeters, "Raio (m)");
  if (radiusMeters.error) return { error: radiusMeters.error };
  if (radiusMeters.value !== undefined && radiusMeters.value <= 0)
    return { error: "Raio (m) deve ser maior que 0." };

  const lengthMeters = parseOptionalPositiveFloat(form.lengthMeters, "Comprimento (m)");
  if (lengthMeters.error) return { error: lengthMeters.error };
  if (lengthMeters.value !== undefined && lengthMeters.value <= 0)
    return { error: "Comprimento (m) deve ser maior que 0." };

  const sideMeters = parseOptionalPositiveFloat(form.sideMeters, "Lado (m)");
  if (sideMeters.error) return { error: sideMeters.error };
  if (sideMeters.value !== undefined && sideMeters.value <= 0)
    return { error: "Lado (m) deve ser maior que 0." };

  const upcastFlat = parseOptionalInteger(form.upcastFlat, "Upcast flat");
  if (upcastFlat.error) return { error: upcastFlat.error };
  const upcastPerLevel = parseOptionalInteger(form.upcastPerLevel, "Upcast por nível");
  if (upcastPerLevel.error) return { error: upcastPerLevel.error };
  const upcastMaxLevel = parseOptionalInteger(form.upcastMaxLevel, "Upcast nível máximo");
  if (upcastMaxLevel.error) return { error: upcastMaxLevel.error };

  const showDamage = form.resolutionType === "damage";
  const showHealDice = form.resolutionType === "heal";
  const showSavingThrow =
    form.resolutionType === "damage" ||
    form.resolutionType === "control" ||
    form.resolutionType === "debuff";
  const showSaveSuccessOutcome = showDamage && Boolean(form.savingThrow);

  if (
    showDamage &&
    !buildDiceExpression(
      form.damageDiceCount,
      form.damageDieSize,
      form.damageFixedBonus,
    )
  )
    return { error: "Dados de dano são obrigatórios para resolutionType damage." };
  if (showHealDice && !form.healDice.trim())
    return { error: "Heal dice é obrigatório para resolutionType heal." };
  if (form.upcastMode === "extra_damage_dice" && !showDamage)
    return { error: "Upcast extra_damage_dice exige resolutionType damage." };
  if (form.upcastMode === "extra_heal_dice" && !showHealDice)
    return { error: "Upcast extra_heal_dice exige resolutionType heal." };
  if (
    (form.upcastMode === "extra_damage_dice" || form.upcastMode === "extra_heal_dice" || form.upcastMode === "flat_bonus")
    && !buildDiceExpression(
      form.upcastDiceCount,
      form.upcastDieSize,
      form.upcastFixedBonus,
    )
    && upcastFlat.value == null
  ) {
    return { error: "Upcast de dado/bônus exige dice ou flat." };
  }
  if (form.upcastMode === "flat_bonus" && !form.upcastFlat.trim())
    return { error: "Upcast flat_bonus exige valor flat." };
  if (form.upcastMode === "effect_scaling") {
    if (!form.upcastScalingKey.trim()) return { error: "effect_scaling exige scaling key." };
    if (!form.upcastScalingSummary.trim()) return { error: "effect_scaling exige scaling summary." };
  }
  if (form.upcastMode === "extra_effect") {
    if (!form.upcastUnlockKey.trim()) return { error: "extra_effect exige unlock key." };
    if (!form.upcastUnlockSummary.trim()) return { error: "extra_effect exige unlock summary." };
  }

  return {
    payload: {
      ...(isNew ? { system: form.system, canonicalKey } : {}),
      nameEn,
      namePt: normalizeOptionalText(form.namePt) ?? null,
      descriptionEn,
      descriptionPt: normalizeOptionalText(form.descriptionPt) ?? null,
      level: form.level,
      school: form.school,
      classesJson: form.classesJson.length > 0 ? form.classesJson : null,
      castingTimeType: form.castingTimeType || null,
      castingTime: deriveCastingTime(form.castingTimeType),
      rangeMeters: rangeMeters.value ?? null,
      rangeText: deriveRangeText(form.targetType, form.rangeMeters),
      targetType: form.targetType || null,
      maxTargets: maxTargets.value ?? null,
      selectionType: form.selectionType || null,
      originType: form.originType || null,
      targetAnchor: form.targetAnchor || null,
      attackType: form.attackType || null,
      rangeKind: form.rangeKind || null,
      effectTiming: form.effectTiming || null,
      areaShape: form.areaShape || null,
      radiusMeters:
        form.areaShape === "sphere" || form.areaShape === "cylinder"
          ? radiusMeters.value ?? null
          : null,
      lengthMeters:
        form.areaShape === "cone" || form.areaShape === "line"
          ? lengthMeters.value ?? null
          : null,
      sideMeters:
        form.areaShape === "cube"
          ? sideMeters.value ?? null
          : null,
      duration: normalizeOptionalText(form.duration) ?? null,
      componentsJson: form.componentsJson.length > 0 ? form.componentsJson : null,
      materialComponentText: form.componentsJson.includes("M")
        ? normalizeOptionalText(form.materialComponentText) ?? null
        : null,
      concentration: form.concentration,
      ritual: form.ritual,
      resolutionType: form.resolutionType || null,
      savingThrow: showSavingThrow ? form.savingThrow || null : null,
      saveSuccessOutcome: showSaveSuccessOutcome ? form.saveSuccessOutcome || null : null,
      damageDice: showDamage
        ? buildDiceExpression(
            form.damageDiceCount,
            form.damageDieSize,
            form.damageFixedBonus,
          )
        : null,
      damageType: showDamage ? form.damageType || null : null,
      healDice: showHealDice ? normalizeOptionalText(form.healDice) ?? null : null,
      upcast: form.upcastMode
        ? {
            mode: form.upcastMode,
            dice: buildDiceExpression(
              form.upcastDiceCount,
              form.upcastDieSize,
              form.upcastFixedBonus,
            ),
            flat: upcastFlat.value ?? null,
            perLevel: upcastPerLevel.value ?? 1,
            maxLevel: upcastMaxLevel.value ?? null,
            ...(form.upcastMode === "effect_scaling" ? {
              scalingKey: normalizeOptionalText(form.upcastScalingKey) ?? null,
              scalingSummary: normalizeOptionalText(form.upcastScalingSummary) ?? null,
              scalingEditorial: normalizeOptionalText(form.upcastScalingEditorial) ?? null,
            } : {}),
            ...(form.upcastMode === "extra_effect" ? {
              unlockKey: normalizeOptionalText(form.upcastUnlockKey) ?? null,
              unlockSummary: normalizeOptionalText(form.upcastUnlockSummary) ?? null,
              unlockEditorial: normalizeOptionalText(form.upcastUnlockEditorial) ?? null,
            } : {}),
          }
        : null,
      source: form.source,
      sourceRef: normalizeOptionalText(form.sourceRef) ?? null,
      isSrd: form.isSrd,
      isActive: form.isActive,
    },
  };
};
