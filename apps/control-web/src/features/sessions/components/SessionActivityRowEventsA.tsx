import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { formatSessionActivityOffset } from "./sessionActivity.utils";
import { localizeRollMode } from "./sessionActivityRowUtils";

// Covers event types: roll, shop, roll_request, combat, rest, reward

interface Props {
  event: ActivityEvent;
  actor: string;
}

export const SessionActivityRollRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "roll") return null;
  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">🎲</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {" "}
          {t("sessionActivity.rolled")}
          {" "}
          <span className="font-mono text-limiar-300">{event.expression}</span>
          {" → "}
          <span className="font-bold text-limiar-400">{event.total}</span>
          {event.results.length > 1 && (
            <span className="ml-1 text-xs text-slate-500">({event.results.join(", ")})</span>
          )}
        </p>
        {event.label && (
          <p className="mt-0.5 text-xs text-slate-400">
            {t("sessionActivity.reason")} {event.label}
          </p>
        )}
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityShopRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "shop") return null;
  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">{event.action === "opened" ? "🏪" : "🔒"}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {event.action === "opened"
            ? ` ${t("sessionActivity.shopOpened")}`
            : ` ${t("sessionActivity.shopClosed")}`}
        </p>
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityRollRequestRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "roll_request") return null;
  const target = event.targetDisplayName ?? t("sessionActivity.allPlayers");
  const modeLabel = localizeRollMode(event.mode, t);
  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">🎯</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {" "}
          {t("sessionActivity.rollRequested")}
          {" "}
          <span className="font-mono text-limiar-300">{event.expression}</span>
          {" "}
          {t("sessionActivity.rollRequestedTarget")}
          {" "}
          <span className="font-semibold text-slate-200">{target}</span>
        </p>
        {(event.reason || event.mode) && (
          <p className="mt-0.5 text-xs text-slate-400">
            {event.reason ? `${t("sessionActivity.reason")} ${event.reason}` : ""}
            {event.reason && event.mode ? " · " : ""}
            {modeLabel ?? ""}
          </p>
        )}
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityCombatRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "combat") return null;
  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">⚔️</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {event.action === "started"
            ? ` ${t("sessionActivity.combatStarted")}`
            : ` ${t("sessionActivity.combatEnded")}`}
        </p>
        {event.note && <p className="mt-0.5 text-xs text-slate-400">{event.note}</p>}
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityRestRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "rest") return null;
  const summary =
    event.action === "short_started"
      ? t("sessionActivity.shortRestStarted")
      : event.action === "short_ended"
        ? t("sessionActivity.shortRestEnded")
        : event.action === "long_started"
          ? t("sessionActivity.longRestStarted")
          : t("sessionActivity.longRestEnded");

  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">{event.action.includes("long") ? "🌙" : "☕"}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {" "}
          {summary}
        </p>
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityRewardRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "reward") return null;
  const target = event.targetDisplayName ?? t("sessionActivity.unknownTarget");
  const summary =
    event.action === "currency"
      ? `${t("sessionActivity.grantedCurrency")} ${event.amountLabel ?? "?"} ${t("sessionActivity.toTarget")} ${target}`
      : event.action === "item"
        ? `${t("sessionActivity.grantedItem")} ${event.itemName ?? t("inventory.unknownItem")}${event.quantity && event.quantity > 1 ? ` ×${event.quantity}` : ""} ${t("sessionActivity.toTarget")} ${target}`
        : `${t("sessionActivity.grantedXp")} ${event.amountLabel ?? "?"} ${t("sessionActivity.toTarget")} ${target}`;

  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">{event.action === "xp" ? "⭐" : event.action === "item" ? "🎁" : "💰"}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {" "}
          {summary}
        </p>
        {event.action === "xp" && event.currentXp != null && (
          <p className="mt-0.5 text-xs text-slate-400">
            {event.nextLevelThreshold != null
              ? `${t("sessionActivity.currentXp")} ${event.currentXp}/${event.nextLevelThreshold}`
              : `${t("sessionActivity.currentXp")} ${event.currentXp}`}
          </p>
        )}
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};
