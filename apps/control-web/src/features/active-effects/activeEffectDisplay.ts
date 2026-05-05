import type { LocaleKey } from "../../shared/i18n";

export type ActiveEffectLifecycleBadge = {
  key: string;
  i18nKey: LocaleKey;
  params?: Record<string, string | number>;
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
  }

  if (durationType === "manual") {
    badges.push({
      key: "long-rest",
      i18nKey: "playerBoard.lifecycleLongRest",
    });
  }

  return badges;
};
