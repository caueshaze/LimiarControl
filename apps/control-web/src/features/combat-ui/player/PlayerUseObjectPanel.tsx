import { useMemo } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";
import type {
  ConsumableOption,
  SelectedConsumable,
  UseObjectTargetOption,
} from "./playerCombatShell.types";

type Props = {
  consumableItemId: string;
  consumableOptions: ConsumableOption[];
  handleUseObject: () => Promise<void>;
  myParticipantId?: string | null;
  selectedConsumable: SelectedConsumable | null;
  setConsumableItemId: (id: string) => void;
  setUseObjectManualRolls: (updater: (current: number[]) => number[]) => void;
  setUseObjectNote: (note: string) => void;
  setUseObjectRollMode: (mode: "system" | "manual") => void;
  setUseObjectTargetParticipantId: (id: string) => void;
  useObjectActionDisabled: boolean;
  useObjectManualRolls: number[];
  useObjectNote: string;
  useObjectRollMode: "system" | "manual";
  useObjectTargetOptions: UseObjectTargetOption[];
  useObjectTargetParticipantId: string;
};

export const PlayerUseObjectPanel = ({
  consumableItemId,
  consumableOptions,
  handleUseObject,
  myParticipantId,
  selectedConsumable,
  setConsumableItemId,
  setUseObjectManualRolls,
  setUseObjectNote,
  setUseObjectRollMode,
  setUseObjectTargetParticipantId,
  useObjectActionDisabled,
  useObjectManualRolls,
  useObjectNote,
  useObjectRollMode,
  useObjectTargetOptions,
  useObjectTargetParticipantId,
}: Props) => {
  const { t } = useLocale();

  const selectedConsumableIsHealing = Boolean(selectedConsumable?.isHealingConsumable);
  const useObjectCanManualRoll = Boolean(
    selectedConsumableIsHealing &&
      selectedConsumable &&
      selectedConsumable.manualRollCount > 0 &&
      selectedConsumable.manualRollSides > 0,
  );
  const useObjectManualRollValues = useMemo(
    () =>
      Array.from({ length: selectedConsumable?.manualRollSides ?? 0 }, (_, index) => index + 1),
    [selectedConsumable?.manualRollSides],
  );
  const selectedUseObjectTarget = useMemo(
    () =>
      useObjectTargetOptions.find((participant) => participant.id === useObjectTargetParticipantId) ?? null,
    [useObjectTargetOptions, useObjectTargetParticipantId],
  );

  return (
    <article className="rounded-3xl border border-emerald-500/15 bg-emerald-500/8 p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">{t("combatUi.useObject")}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {t("combatUi.useObjectHint")}
          </p>
        </div>
        <button
          type="button"
          disabled={useObjectActionDisabled}
          onClick={() => {
            void handleUseObject();
          }}
          className="rounded-full bg-emerald-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-950 transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {t("combatUi.useObject")}
        </button>
      </div>
      <label className="mt-4 block space-y-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
          {t("combatUi.usableConsumable")}
        </span>
        <select
          value={consumableItemId}
          onChange={(event) => setConsumableItemId(event.target.value)}
          className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-emerald-400"
        >
          <option value="">{t("combatUi.useObjectManualOption")}</option>
          {consumableOptions.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      {consumableOptions.length === 0 ? (
        <p className="mt-3 text-xs text-slate-400">{t("combatUi.noConsumables")}</p>
      ) : null}
      {selectedConsumableIsHealing && selectedConsumable ? (
        <>
          <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
            <label className="space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                {t("playerBoard.consumableTarget")}
              </span>
              <select
                value={useObjectTargetParticipantId}
                onChange={(event) => setUseObjectTargetParticipantId(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-emerald-400"
              >
                {useObjectTargetOptions.length === 0 ? (
                  <option value="">{t("playerBoard.consumableNoHealingTargets")}</option>
                ) : null}
                {useObjectTargetOptions.map((participant) => (
                  <option key={participant.id} value={participant.id}>
                    {participant.display_name}
                    {participant.id === myParticipantId ? ` · ${t("combatUi.you")}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <div className="rounded-3xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-100/80">
                {t("inventory.healing")}
              </p>
              <p className="mt-2 text-sm font-semibold text-white">
                {selectedConsumable.healingLabel ?? "-"}
              </p>
              {selectedUseObjectTarget ? (
                <p className="mt-2 text-xs text-emerald-50/80">
                  {selectedUseObjectTarget.display_name}
                </p>
              ) : null}
            </div>
          </div>

          <div className="mt-4 space-y-3 rounded-3xl border border-white/8 bg-slate-950/35 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
              {t("playerBoard.consumableRollMode")}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => {
                  setUseObjectRollMode("system");
                  setUseObjectManualRolls(() => []);
                }}
                className={`rounded-2xl border px-4 py-3 text-sm font-semibold transition-colors ${
                  useObjectRollMode === "system"
                    ? "border-emerald-400/30 bg-emerald-500/12 text-emerald-100"
                    : "border-white/10 bg-white/4 text-slate-200 hover:bg-slate-900/70"
                }`}
              >
                {t("playerBoard.consumableRollAuto")}
              </button>
              <button
                type="button"
                disabled={!useObjectCanManualRoll}
                onClick={() => {
                  setUseObjectRollMode("manual");
                  setUseObjectManualRolls(() => []);
                }}
                className={`rounded-2xl border px-4 py-3 text-sm font-semibold transition-colors ${
                  useObjectRollMode === "manual"
                    ? "border-amber-400/30 bg-amber-500/12 text-amber-100"
                    : "border-white/10 bg-white/4 text-slate-200 hover:bg-slate-900/70"
                } disabled:cursor-not-allowed disabled:opacity-40`}
              >
                {t("playerBoard.consumableRollManual")}
              </button>
            </div>

            {useObjectRollMode === "manual" && useObjectCanManualRoll ? (
              <div className="space-y-3 rounded-2xl border border-white/8 bg-white/4 p-4">
                <p className="text-xs text-slate-300">
                  {t("playerBoard.consumableRollSelect")} (
                  {useObjectManualRolls.length}/{selectedConsumable.manualRollCount})
                </p>
                {useObjectManualRolls.length > 0 ? (
                  <p className="rounded-2xl border border-white/8 bg-slate-950/70 px-3 py-2 text-xs text-slate-200">
                    {useObjectManualRolls.join(", ")}
                  </p>
                ) : null}
                <div className="grid grid-cols-5 gap-2">
                  {useObjectManualRollValues.map((value) => (
                    <button
                      key={value}
                      type="button"
                      disabled={
                        useObjectManualRolls.length >= selectedConsumable.manualRollCount
                      }
                      onClick={() =>
                        setUseObjectManualRolls((current) => [...current, value])
                      }
                      className="rounded-2xl border border-white/10 bg-slate-950/70 px-2 py-3 text-sm font-semibold text-white transition hover:border-amber-400/40 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {value}
                    </button>
                  ))}
                </div>
                <div className="flex justify-end">
                  <button
                    type="button"
                    disabled={useObjectManualRolls.length === 0}
                    onClick={() => setUseObjectManualRolls(() => [])}
                    className="rounded-full border border-white/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-300 transition hover:border-white/20 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {t("playerBoard.consumableRollClear")}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </>
      ) : (
        <label className="mt-4 block space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
            {t("combatUi.useObjectManualNote")}
          </span>
          <input
            type="text"
            value={useObjectNote}
            onChange={(event) => setUseObjectNote(event.target.value)}
            placeholder={t("combatUi.useObjectPlaceholder")}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-emerald-400"
          />
        </label>
      )}
    </article>
  );
};
