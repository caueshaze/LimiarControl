import { useState } from "react";
import type {
  AbilityName,
  AdvantageMode,
  RollResult,
  RollType,
  SkillName,
} from "../../../entities/roll/rollResolution.types";
import { useLocale } from "../../../shared/hooks/useLocale";
import { useRollResolution } from "../hooks/useRollResolution";
import { RollResultCard } from "./RollResultCard";
import { formatCheckModifierSource } from "../../sessions/components/sessionActivityRowUtils";

export type AuthoritativeRollRequest = {
  rollType: RollType;
  ability?: AbilityName;
  skill?: SkillName;
  advantageMode: AdvantageMode;
  dc?: number | null;
  targetParticipantId?: string | null;
  reason?: string;
  issuedBy?: string;
  issuedByLabel?: string;
  debugModifiers?: Array<{
    source_label: string;
    modifier_type: "advantage" | "disadvantage";
    roll_type: "ability" | "skill";
    ability?: string | null;
    skill?: string | null;
    against?: "any" | "effect_target" | "selected_target" | null;
    selected_target_participant_id?: string | null;
    selected_target_display_name?: string | null;
    applied: boolean;
    skip_reason?: "target_mismatch" | "ability_mismatch" | "skill_mismatch" | "missing_target" | null;
  }> | null;
};

type Props = {
  request: AuthoritativeRollRequest;
  sessionId: string;
  actorKind: "player" | "session_entity";
  actorRefId: string;
  onClose: () => void;
  onResolved?: (result: RollResult) => void | Promise<void>;
  onSubmitRoll?: (payload: {
    rollSource: "system" | "manual";
    manualRoll?: number | null;
    manualRolls?: [number, number] | null;
  }) => Promise<RollResult | null>;
};

const D20_VALUES = Array.from({ length: 20 }, (_, i) => i + 1);

export const AuthoritativeRollDialog = ({
  request,
  sessionId,
  actorKind,
  actorRefId,
  onClose,
  onResolved,
  onSubmitRoll,
}: Props) => {
  const { t } = useLocale();
  const [mode, setMode] = useState<"choose" | "virtual" | "manual">("choose");
  const [manualD20, setManualD20] = useState<number | null>(null);
  const [manualD20Second, setManualD20Second] = useState<number | null>(null);
  const [overrideResult, setOverrideResult] = useState<RollResult | null>(null);
  const [overrideLoading, setOverrideLoading] = useState(false);

  const { result, loading, submitRoll } = useRollResolution(
    sessionId,
    actorKind,
    actorRefId,
  );

  const displayedResult = overrideResult ?? result;
  const isLoading = overrideLoading || loading;
  const needsTwoRolls = request.advantageMode !== "normal";
  const selectingSecond = needsTwoRolls && manualD20 !== null && manualD20Second === null;
  const modifierSources = displayedResult?.check_modifier_sources ?? request.debugModifiers ?? [];
  const manualAdvantageLabel =
    request.advantageMode === "advantage"
      ? "Vantagem (manual)"
      : request.advantageMode === "disadvantage"
        ? "Desvantagem (manual)"
        : null;

  const rollTypeLabels: Record<string, string> = {
    ability: t("rolls.abilityCheck" as Parameters<typeof t>[0]),
    save: t("rolls.savingThrow" as Parameters<typeof t>[0]),
    skill: t("rolls.skillCheck" as Parameters<typeof t>[0]),
    initiative: t("rolls.initiative" as Parameters<typeof t>[0]),
    attack: t("rolls.attackRoll" as Parameters<typeof t>[0]),
  };

  const handleVirtualRoll = async () => {
    setOverrideLoading(Boolean(onSubmitRoll));
    const result = onSubmitRoll
      ? await onSubmitRoll({ rollSource: "system" }).finally(() => setOverrideLoading(false))
      : await submitRoll({
          rollType: request.rollType,
          ability: request.ability,
          skill: request.skill,
          advantageMode: request.advantageMode,
          dc: request.dc,
          targetParticipantId: request.targetParticipantId,
          rollSource: "system",
        });
    if (result) {
      setOverrideResult(result);
      await onResolved?.(result);
    }
  };

  const handleManualSelect = async (value: number) => {
    if (needsTwoRolls) {
      if (manualD20 === null) {
        setManualD20(value);
        return;
      }
      setManualD20Second(value);
      setOverrideLoading(Boolean(onSubmitRoll));
      const result = onSubmitRoll
        ? await onSubmitRoll({ rollSource: "manual", manualRolls: [manualD20, value] }).finally(() => setOverrideLoading(false))
        : await submitRoll({
            rollType: request.rollType,
            ability: request.ability,
            skill: request.skill,
            advantageMode: request.advantageMode,
            dc: request.dc,
            targetParticipantId: request.targetParticipantId,
            rollSource: "manual",
            manualRolls: [manualD20, value],
          });
      if (result) {
        setOverrideResult(result);
        await onResolved?.(result);
      }
    } else {
      setManualD20(value);
      setOverrideLoading(Boolean(onSubmitRoll));
      const result = onSubmitRoll
        ? await onSubmitRoll({ rollSource: "manual", manualRoll: value }).finally(() => setOverrideLoading(false))
        : await submitRoll({
            rollType: request.rollType,
            ability: request.ability,
            skill: request.skill,
            advantageMode: request.advantageMode,
            dc: request.dc,
            targetParticipantId: request.targetParticipantId,
            rollSource: "manual",
            manualRoll: value,
          });
      if (result) {
        setOverrideResult(result);
        await onResolved?.(result);
      }
    }
  };

  const context = request.ability ?? request.skill ?? null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-md rounded-3xl border border-limiar-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-limiar-900/40">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-200">
          {rollTypeLabels[request.rollType] ?? request.rollType}
        </p>

        {request.reason && (
          <p className="mt-2 text-base font-semibold text-white">{request.reason}</p>
        )}

        <div className={`flex items-center gap-3 ${request.reason ? "mt-1" : "mt-3"}`}>
          {context && (
            <h2 className="text-2xl font-semibold text-limiar-300">
              {context}
            </h2>
          )}
          {manualAdvantageLabel && (
            <span
              className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
                request.advantageMode === "advantage"
                  ? "border border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                  : "border border-red-500/30 bg-red-500/15 text-red-400"
              }`}
            >
              {manualAdvantageLabel}
            </span>
          )}
        </div>

        {request.issuedBy && (
          <p className="mt-2 text-sm text-slate-400">
            {request.issuedByLabel ?? t("playerBoard.requestedBy" as Parameters<typeof t>[0])} {request.issuedBy}
          </p>
        )}

        {modifierSources.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3">
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-emerald-200">
              {displayedResult ? "Vantagem automática" : "Contexto do efeito"}
            </p>
            <div className="mt-2 space-y-1 text-xs text-slate-100">
              {modifierSources.map((entry, index) => (
                <p key={`${entry.source_label}:${entry.modifier_type}:${index}`}>
                  {formatCheckModifierSource(entry)}
                </p>
              ))}
            </div>
          </div>
        ) : null}

        {/* Result display */}
        {displayedResult && (
          <div className="mt-4">
            <RollResultCard result={displayedResult} hideDc />
            <button
              type="button"
              onClick={onClose}
              className="mt-4 w-full rounded-full bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
            >
              {t("common.close" as Parameters<typeof t>[0])}
            </button>
          </div>
        )}

        {/* Mode selection */}
        {!displayedResult && mode === "choose" && (
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setMode("virtual")}
              className="rounded-2xl bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-limiar-400"
            >
              🎲 {t("rolls.virtual" as Parameters<typeof t>[0])}
            </button>
            <button
              type="button"
              onClick={() => setMode("manual")}
              className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
            >
              ✍️ {t("rolls.manual" as Parameters<typeof t>[0])}
            </button>
          </div>
        )}

        {/* Virtual roll */}
        {!displayedResult && mode === "virtual" && (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={isLoading}
              onClick={() => { void handleVirtualRoll(); }}
              className="flex-1 rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {isLoading
                ? "..."
                : t("playerBoard.rollNow" as Parameters<typeof t>[0])}
            </button>
            <button
              type="button"
              onClick={() => setMode("choose")}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              ←
            </button>
          </div>
        )}

        {/* Manual roll — d20 grid */}
        {!displayedResult && mode === "manual" && (
          <div className="mt-5 space-y-3">
            <p className="text-xs text-slate-400">
              {selectingSecond
                ? `d20 #1: ${manualD20} — ${t("rolls.selectSecondD20" as Parameters<typeof t>[0])}`
                : needsTwoRolls
                  ? t("rolls.selectFirstD20" as Parameters<typeof t>[0])
                  : t("rolls.selectD20" as Parameters<typeof t>[0])}
            </p>

            <div className="grid grid-cols-5 gap-2">
              {D20_VALUES.map((n) => (
                <button
                  key={n}
                  type="button"
                  disabled={isLoading}
                  onClick={() => { void handleManualSelect(n); }}
                  className={`rounded-xl border px-2 py-3 text-center text-lg font-bold transition-colors ${
                    (n === manualD20 && !selectingSecond)
                      ? "border-limiar-400 bg-limiar-500/30 text-limiar-300"
                      : "border-slate-700 bg-slate-900 text-white hover:border-limiar-500/50 hover:bg-slate-800"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setMode("choose");
                  setManualD20(null);
                  setManualD20Second(null);
                }}
                className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
              >
                ←
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
