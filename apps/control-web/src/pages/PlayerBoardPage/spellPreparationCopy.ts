import type { PendingSpellPreparation } from "../../shared/api/combatRepo";
import type { SessionRestState } from "../../features/sessions/hooks/sessionRuntime.types";
import type { LocaleKey } from "../../shared/i18n";

export type SpellPreparationCopyMode = "initial_setup" | "during_long_rest" | "fallback";

const SPELL_PREPARATION_COPY_KEYS: Record<
  SpellPreparationCopyMode,
  {
    description: LocaleKey;
    title: LocaleKey;
  }
> = {
  initial_setup: {
    title: "playerBoard.prepareSpellsInitialPrompt",
    description: "playerBoard.prepareSpellsInitialDescription",
  },
  during_long_rest: {
    title: "playerBoard.prepareSpellsDuringLongRestPrompt",
    description: "playerBoard.prepareSpellsDuringLongRestDescription",
  },
  fallback: {
    title: "playerBoard.prepareSpellsPrompt",
    description: "playerBoard.prepareSpellsDescription",
  },
};

export const resolveSpellPreparationCopyMode = (
  pendingSpellPreparation: PendingSpellPreparation | null | undefined,
  restState: SessionRestState,
): SpellPreparationCopyMode => {
  if (pendingSpellPreparation?.source === "initial_setup") return "initial_setup";
  if (pendingSpellPreparation?.availableDuringRest === true && restState === "long_rest")
    return "during_long_rest";
  return "fallback";
};

export const getSpellPreparationCopyKeys = (copyMode: SpellPreparationCopyMode) =>
  SPELL_PREPARATION_COPY_KEYS[copyMode];
