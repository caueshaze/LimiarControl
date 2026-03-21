import { useEffect, useRef } from "react";

import type { LocaleKey } from "../../shared/i18n";
import type { ToastState } from "../../shared/ui/Toast";

type CampaignEventLike = {
  type: string;
  payload: Record<string, unknown>;
};

type Props = {
  lastEvent: CampaignEventLike | null;
  restState: "exploration" | "short_rest" | "long_rest";
  showToast: (toast: ToastState) => void;
  t: (key: LocaleKey) => string;
  userId?: string | null;
};

export const usePlayerBoardRestFeedback = ({
  lastEvent,
  restState,
  showToast,
  t,
  userId = null,
}: Props) => {
  const previousRestStateRef = useRef<"exploration" | "short_rest" | "long_rest" | null>(null);

  useEffect(() => {
    const previousRestState = previousRestStateRef.current;
    previousRestStateRef.current = restState;

    if (previousRestState === restState) {
      return;
    }

    if (restState === "short_rest") {
      showToast({
        variant: "info",
        title: t("playerBoard.shortRestStartedTitle"),
        description: t("playerBoard.shortRestStartedDescription"),
      });
      return;
    }

    if (restState === "long_rest") {
      showToast({
        variant: "info",
        title: t("playerBoard.longRestStartedTitle"),
        description: t("playerBoard.longRestStartedDescription"),
      });
      return;
    }

    if (previousRestState === "short_rest") {
      showToast({
        variant: "info",
        title: t("playerBoard.shortRestEndedTitle"),
        description: t("playerBoard.shortRestEndedDescription"),
      });
      return;
    }

    if (previousRestState === "long_rest") {
      showToast({
        variant: "info",
        title: t("playerBoard.longRestEndedTitle"),
        description: t("playerBoard.longRestEndedDescription"),
      });
    }
  }, [restState, showToast, t]);

  useEffect(() => {
    if (!lastEvent) {
      return;
    }

    if (lastEvent.type === "hit_dice_used") {
      const playerUserId =
        typeof lastEvent.payload.playerUserId === "string" ? lastEvent.payload.playerUserId : null;
      if (!playerUserId || playerUserId !== userId) {
        return;
      }
      showToast({
        variant: "success",
        title: t("playerBoard.hitDieUsedTitle"),
        description: t("playerBoard.hitDieUsedDescription")
          .replace("{healing}", String(lastEvent.payload.healingApplied ?? 0))
          .replace("{roll}", String(lastEvent.payload.roll ?? 0)),
      });
    }
  }, [lastEvent, showToast, t, userId]);
};
