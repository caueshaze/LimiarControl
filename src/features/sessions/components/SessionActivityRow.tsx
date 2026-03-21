import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { formatSessionActivityOffset } from "./sessionActivity.utils";

function formatEntityDisplayName(event: Extract<ActivityEvent, { type: "entity" }>): string {
  return event.label ? `${event.entityName} (${event.label})` : event.entityName;
}

function formatCurrentHp(event: Extract<ActivityEvent, { type: "entity" }>): string | null {
  if (event.currentHp == null) {
    return null;
  }
  if (event.maxHp != null) {
    return `${event.currentHp}/${event.maxHp}`;
  }
  return String(event.currentHp);
}

export const SessionActivityRow = ({ event }: { event: ActivityEvent }) => {
  const { t } = useLocale();
  const actor = event.displayName ?? event.username ?? "Unknown";

  if (event.type === "roll") {
    return (
      <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
        <span className="mt-0.5 text-base">🎲</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-white">
            <span className="font-semibold">{actor}</span>
            {" rolled "}
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
  }

  if (event.type === "shop") {
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
  }

  if (event.type === "roll_request") {
    const target = event.targetDisplayName ?? t("sessionActivity.allPlayers");
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
              {event.mode ? event.mode : ""}
            </p>
          )}
        </div>
        <span className="shrink-0 text-xs font-mono text-slate-500">
          {formatSessionActivityOffset(event.sessionOffsetSeconds)}
        </span>
      </div>
    );
  }

  if (event.type === "combat") {
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
  }

  if (event.type === "rest") {
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
  }

  if (event.type === "reward") {
    const target = event.targetDisplayName ?? t("sessionActivity.unknownTarget");
    const summary =
      event.action === "currency"
        ? `${t("sessionActivity.grantedCurrency")} ${event.amountLabel ?? "?"} ${t("sessionActivity.toTarget")} ${target}`
        : event.action === "item"
          ? `${t("sessionActivity.grantedItem")} ${event.itemName ?? "Item"}${event.quantity && event.quantity > 1 ? ` ×${event.quantity}` : ""} ${t("sessionActivity.toTarget")} ${target}`
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
  }

  if (event.type === "level_up") {
    const target = event.targetDisplayName ?? actor;
    const summary =
      event.action === "requested"
        ? `${target} ${t("sessionActivity.levelUpRequested")}`
        : event.action === "approved"
          ? `${t("sessionActivity.levelUpApproved")} ${target}`
          : `${t("sessionActivity.levelUpDenied")} ${target}`;

    return (
      <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
        <span className="mt-0.5 text-base">🆙</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-white">
            <span className="font-semibold">{actor}</span>
            {" "}
            {summary}
          </p>
          <p className="mt-0.5 text-xs text-slate-400">
            {`${t("sheet.basicInfo.level")} ${event.level} · XP ${event.experiencePoints}`}
          </p>
        </div>
        <span className="shrink-0 text-xs font-mono text-slate-500">
          {formatSessionActivityOffset(event.sessionOffsetSeconds)}
        </span>
      </div>
    );
  }

  if (event.type === "hit_dice") {
    return (
      <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
        <span className="mt-0.5 text-base">❤️‍🩹</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-white">
            <span className="font-semibold">{actor}</span>
            {" "}
            {t("sessionActivity.usedHitDie")}
          </p>
          <p className="mt-0.5 text-xs text-slate-400">
            {`${t("sessionActivity.roll")} ${event.roll} · ${t("sessionActivity.healedHp")} ${event.healingApplied} · ${t("sessionActivity.currentHp")} ${event.currentHp}${event.maxHp != null ? `/${event.maxHp}` : ""}`}
          </p>
        </div>
        <span className="shrink-0 text-xs font-mono text-slate-500">
          {formatSessionActivityOffset(event.sessionOffsetSeconds)}
        </span>
      </div>
    );
  }

  if (event.type === "player_hp") {
    const target = event.targetDisplayName ?? t("sessionActivity.unknownTarget");
    const summary =
      event.action === "damaged"
        ? `${t("sessionActivity.playerDamaged")} ${target} ${event.delta ?? 0} HP`
        : event.action === "healed"
          ? `${t("sessionActivity.playerHealed")} ${target} ${event.delta ?? 0} HP`
          : `${t("sessionActivity.playerHpSet")} ${target}`;

    return (
      <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
        <span className="mt-0.5 text-base">{event.action === "healed" ? "💚" : "🩸"}</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-white">
            <span className="font-semibold">{actor}</span>
            {" "}
            {summary}
          </p>
          {event.currentHp != null && (
            <p className="mt-0.5 text-xs text-slate-400">
              {`${t("sessionActivity.currentHp")} ${event.currentHp}${event.maxHp != null ? `/${event.maxHp}` : ""}`}
            </p>
          )}
        </div>
        <span className="shrink-0 text-xs font-mono text-slate-500">
          {formatSessionActivityOffset(event.sessionOffsetSeconds)}
        </span>
      </div>
    );
  }

  if (event.type === "entity") {
    const entityName = formatEntityDisplayName(event);
    const currentHp = formatCurrentHp(event);
    const summary =
      event.action === "added"
        ? `${t("sessionActivity.entityAdded")} ${entityName}`
        : event.action === "removed"
          ? `${t("sessionActivity.entityRemoved")} ${entityName}`
          : event.action === "revealed"
            ? `${t("sessionActivity.entityRevealed")} ${entityName}`
            : event.action === "hidden"
              ? `${t("sessionActivity.entityHidden")} ${entityName}`
              : event.action === "damaged"
                ? `${entityName} ${t("sessionActivity.entityDamaged")} ${event.delta ?? 0} HP`
                : event.action === "healed"
                  ? `${entityName} ${t("sessionActivity.entityHealed")} ${event.delta ?? 0} HP`
                  : `${entityName} ${t("sessionActivity.entityHpSet")} ${currentHp ?? "?"}`;

    return (
      <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
        <span className="mt-0.5 text-base">
          {event.action === "damaged" ? "🩸" : event.action === "healed" ? "💚" : "👁️"}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-white">
            <span className="font-semibold">{actor}</span>
            {" "}
            {summary}
          </p>
          {(currentHp || event.entityCategory) && (
            <p className="mt-0.5 text-xs text-slate-400">
              {event.entityCategory ? event.entityCategory : ""}
              {event.entityCategory && currentHp ? " · " : ""}
              {currentHp ? `${t("sessionActivity.currentHp")} ${currentHp}` : ""}
            </p>
          )}
        </div>
        <span className="shrink-0 text-xs font-mono text-slate-500">
          {formatSessionActivityOffset(event.sessionOffsetSeconds)}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">🛒</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {" bought "}
          <span className="font-semibold text-amber-300">{event.itemName}</span>
          {event.quantity > 1 && <span className="text-slate-400"> ×{event.quantity}</span>}
        </p>
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};
