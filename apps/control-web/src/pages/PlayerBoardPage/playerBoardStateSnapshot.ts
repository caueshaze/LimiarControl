import type { ActiveConcentration, SessionStateRecord } from "../../entities/character";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { parseCharacterSheet } from "../../features/character-sheet/model/characterSheet.schema";
import { EMPTY_WALLET, normalizeWallet } from "../../features/shop/utils/shopCurrency";
import type { ActiveEffect, PendingSpellPreparation } from "../../shared/api/combatRepo";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";

type SessionStateRecordLike = Pick<
  SessionStateRecord,
  "state" | "activeConcentration" | "activeSpellEffects" | "pendingSpellPreparation"
>;

export type PlayerBoardStateSnapshot = {
  activeConcentration: ActiveConcentration | null;
  activeSpellEffects: ActiveEffect[] | null;
  pendingSpellPreparation: PendingSpellPreparation | null;
  playerSheet: CharacterSheet;
  playerWallet: CurrencyWallet;
};

const asRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;

const normalizeActiveSpellEffectsFromState = (state: unknown): ActiveEffect[] | null => {
  const rawEffects = asRecord(state)?.active_spell_effects;
  return Array.isArray(rawEffects) ? (rawEffects as ActiveEffect[]) : null;
};

const normalizePendingSpellPreparationFromState = (
  state: unknown,
): PendingSpellPreparation | null => {
  const rawPending = asRecord(state)?.pending_spell_preparation;
  const pending = asRecord(rawPending);
  if (!pending) return null;

  const currentPreparedSpellIds = Array.isArray(pending.current_prepared_spell_ids)
    ? pending.current_prepared_spell_ids.filter(
        (spellId): spellId is string => typeof spellId === "string",
      )
    : [];

  return {
    source: typeof pending.source === "string" ? pending.source : "long_rest",
    classKey: typeof pending.class_key === "string" ? pending.class_key : "",
    preparedLimit:
      typeof pending.prepared_limit === "number" ? pending.prepared_limit : 0,
    currentPreparedSpellIds,
    createdAt: typeof pending.created_at === "string" ? pending.created_at : "",
    availableDuringRest: pending.available_during_rest === true,
  };
};

const deriveActiveConcentrationFromState = (
  state: unknown,
): ActiveConcentration | null => {
  const effects = normalizeActiveSpellEffectsFromState(state);
  if (!effects?.length) return null;

  let firstGroup: string | null = null;
  let firstMetadata: Record<string, unknown> | null = null;

  for (const effect of effects) {
    const metadata = asRecord(effect.metadata);
    if (!metadata || metadata.concentration !== true) continue;
    firstGroup =
      typeof metadata.concentration_group === "string"
        ? metadata.concentration_group
        : null;
    firstMetadata = metadata;
    break;
  }

  if (!firstMetadata) return null;

  const effectIds = firstGroup
    ? effects
        .filter(
          (effect) =>
            asRecord(effect.metadata)?.concentration_group === firstGroup &&
            typeof effect.id === "string",
        )
        .map((effect) => effect.id)
    : effects
        .filter(
          (effect) =>
            asRecord(effect.metadata)?.concentration === true &&
            typeof effect.id === "string",
        )
        .map((effect) => effect.id)
        .slice(0, 1);

  return {
    spellKey:
      typeof firstMetadata.source_spell_key === "string"
        ? firstMetadata.source_spell_key
        : null,
    spellName:
      typeof firstMetadata.source_spell_name === "string"
        ? firstMetadata.source_spell_name
        : null,
    variantKey:
      typeof firstMetadata.selected_variant_key === "string"
        ? firstMetadata.selected_variant_key
        : null,
    variantLabel:
      typeof firstMetadata.selected_variant_label === "string"
        ? firstMetadata.selected_variant_label
        : null,
    concentrationGroup: firstGroup,
    effectIds,
  };
};

export const parsePlayerBoardStateSnapshot = (
  record: SessionStateRecordLike,
): PlayerBoardStateSnapshot | null => {
  try {
    const playerSheet = parseCharacterSheet(record.state);
    const playerWallet = normalizeWallet(playerSheet.currency) ?? EMPTY_WALLET;

    return {
      playerSheet,
      playerWallet,
      activeConcentration:
        record.activeConcentration !== undefined
          ? record.activeConcentration
          : deriveActiveConcentrationFromState(record.state),
      activeSpellEffects:
        record.activeSpellEffects !== undefined
          ? (record.activeSpellEffects as ActiveEffect[] | null)
          : normalizeActiveSpellEffectsFromState(record.state),
      pendingSpellPreparation:
        record.pendingSpellPreparation !== undefined
          ? (record.pendingSpellPreparation as PendingSpellPreparation | null)
          : normalizePendingSpellPreparationFromState(record.state),
    };
  } catch {
    return null;
  }
};
