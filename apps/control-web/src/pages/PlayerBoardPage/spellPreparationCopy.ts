import type { PendingSpellPreparation } from "../../shared/api/combatRepo";
import type { SessionRestState } from "../../features/sessions/hooks/sessionRuntime.types";
import type { LocaleKey } from "../../shared/i18n";

export type SpellPreparationCopyMode = "during_long_rest" | "fallback";

const SPELL_PREPARATION_COPY_KEYS: Record<
  SpellPreparationCopyMode,
  {
    description: LocaleKey;
    title: LocaleKey;
  }
> = {
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
): SpellPreparationCopyMode =>
  pendingSpellPreparation?.availableDuringRest === true && restState === "long_rest"
    ? "during_long_rest"
    : "fallback";

export const getSpellPreparationCopyKeys = (copyMode: SpellPreparationCopyMode) =>
  SPELL_PREPARATION_COPY_KEYS[copyMode];
