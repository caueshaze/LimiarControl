import { useEffect } from "react";
import type { Item } from "../../../entities/item";
import type { SessionHealingConsumableTarget } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getDamageRollCount, getDamageRollSides, parseDiceExpression } from "../../../shared/utils/diceExpression";

export const HealingConsumableDialog = ({
  activeSessionId,
  combatActive,
  item,
  loadingTargets,
  manualRolls,
  rollMode,
  selectedTargetUserId,
  submitting,
  targets,
  onClose,
  onManualRollSelect,
  onManualRollsClear,
  onRollModeChange,
  onSubmit,
  onTargetChange,
}: {
  activeSessionId: string | null;
  combatActive: boolean;
  item: Item;
  loadingTargets: boolean;
  manualRolls: number[];
  rollMode: "system" | "manual";
  selectedTargetUserId: string;
  submitting: boolean;
  targets: SessionHealingConsumableTarget[];
  onClose: () => void;
  onManualRollSelect: (value: number) => void;
  onManualRollsClear: () => void;
  onRollModeChange: (value: "system" | "manual") => void;
  onSubmit: (payload: { rollSource: "system" | "manual"; manualRolls?: number[] | null }) => Promise<void>;
  onTargetChange: (value: string) => void;
}) => {
  const { t } = useLocale();
  const parsedDice = parseDiceExpression(item.healDice);
  const manualRollCount = getDamageRollCount(item.healDice);
  const manualRollSides = getDamageRollSides(item.healDice);
  const manualRollValues = Array.from({ length: manualRollSides }, (_, index) => index + 1);
  const canManualRoll = Boolean(parsedDice && manualRollCount > 0 && manualRollSides > 0);
  const canSubmit = Boolean(activeSessionId && selectedTargetUserId && !combatActive && !loadingTargets);

  useEffect(() => {
    if (!canManualRoll && rollMode === "manual") {
      onRollModeChange("system");
    }
  }, [canManualRoll, onRollModeChange, rollMode]);

  useEffect(() => {
    if (!canManualRoll && manualRolls.length > 0) {
      onManualRollsClear();
    }
  }, [canManualRoll, manualRolls.length, onManualRollsClear]);

  useEffect(() => {
    if (
      rollMode === "manual" &&
      canSubmit &&
      !submitting &&
      manualRollCount > 0 &&
      manualRolls.length >= manualRollCount
    ) {
      const nextRolls = manualRolls.slice(0, manualRollCount);
      onManualRollsClear();
      void onSubmit({
        rollSource: "manual",
        manualRolls: nextRolls,
      });
    }
  }, [
    canSubmit,
    manualRollCount,
    manualRolls,
    onManualRollsClear,
    onSubmit,
    rollMode,
    submitting,
  ]);

  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/75 p-4">
      <div className="w-full max-w-md rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(10,14,30,0.98),rgba(3,7,20,0.98))] p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-200/80">
              {t("playerBoard.useConsumableTitle")}
            </p>
            <h3 className="mt-2 text-xl font-semibold text-white">{item.name}</h3>
            <p className="mt-2 text-sm text-slate-300">
              {item.healDice
                ? `${item.healDice}${typeof item.healBonus === "number" && item.healBonus !== 0 ? ` + ${item.healBonus}` : ""}`
                : `${item.healBonus ?? 0}`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-white/10 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300 transition hover:border-white/20 hover:text-white"
          >
            {t("playerBoard.closeInventoryModal")}
          </button>
        </div>

        <div className="mt-5 space-y-4">
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("playerBoard.consumableTarget")}
            </span>
            <select
              value={selectedTargetUserId}
              onChange={(event) => onTargetChange(event.target.value)}
              disabled={loadingTargets || targets.length === 0}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-emerald-400/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
            >
              <option value="">
                {loadingTargets
                  ? t("inventory.loading")
                  : t("playerBoard.consumableNoHealingTargets")}
              </option>
              {targets.map((target) => (
                <option key={target.playerUserId} value={target.playerUserId}>
                  {target.displayName} · {target.currentHp}/{target.maxHp}
                  {target.isSelf ? ` · ${t("combatUi.you")}` : ""}
                </option>
              ))}
            </select>
          </label>

          <div className="space-y-2">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("playerBoard.consumableRollMode")}
            </span>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => onRollModeChange("system")}
                className={`rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
                  rollMode === "system"
                    ? "border-emerald-400/30 bg-emerald-500/12 text-emerald-100"
                    : "border-white/10 bg-white/4 text-slate-300 hover:border-white/20"
                }`}
              >
                {t("playerBoard.consumableRollAuto")}
              </button>
              <button
                type="button"
                disabled={!canManualRoll}
                onClick={() => onRollModeChange("manual")}
                className={`rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
                  rollMode === "manual"
                    ? "border-amber-400/30 bg-amber-500/12 text-amber-100"
                    : "border-white/10 bg-white/4 text-slate-300 hover:border-white/20"
                } disabled:cursor-not-allowed disabled:opacity-40`}
              >
                {t("playerBoard.consumableRollManual")}
              </button>
            </div>
          </div>

          {combatActive ? (
            <p className="text-sm text-rose-200">{t("playerBoard.consumableUnavailableInCombat")}</p>
          ) : null}

          {rollMode === "manual" && canManualRoll ? (
            <div className="space-y-3">
              <p className="text-sm text-slate-300">
                {t("playerBoard.consumableRollSelect")} ({manualRolls.length}/{manualRollCount})
              </p>
              {manualRolls.length > 0 ? (
                <div className="rounded-2xl border border-white/10 bg-slate-950/50 px-3 py-2 text-xs text-slate-300">
                  {manualRolls.join(", ")}
                </div>
              ) : null}
              <div className="grid grid-cols-4 gap-2">
                {manualRollValues.map((value) => (
                  <button
                    key={value}
                    type="button"
                    disabled={submitting || !canSubmit}
                    onClick={() => onManualRollSelect(value)}
                    className="rounded-xl border border-white/10 bg-white/4 px-3 py-3 text-sm font-semibold text-white transition hover:border-amber-400/40 hover:bg-amber-500/10 disabled:opacity-40"
                  >
                    {value}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={onManualRollsClear}
                className="rounded-full border border-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300 transition hover:border-white/20 hover:text-white"
              >
                {t("playerBoard.consumableRollClear")}
              </button>
            </div>
          ) : (
            <button
              type="button"
              disabled={!canSubmit || submitting}
              onClick={() => {
                void onSubmit({ rollSource: "system", manualRolls: null });
              }}
              className="w-full rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.18em] text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting ? t("inventory.usingConsumable") : t("inventory.useConsumable")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
