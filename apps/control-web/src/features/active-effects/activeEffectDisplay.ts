import { formatDeclarativeEffectSummaryLine } from "../combat-ui/spellVariantUi";
import type { Locale, LocaleKey } from "../../shared/i18n";

export type ActiveEffectLifecycleBadge = {
  key: string;
  i18nKey: LocaleKey;
  params?: Record<string, string | number>;
};

export type ActiveEffectDisplayGroup = {
  effects: Record<string, unknown>[];
  groupKey: string | null;
  title: string | null;
  summaryLines: string[];
};

const CREATURE_SIZE_LABELS: Record<Locale, Record<string, string>> = {
  en: {
    tiny: "Tiny",
    small: "Small",
    medium: "Medium",
    large: "Large",
    huge: "Huge",
    gargantuan: "Gargantuan",
  },
  pt: {
    tiny: "Minúsculo",
    small: "Pequeno",
    medium: "Médio",
    large: "Grande",
    huge: "Enorme",
    gargantuan: "Colossal",
  },
};

const normalizeSize = (size: unknown) =>
  typeof size === "string" && size.trim() ? size.trim().toLowerCase() : null;

export const formatCreatureSize = (size: unknown, locale: Locale = "pt") => {
  const normalized = normalizeSize(size);
  if (!normalized) {
    return null;
  }
  return CREATURE_SIZE_LABELS[locale][normalized] ?? normalized;
};

export const formatEffectiveCreatureSize = (
  participant: {
    base_size?: string | null;
    effective_size?: string | null;
  },
  locale: Locale = "pt",
) => {
  const baseSize = normalizeSize(participant.base_size) ?? "medium";
  const effectiveSize = normalizeSize(participant.effective_size);
  if (!effectiveSize || effectiveSize === baseSize) {
    return null;
  }
  const effectiveLabel = formatCreatureSize(effectiveSize, locale);
  const baseLabel = formatCreatureSize(baseSize, locale);
  if (!effectiveLabel || !baseLabel) {
    return null;
  }
  return `Tamanho atual: ${effectiveLabel} (base ${baseLabel})`;
};

export const formatActiveEffectLabel = (
  effect: Record<string, unknown>,
): string | null => {
  const metadata = ((effect.metadata ?? {}) as Record<string, unknown>) || {};
  const variantLabel = metadata.selected_variant_label as string | undefined;
  const spellName = metadata.source_spell_name as string | undefined;
  const displayLabel = effect.display_label as string | undefined;
  const spellKey = metadata.source_spell_key as string | undefined;

  if (spellName && variantLabel) return `${spellName} \u2014 ${variantLabel}`;
  if (variantLabel) return variantLabel;
  if (displayLabel) return displayLabel;
  if (spellName) return spellName;
  if (spellKey) return spellKey;
  return null;
};

const getGroupKey = (effect: Record<string, unknown>) => {
  const metadata = ((effect.metadata ?? {}) as Record<string, unknown>) || {};
  const declarativeGroup = metadata.declarative_effect_group_id;
  if (typeof declarativeGroup === "string" && declarativeGroup.trim()) {
    return `declarative:${declarativeGroup.trim()}`;
  }
  const concentrationGroup = metadata.concentration_group;
  if (typeof concentrationGroup === "string" && concentrationGroup.trim()) {
    return `concentration:${concentrationGroup.trim()}`;
  }
  return null;
};

export const buildActiveEffectGroupTitle = (
  group: Pick<ActiveEffectDisplayGroup, "effects">,
) => {
  const first = group.effects[0];
  if (!first) {
    return null;
  }
  const metadata = ((first.metadata ?? {}) as Record<string, unknown>) || {};
  const spellName = typeof metadata.source_spell_name === "string" ? metadata.source_spell_name.trim() : "";
  const variantLabel = typeof metadata.selected_variant_label === "string" ? metadata.selected_variant_label.trim() : "";
  if (spellName && variantLabel) {
    return `${spellName} \u2014 ${variantLabel}`;
  }
  if (spellName) {
    return spellName;
  }
  if (variantLabel) {
    return variantLabel;
  }
  return formatActiveEffectLabel(first);
};

const buildSummaryLines = (effects: Record<string, unknown>[]) =>
  effects
    .map((effect) => {
      const metadata = ((effect.metadata ?? {}) as Record<string, unknown>) || {};
      const declarative = metadata.declarative_effect;
      if (!declarative || typeof declarative !== "object") {
        return null;
      }
      return formatDeclarativeEffectSummaryLine(
        declarative as { type?: unknown; params?: Record<string, unknown> | null },
        metadata,
      );
    })
    .filter((line): line is string => Boolean(line));

export const groupActiveEffectsForDisplay = (
  effects: Record<string, unknown>[] | null | undefined,
): ActiveEffectDisplayGroup[] => {
  if (!effects?.length) {
    return [];
  }
  const grouped = new Map<string, Record<string, unknown>[]>();
  const output: ActiveEffectDisplayGroup[] = [];

  effects.forEach((effect) => {
    const groupKey = getGroupKey(effect);
    if (!groupKey) {
      output.push({
        effects: [effect],
        groupKey: null,
        title: formatActiveEffectLabel(effect),
        summaryLines: buildSummaryLines([effect]),
      });
      return;
    }
    grouped.set(groupKey, [...(grouped.get(groupKey) ?? []), effect]);
  });

  grouped.forEach((groupEffects, groupKey) => {
    const group = {
      effects: groupEffects,
      groupKey,
      title: null,
      summaryLines: buildSummaryLines(groupEffects),
    };
    output.push({
      ...group,
      title: buildActiveEffectGroupTitle(group),
    });
  });

  return output;
};

export const getActiveEffectLifecycleBadges = (
  effect: Record<string, unknown>,
): ActiveEffectLifecycleBadge[] => {
  const badges: ActiveEffectLifecycleBadge[] = [];
  const metadata = ((effect.metadata ?? {}) as Record<string, unknown>) || {};
  const durationType = effect.duration_type as string | undefined;

  if (metadata.concentration === true) {
    badges.push({
      key: "concentration",
      i18nKey: "playerBoard.lifecycleConcentration",
    });
  }

  if (durationType === "manual") {
    badges.push({
      key: "manual",
      i18nKey: "playerBoard.lifecycleManual",
    });
  } else if (durationType === "rounds") {
    const remaining = effect.remaining_rounds;
    if (typeof remaining === "number") {
      badges.push({
        key: "rounds",
        i18nKey: "playerBoard.lifecycleRounds",
        params: { count: remaining },
      });
    } else {
      badges.push({
        key: "rounds-unknown",
        i18nKey: "playerBoard.lifecycleRoundsUnknown",
      });
    }
  } else if (durationType === "until_turn_start") {
    badges.push({
      key: "until-turn-start",
      i18nKey: "playerBoard.lifecycleUntilTurnStart",
    });
  } else if (durationType === "until_turn_end") {
    badges.push({
      key: "until-turn-end",
      i18nKey: "playerBoard.lifecycleUntilTurnEnd",
    });
  } else if (durationType === "until_long_rest") {
    badges.push({
      key: "until-long-rest",
      i18nKey: "playerBoard.lifecycleUntilLongRest",
    });
  } else if (durationType === "until_short_rest") {
    badges.push({
      key: "until-short-rest",
      i18nKey: "playerBoard.lifecycleUntilShortRest",
    });
  } else if (durationType === "until_removed") {
    badges.push({
      key: "until-removed",
      i18nKey: "playerBoard.lifecycleUntilRemoved",
    });
  }

  if (durationType === "manual") {
    badges.push({
      key: "long-rest",
      i18nKey: "playerBoard.lifecycleLongRest",
    });
  }

  return badges;
};
