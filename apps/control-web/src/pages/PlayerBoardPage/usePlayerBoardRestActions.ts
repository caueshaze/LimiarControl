import { useCallback, useState } from "react";

import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { sessionsRepo } from "../../shared/api/sessionsRepo";
import type { LocaleKey } from "../../shared/i18n";
import type { ToastState } from "../../shared/ui/Toast";

type Props = {
  activeSessionId: string | null;
  setPlayerSheet: React.Dispatch<React.SetStateAction<CharacterSheet | null>>;
  showToast: (toast: ToastState) => void;
  t: (key: LocaleKey) => string;
};

export const usePlayerBoardRestActions = ({
  activeSessionId,
  setPlayerSheet,
  showToast,
  t,
}: Props) => {
  const [usingHitDie, setUsingHitDie] = useState(false);

  const handleUseHitDie = useCallback(async () => {
    if (!activeSessionId || usingHitDie) {
      return;
    }

    setUsingHitDie(true);
    try {
      const result = await sessionsRepo.useHitDie(activeSessionId);
      setPlayerSheet((current) =>
        current
          ? {
              ...current,
              currentHP: result.currentHp,
              hitDiceRemaining: result.hitDiceRemaining,
            }
          : current,
      );
    } catch (error) {
      showToast({
        variant: "error",
        title: t("playerBoard.hitDieUseErrorTitle"),
        description:
          (error as { message?: string })?.message ?? t("playerBoard.hitDieUseErrorDescription"),
      });
    } finally {
      setUsingHitDie(false);
    }
  }, [activeSessionId, setPlayerSheet, showToast, t, usingHitDie]);

  return {
    usingHitDie,
    handleUseHitDie,
  };
};
