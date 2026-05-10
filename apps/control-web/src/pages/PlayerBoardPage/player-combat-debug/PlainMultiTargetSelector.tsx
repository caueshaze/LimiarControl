import type { CombatParticipant } from "../../../shared/api/combatRepo";

type Props = {
  disabled?: boolean;
  maxTargets: number;
  participants: CombatParticipant[];
  value: string[];
  onChange: (value: string[]) => void;
};

/**
 * Target selector for plain multi-target automation spells (no variants).
 * Renders one dropdown per target slot up to maxTargets.
 * Each slot excludes targets already selected in other slots.
 */
export const PlainMultiTargetSelector = ({
  disabled = false,
  maxTargets,
  participants,
  value,
  onChange,
}: Props) => {
  const eligible = participants.filter(
    (p) => p.status !== "dead" && p.status !== "defeated",
  );

  const rows = Array.from({ length: maxTargets }, (_, i) => value[i] ?? "");

  const handleChange = (index: number, refId: string) => {
    const next = [...rows];
    next[index] = refId;
    onChange(next.filter(Boolean));
  };

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-slate-300">
        Selecione até {maxTargets} alvo{maxTargets !== 1 ? "s" : ""}
      </p>
      {rows.map((selectedRefId, index) => {
        const otherSelected = new Set(rows.filter((_, i) => i !== index));
        const options = eligible.filter(
          (p) => !otherSelected.has(p.ref_id) || p.ref_id === selectedRefId,
        );
        return (
          <select
            key={index}
            disabled={disabled}
            value={selectedRefId}
            onChange={(e) => handleChange(index, e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white focus:border-fuchsia-400 focus:outline-none"
          >
            <option value="">— Alvo {index + 1} —</option>
            {options.map((p) => (
              <option key={p.id} value={p.ref_id}>
                {p.display_name}
              </option>
            ))}
          </select>
        );
      })}
    </div>
  );
};
