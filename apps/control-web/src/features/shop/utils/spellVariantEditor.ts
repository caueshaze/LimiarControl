import type { SpellVariant, SpellVariantManualNote } from "../../../entities/base-spell";
import type { Locale } from "../../../shared/i18n";

export type SpellVariantIssue = {
  severity: "error" | "warning";
  message: string;
  variantIndex: number;
  noteIndex?: number;
};

export type SpellVariantValidationResult = {
  issues: SpellVariantIssue[];
  errors: SpellVariantIssue[];
  warnings: SpellVariantIssue[];
  hasBlockingErrors: boolean;
};

export const createEmptySpellVariantManualNote = (): SpellVariantManualNote => ({
  key: "",
  label: "",
  description: "",
});

export const createEmptySpellVariant = (): SpellVariant => ({
  key: "",
  labelPt: "",
  labelEn: "",
  descriptionPt: "",
  descriptionEn: "",
  effects: [],
  onEndEffects: [],
  manualNotes: [],
});

export const addSpellVariant = (variants: SpellVariant[]) => [
  ...variants,
  createEmptySpellVariant(),
];

export const removeSpellVariant = (variants: SpellVariant[], index: number) =>
  variants.filter((_, entryIndex) => entryIndex !== index);

const trimToNull = (value: string | null | undefined) => {
  const normalized = value?.trim() ?? "";
  return normalized.length > 0 ? normalized : null;
};

const humanizeVariantKey = (variantKey: string) =>
  variantKey
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

const hasAutomatedEffects = (variant: SpellVariant) =>
  Boolean((variant.effects?.length ?? 0) > 0 || (variant.onEndEffects?.length ?? 0) > 0);

const noteHasAnyValue = (note: SpellVariantManualNote) =>
  Boolean(note.key.trim() || note.label.trim() || note.description.trim());

const getCurrentLocaleLabel = (variant: SpellVariant, locale: Locale) =>
  locale === "en" ? trimToNull(variant.labelEn) : trimToNull(variant.labelPt);

const getOtherLocaleLabel = (variant: SpellVariant, locale: Locale) =>
  locale === "en" ? trimToNull(variant.labelPt) : trimToNull(variant.labelEn);

const getCurrentLocaleDescription = (variant: SpellVariant, locale: Locale) =>
  locale === "en" ? trimToNull(variant.descriptionEn) : trimToNull(variant.descriptionPt);

const getOtherLocaleDescription = (variant: SpellVariant, locale: Locale) =>
  locale === "en" ? trimToNull(variant.descriptionPt) : trimToNull(variant.descriptionEn);

export const validateSpellVariants = (
  variants: SpellVariant[],
  locale: Locale = "pt",
): SpellVariantValidationResult => {
  const issues: SpellVariantIssue[] = [];
  const seenKeys = new Map<string, number>();

  variants.forEach((variant, variantIndex) => {
    const key = variant.key.trim();
    const currentLabel = getCurrentLocaleLabel(variant, locale);
    const otherLabel = getOtherLocaleLabel(variant, locale);
    const currentDescription = getCurrentLocaleDescription(variant, locale);
    const otherDescription = getOtherLocaleDescription(variant, locale);
    const activeManualNotes = (variant.manualNotes ?? []).filter(noteHasAnyValue);
    const hasAnyEffect = hasAutomatedEffects(variant);

    if (!key) {
      issues.push({
        severity: "error",
        message: `Variante ${variantIndex + 1} precisa de uma chave.`,
        variantIndex,
      });
    } else if (seenKeys.has(key)) {
      issues.push({
        severity: "error",
        message: `Chave de variante duplicada: ${key}.`,
        variantIndex,
      });
      issues.push({
        severity: "error",
        message: `Chave de variante duplicada: ${key}.`,
        variantIndex: seenKeys.get(key) ?? variantIndex,
      });
    } else {
      seenKeys.set(key, variantIndex);
    }

    if (!currentLabel) {
      issues.push({
        severity: "error",
        message:
          locale === "en"
            ? `Variant ${key || variantIndex + 1} needs an English label.`
            : `Variante ${key || variantIndex + 1} precisa de um rótulo em português.`,
        variantIndex,
      });
    }

    if (!hasAnyEffect && activeManualNotes.length === 0) {
      issues.push({
        severity: "error",
        message: `Variante ${key || variantIndex + 1} precisa de ao menos um efeito declarativo, efeito ao terminar ou nota manual.`,
        variantIndex,
      });
    }

    if (currentLabel && !currentDescription) {
      issues.push({
        severity: "warning",
        message:
          locale === "en"
            ? `Variant ${key || variantIndex + 1} is missing an English description.`
            : `Variante ${key || variantIndex + 1} está sem descrição em português.`,
        variantIndex,
      });
    }

    if (!otherLabel || !otherDescription) {
      issues.push({
        severity: "warning",
        message:
          locale === "en"
            ? `Variant ${key || variantIndex + 1} is incomplete in PT localization.`
            : `Variante ${key || variantIndex + 1} está com localização EN incompleta.`,
        variantIndex,
      });
    }

    if (!hasAnyEffect && activeManualNotes.length > 0) {
      issues.push({
        severity: "warning",
        message: `Variante ${key || variantIndex + 1} depende apenas de notas manuais.`,
        variantIndex,
      });
    }

    (variant.manualNotes ?? []).forEach((note, noteIndex) => {
      if (!noteHasAnyValue(note)) {
        return;
      }
      if (!note.key.trim()) {
        issues.push({
          severity: "error",
          message: `Nota manual ${noteIndex + 1} da variante ${key || variantIndex + 1} precisa de uma chave.`,
          variantIndex,
          noteIndex,
        });
      }
      if (!note.label.trim() || !note.description.trim()) {
        issues.push({
          severity: "error",
          message: `Nota manual ${noteIndex + 1} da variante ${key || variantIndex + 1} precisa de rótulo e descrição.`,
          variantIndex,
          noteIndex,
        });
      }
    });
  });

  return {
    issues,
    errors: issues.filter((issue) => issue.severity === "error"),
    warnings: issues.filter((issue) => issue.severity === "warning"),
    hasBlockingErrors: issues.some((issue) => issue.severity === "error"),
  };
};

export const getSpellVariantWarnings = (variants: SpellVariant[], locale: Locale = "pt") =>
  validateSpellVariants(variants, locale).warnings.map((issue) => issue.message);

export const getSpellVariantErrors = (variants: SpellVariant[], locale: Locale = "pt") =>
  validateSpellVariants(variants, locale).errors.map((issue) => issue.message);

const summarizeEffect = (variant: SpellVariant, locale: "pt" | "en") => {
  const summaries = (variant.effects ?? []).map((effect) => {
    if (
      (effect.type === "advantage_on_checks" || effect.type === "disadvantage_on_checks") &&
      "ability" in effect.params
    ) {
      return `${effect.type} (${String(effect.params.ability).slice(0, 3).toUpperCase()})`;
    }
    if (effect.type === "apply_condition" && "condition" in effect.params) {
      return `condition (${effect.params.condition})`;
    }
    if (effect.type === "modify_stat" && "stat" in effect.params) {
      return `modify_stat (${effect.params.stat})`;
    }
    if (effect.type === "restrict_action" && "action" in effect.params) {
      return `restrict_action (${effect.params.action})`;
    }
    return effect.type;
  });

  const firstManualNote = variant.manualNotes?.find(noteHasAnyValue);
  if (firstManualNote) {
    summaries.push(`manual (${firstManualNote.label.trim() || firstManualNote.key.trim()})`);
  }

  if (summaries.length === 0) {
    return locale === "pt" ? "Sem efeito configurado" : "No configured effect";
  }

  return summaries.join(" + ");
};

export const summarizeSpellVariant = (variant: SpellVariant, locale: "pt" | "en" = "pt") =>
  summarizeEffect(variant, locale);

export const normalizeSpellVariantsForPayload = (
  variants: SpellVariant[],
  locale: Locale = "pt",
): { variants: SpellVariant[] | null; errors: string[] } => {
  if (variants.length === 0) {
    return { variants: null, errors: [] };
  }

  const validation = validateSpellVariants(variants, locale);
  if (validation.hasBlockingErrors) {
    return {
      variants: null,
      errors: validation.errors.map((issue) => issue.message),
    };
  }

  return {
    variants: variants.map((variant) => {
      const manualNotes = (variant.manualNotes ?? [])
        .filter(noteHasAnyValue)
        .map((note) => ({
          key: note.key.trim(),
          label: note.label.trim(),
          description: note.description.trim(),
        }));

      return {
        key: variant.key.trim(),
        labelPt: variant.labelPt.trim(),
        labelEn: trimToNull(variant.labelEn),
        descriptionPt: trimToNull(variant.descriptionPt),
        descriptionEn: trimToNull(variant.descriptionEn),
        effects: (variant.effects?.length ?? 0) > 0 ? variant.effects ?? [] : null,
        onEndEffects: (variant.onEndEffects?.length ?? 0) > 0 ? variant.onEndEffects ?? [] : null,
        manualNotes: manualNotes.length > 0 ? manualNotes : null,
      };
    }),
    errors: [],
  };
};

export const getVariantIssueLabel = (variant: SpellVariant, index: number) =>
  trimToNull(variant.labelPt) ??
  trimToNull(variant.labelEn) ??
  trimToNull(variant.key) ??
  `Variante ${index + 1}`;

export const describeUnknownVariantKey = (key: string) =>
  `Variante desconhecida (${humanizeVariantKey(key)})`;
