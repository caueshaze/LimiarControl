import type { RollResult } from "../../../entities/roll/rollResolution.types";
import { useLocale } from "../../../shared/hooks/useLocale";

const ROLL_TYPE_LABELS: Record<string, string> = {
  ability: "rolls.abilityCheck",
  save: "rolls.savingThrow",
  skill: "rolls.skillCheck",
  initiative: "rolls.initiative",
  attack: "rolls.attackRoll",
};

export const RollResultCard = ({ result }: { result: RollResult }) => {
  const { t } = useLocale();

  const label = t((ROLL_TYPE_LABELS[result.roll_type] ?? result.roll_type) as Parameters<typeof t>[0]);
  const context = result.ability ?? result.skill ?? null;
  const successIcon = result.success === true ? " ✓" : result.success === false ? " ✗" : "";
  const rollBreakdown =
    result.advantage_mode === "normal"
      ? `d20: ${result.selected_roll} + ${result.modifier_used}`
      : `d20: [${result.rolls.join(", ")}] → ${result.selected_roll} + ${result.modifier_used}`;

  return (
    <div className="rounded-2xl border border-limiar-400/20 bg-slate-900/80 p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-xs uppercase tracking-widest text-limiar-300">
          {label}
          {context && <span className="ml-1 normal-case text-slate-400">({context})</span>}
        </p>
        {result.advantage_mode !== "normal" && (
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
              result.advantage_mode === "advantage"
                ? "border border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                : "border border-red-500/30 bg-red-500/15 text-red-400"
            }`}
          >
            {result.advantage_mode}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-end gap-4">
        <span className="text-4xl font-bold text-white">{result.total}</span>
        {successIcon && (
          <span
            className={`mb-1 text-lg font-bold ${result.success ? "text-green-400" : "text-red-400"}`}
          >
            {successIcon}
          </span>
        )}
      </div>

      <p className="mt-2 text-xs text-slate-500">
        {rollBreakdown}
        {result.dc != null && ` vs DC ${result.dc}`}
        {result.target_ac != null && ` vs AC ${result.target_ac}`}
      </p>

      {result.is_gm_roll && (
        <p className="mt-1 text-[10px] uppercase tracking-widest text-slate-600">GM Roll</p>
      )}
    </div>
  );
};
