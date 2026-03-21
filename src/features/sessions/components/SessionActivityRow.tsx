import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";

export function formatSessionActivityOffset(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}h${String(m).padStart(2, "0")}m`;
  }
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

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
