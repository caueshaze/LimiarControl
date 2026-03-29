import type { ActivityEvent, PurchaseActivityEvent } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { formatSessionActivityOffset } from "./sessionActivity.utils";
import {
  formatCurrentHp,
  formatEntityDisplayName,
  formatSignedModifier,
  localizeRollContext,
  localizeRollMode,
} from "./sessionActivityRowUtils";

// Covers event types: level_up, hit_dice, consumable, player_hp, entity, roll_resolved, purchase (default)

interface Props {
  event: ActivityEvent;
  actor: string;
  isGm?: boolean;
}

export const SessionActivityLevelUpRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "level_up") return null;
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
          {`${t("sheet.basicInfo.level")} ${event.level} · ${t("sessionActivity.xpLabel")} ${event.experiencePoints}`}
        </p>
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityHitDiceRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "hit_dice") return null;
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
};

export const SessionActivityConsumableRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "consumable") return null;
  const hpUnit = t("combatUi.hp");
  const target = event.targetDisplayName ?? t("sessionActivity.unknownTarget");
  const healingText =
    event.maxHp != null && event.newHp != null
      ? `${event.healingApplied} ${hpUnit} · ${event.newHp}/${event.maxHp}`
      : `${event.healingApplied} ${hpUnit}`;

  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">🧪</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {" "}
          {t("sessionActivity.usedConsumable")}
          {" "}
          <span className="font-semibold text-slate-100">{event.itemName}</span>
          {" "}
          {t("sessionActivity.onTarget")}
          {" "}
          <span className="font-semibold text-slate-200">{target}</span>
        </p>
        <p className="mt-0.5 text-xs text-slate-400">
          {`${t("sessionActivity.healedHp")} ${healingText}`}
          {typeof event.remainingQuantity === "number"
            ? ` · ${t("sessionActivity.remainingQuantity")} ${event.remainingQuantity}`
            : ""}
        </p>
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityPlayerHpRow = ({ event, actor }: Props) => {
  const { t } = useLocale();
  if (event.type !== "player_hp") return null;
  const hpUnit = t("combatUi.hp");
  const target = event.targetDisplayName ?? t("sessionActivity.unknownTarget");
  const summary =
    event.action === "damaged"
      ? `${t("sessionActivity.playerDamaged")} ${target} ${event.delta ?? 0} ${hpUnit}`
      : event.action === "healed"
        ? `${t("sessionActivity.playerHealed")} ${target} ${event.delta ?? 0} ${hpUnit}`
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
};

export const SessionActivityEntityRow = ({ event, actor, isGm = false }: Props) => {
  const { t } = useLocale();
  if (event.type !== "entity") return null;
  const hpUnit = t("combatUi.hp");
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
              ? `${entityName} ${t("sessionActivity.entityDamaged")} ${event.delta ?? 0} ${hpUnit}`
              : event.action === "healed"
                ? `${entityName} ${t("sessionActivity.entityHealed")} ${event.delta ?? 0} ${hpUnit}`
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
        {(event.entityCategory || (isGm && currentHp)) && (
          <p className="mt-0.5 text-xs text-slate-400">
            {event.entityCategory ? event.entityCategory : ""}
            {event.entityCategory && isGm && currentHp ? " · " : ""}
            {isGm && currentHp ? `${t("sessionActivity.currentHp")} ${currentHp}` : ""}
          </p>
        )}
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityRollResolvedRow = ({ event }: Props) => {
  const { t } = useLocale();
  if (event.type !== "roll_resolved") return null;
  const rollTypeLabel: Record<string, string> = {
    ability: t("rolls.abilityCheck"),
    save: t("rolls.savingThrow"),
    skill: t("rolls.skillCheck"),
    initiative: t("rolls.initiative"),
    attack: t("rolls.attackRoll"),
  };
  const label = rollTypeLabel[event.rollType] ?? event.rollType;
  const context = localizeRollContext(event.ability, event.skill, t);
  const advantageMode = localizeRollMode(event.advantageMode, t);
  const successIcon = event.success === true ? " ✓" : event.success === false ? " ✗" : "";
  const detailParts = [
    `${t("sessionActivity.rollDetailD20")} [${event.rolls.join(", ")}] → ${event.selectedRoll} ${formatSignedModifier(event.modifierUsed)}`,
  ];

  if (event.dc != null) {
    detailParts.push(`${t("sessionActivity.rollAgainstDc")} ${event.dc}`);
  }
  if (event.targetAc != null) {
    detailParts.push(`${t("sessionActivity.rollAgainstAc")} ${event.targetAc}`);
  }
  if (event.advantageMode !== "normal" && advantageMode) {
    detailParts.push(advantageMode);
  }
  if (event.isGmRoll) {
    detailParts.push(t("sessionActivity.gmBadge"));
  }

  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">🎯</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{event.actorName}</span>
          {" — "}
          {label}
          {context && (
            <span className="ml-1 text-slate-300">({context})</span>
          )}
          {" → "}
          <span className="font-bold text-limiar-400">{event.total}</span>
          {successIcon && (
            <span className={`ml-1 font-semibold ${event.success ? "text-green-400" : "text-red-400"}`}>
              {successIcon}
            </span>
          )}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">
          {detailParts.join(" · ")}
        </p>
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};

export const SessionActivityPurchaseRow = ({ event, actor }: { event: PurchaseActivityEvent; actor: string }) => {
  const { t } = useLocale();
  return (
    <div className="flex items-start gap-3 rounded-xl bg-slate-950/60 px-4 py-3">
      <span className="mt-0.5 text-base">{event.action === "sold" ? "💸" : "🛒"}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white">
          <span className="font-semibold">{actor}</span>
          {" "}
          {event.action === "sold"
            ? t("sessionActivity.soldItem")
            : t("sessionActivity.boughtItem")}
          {" "}
          <span className="font-semibold text-amber-300">{event.itemName}</span>
          {event.quantity > 1 && <span className="text-slate-400"> ×{event.quantity}</span>}
        </p>
        {event.amountLabel && (
          <p className="mt-0.5 text-xs text-slate-400">
            {t("sessionActivity.forPrice")} {event.amountLabel}
          </p>
        )}
      </div>
      <span className="shrink-0 text-xs font-mono text-slate-500">
        {formatSessionActivityOffset(event.sessionOffsetSeconds)}
      </span>
    </div>
  );
};
