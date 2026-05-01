import type { SpellVariant, SpellVariantManualNote } from "../../../entities/base-spell";

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

const hasEffectEntries = (length: number | undefined) => Boolean(length && length > 0);

export const getSpellVariantWarnings = (variants: SpellVariant[]) => {
  const normalizedKeys = variants
    .map((variant) => variant.key.trim())
    .filter(Boolean);
  const duplicateKeys = new Set(
    normalizedKeys.filter((key, index) => normalizedKeys.indexOf(key) !== index),
  );

  const warnings: string[] = [];
  if (variants.some((variant) => variant.key.trim().length === 0)) {
    warnings.push("Algumas variantes ainda estão sem chave.");
  }
  if (duplicateKeys.size > 0) {
    warnings.push(
      `Chaves duplicadas: ${Array.from(duplicateKeys)
        .sort()
        .join(", ")}.`,
    );
  }
  if (
    variants.some(
      (variant) =>
        !trimToNull(variant.labelPt) &&
        !trimToNull(variant.labelEn) &&
        !trimToNull(variant.descriptionPt) &&
        !trimToNull(variant.descriptionEn),
    )
  ) {
    warnings.push(
      "Algumas variantes estão sem rótulos e descrições localizadas. A magia continuará válida, mas ficará ruim de operar no cast.",
    );
  }
  return warnings;
};

export const getSpellVariantErrors = (variants: SpellVariant[]) =>
  normalizeSpellVariantsForPayload(variants).errors;

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

  const firstManualNote = variant.manualNotes?.find(
    (note) => note.label.trim() || note.description.trim() || note.key.trim(),
  );
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
): { variants: SpellVariant[] | null; errors: string[] } => {
  if (variants.length === 0) {
    return { variants: null, errors: [] };
  }

  const errors: string[] = [];
  const normalizedVariants = variants.map((variant, variantIndex) => {
    const key = variant.key.trim();
    if (!key) {
      errors.push(`Variante ${variantIndex + 1} precisa de uma chave.`);
    }
    if (!(variant.effects?.length) && !(variant.manualNotes?.some((note) => note.key.trim() || note.label.trim() || note.description.trim()))) {
      errors.push(
        `Variante ${key || variantIndex + 1} precisa de ao menos um efeito declarativo ou nota manual.`,
      );
    }

    const normalizedManualNotes = (variant.manualNotes ?? [])
      .map((note, noteIndex) => {
        const hasAnyValue = Boolean(
          note.key.trim() || note.label.trim() || note.description.trim(),
        );
        if (!hasAnyValue) {
          return null;
        }
        if (!note.key.trim() || !note.label.trim() || !note.description.trim()) {
          errors.push(
            `Nota manual ${noteIndex + 1} da variante ${key || variantIndex + 1} precisa de chave, rótulo e descrição.`,
          );
        }
        return {
          key: note.key.trim(),
          label: note.label.trim(),
          description: note.description.trim(),
        };
      })
      .filter((entry): entry is SpellVariantManualNote => Boolean(entry));

    return {
      key,
      labelPt: variant.labelPt.trim(),
      labelEn: trimToNull(variant.labelEn),
      descriptionPt: trimToNull(variant.descriptionPt),
      descriptionEn: trimToNull(variant.descriptionEn),
      effects: hasEffectEntries(variant.effects?.length) ? variant.effects ?? [] : null,
      onEndEffects: hasEffectEntries(variant.onEndEffects?.length)
        ? variant.onEndEffects ?? []
        : null,
      manualNotes: normalizedManualNotes.length > 0 ? normalizedManualNotes : null,
    } satisfies SpellVariant;
  });

  const seenKeys = new Set<string>();
  for (const variant of normalizedVariants) {
    if (!variant.key) continue;
    if (seenKeys.has(variant.key)) {
      errors.push(`Chave de variante duplicada: ${variant.key}.`);
    }
    seenKeys.add(variant.key);
  }

  return {
    variants: normalizedVariants,
    errors,
  };
};
