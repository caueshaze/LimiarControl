import type { SpellVariant } from "../../../entities/base-spell";
import type { CombatParticipant } from "../../../shared/api/combatRepo";

export type TargetVariantAssignmentInput = {
  target_participant_id: string;
  variant_key: string;
};

type Props = {
  disabled?: boolean;
  maxTargets: number;
  participants: CombatParticipant[];
  value: TargetVariantAssignmentInput[];
  variants: SpellVariant[];
  onChange: (value: TargetVariantAssignmentInput[]) => void;
};

const normalizeAssignments = (
  value: TargetVariantAssignmentInput[],
  maxTargets: number,
): TargetVariantAssignmentInput[] =>
  value
    .map((entry) => ({
      target_participant_id: entry.target_participant_id?.trim() ?? "",
      variant_key: entry.variant_key?.trim() ?? "",
    }))
    .filter((entry) => entry.target_participant_id && entry.variant_key)
    .slice(0, maxTargets);

export const hasCompleteTargetVariantAssignments = (
  value: TargetVariantAssignmentInput[],
  maxTargets: number,
): boolean => {
  const normalized = normalizeAssignments(value, maxTargets);
  if (normalized.length < 2) {
    return false;
  }
  return new Set(normalized.map((entry) => entry.target_participant_id)).size === normalized.length;
};

export const VariantTargetAssignmentSelector = ({
  disabled = false,
  maxTargets,
  participants,
  value,
  variants,
  onChange,
}: Props) => {
  const normalized = normalizeAssignments(value, maxTargets);
  const rows = Array.from({ length: maxTargets }, (_, index) => normalized[index] ?? null);

  return (
    <div className="mt-5 space-y-3 rounded-2xl border border-white/10 bg-slate-950/50 p-4">
      <div className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
          Variantes por alvo
        </p>
        <p className="text-xs text-slate-400">
          Escolha até {maxTargets} alvos e defina uma variante para cada um.
        </p>
      </div>

      <div className="space-y-3">
        {rows.map((entry, index) => (
          <div
            key={index}
            className="grid gap-2 rounded-2xl border border-white/5 bg-slate-900/50 p-3 md:grid-cols-2"
          >
            <select
              aria-label={`Alvo ${index + 1}`}
              disabled={disabled}
              value={entry?.target_participant_id ?? ""}
              onChange={(event) => {
                const next = [...rows];
                next[index] = {
                  target_participant_id: event.target.value,
                  variant_key: entry?.variant_key ?? variants[0]?.key ?? "",
                };
                onChange(normalizeAssignments(next.filter(Boolean) as TargetVariantAssignmentInput[], maxTargets));
              }}
              className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition focus:border-fuchsia-400 disabled:opacity-50"
            >
              <option value="">Escolha um alvo</option>
              {participants.map((participant) => (
                <option key={participant.id} value={participant.id}>
                  {participant.display_name} [{participant.status}]
                </option>
              ))}
            </select>

            <select
              aria-label={`Variante ${index + 1}`}
              disabled={disabled || !entry?.target_participant_id}
              value={entry?.variant_key ?? ""}
              onChange={(event) => {
                const next = [...rows];
                next[index] = {
                  target_participant_id: entry?.target_participant_id ?? "",
                  variant_key: event.target.value,
                };
                onChange(normalizeAssignments(next.filter(Boolean) as TargetVariantAssignmentInput[], maxTargets));
              }}
              className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition focus:border-fuchsia-400 disabled:opacity-50"
            >
              <option value="">Escolha uma variante</option>
              {variants.map((variant) => (
                <option key={variant.key} value={variant.key}>
                  {variant.labelPt ?? variant.labelEn ?? variant.key}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
};
