import type { CombatParticipant } from "../../../shared/api/combatRepo";
import type { CombatSpellOption } from "./types";

export type EffectInstanceTargetInput = {
  instance_index: number;
  target_ref_id: string;
};

export type InstanceTargetSelectorProps = {
  instanceCount: number;
  instanceDice?: string | null;
  participants: CombatParticipant[];
  spellCanonicalKey?: string | null;
  disabled?: boolean;
  value: EffectInstanceTargetInput[];
  onChange: (value: EffectInstanceTargetInput[]) => void;
};

type ResolvedEffectInstanceContext = {
  instanceCount: number;
  instanceDice: string | null;
};

export function getInstanceLabel(spellCanonicalKey: string | null | undefined, index: number): string {
  switch (spellCanonicalKey) {
    case "magic_missile":
      return `Míssil ${index}`;
    case "eldritch_blast":
      return `Feixe ${index}`;
    default:
      return `Instância ${index}`;
  }
}

export const normalizeEffectInstanceTargets = (
  value: EffectInstanceTargetInput[],
  instanceCount: number,
): EffectInstanceTargetInput[] =>
  Array.from({ length: instanceCount }, (_, offset) => offset + 1)
    .map((instanceIndex) => {
      const entry = value.find((candidate) => candidate.instance_index === instanceIndex);
      const targetRefId = entry?.target_ref_id?.trim() ?? "";
      return targetRefId
        ? {
            instance_index: instanceIndex,
            target_ref_id: targetRefId,
          }
        : null;
    })
    .filter((entry): entry is EffectInstanceTargetInput => entry !== null);

export const reconcileEffectInstanceTargets = (
  value: EffectInstanceTargetInput[],
  instanceCount: number,
  fallbackTargetRefId?: string | null,
): EffectInstanceTargetInput[] => {
  const normalizedCurrent = normalizeEffectInstanceTargets(value, instanceCount);

  return Array.from({ length: instanceCount }, (_, offset) => {
    const instanceIndex = offset + 1;
    const existing = normalizedCurrent.find((entry) => entry.instance_index === instanceIndex);
    if (existing) {
      return existing;
    }
    const targetRefId = fallbackTargetRefId?.trim() ?? "";
    return targetRefId
      ? {
          instance_index: instanceIndex,
          target_ref_id: targetRefId,
        }
      : null;
  }).filter((entry): entry is EffectInstanceTargetInput => entry !== null);
};

export const hasCompleteEffectInstanceTargets = (
  value: EffectInstanceTargetInput[],
  instanceCount: number,
): boolean => normalizeEffectInstanceTargets(value, instanceCount).length === instanceCount;

/**
 * Frontend-only pre-cast estimate for instance-target UI.
 * If the backend starts exposing resolved pre-cast instance metadata here,
 * prefer consuming that instead of recomputing scaling rules in the client.
 */
export const resolveEffectInstanceContext = (
  spell: Pick<CombatSpellOption, "cantripScaling" | "characterLevel" | "level" | "upcast">,
  selectedSlotLevel: number | null,
): ResolvedEffectInstanceContext => {
  const cantripScaling = spell.cantripScaling;
  if (spell.level === 0 && cantripScaling?.scalingEffectType === "effect_instances") {
    const thresholds = [...cantripScaling.thresholds].sort(
      (left, right) => left.characterLevel - right.characterLevel,
    );
    const characterLevel = spell.characterLevel ?? 1;
    const activeThreshold = thresholds.reduce<(typeof thresholds)[number] | null>((best, threshold) => {
      if (threshold.characterLevel > characterLevel) {
        return best;
      }
      return threshold;
    }, null);
    if (activeThreshold && "instances" in activeThreshold) {
      return {
        instanceCount: activeThreshold.instances,
        instanceDice: activeThreshold.instanceDamage?.dice ?? null,
      };
    }
  }

  if (spell.upcast?.mode === "additional_effect_instances") {
    const baseCount = spell.upcast.baseEffectInstances ?? 1;
    const perLevel = spell.upcast.perLevel ?? 0;
    const slotLevel = selectedSlotLevel ?? spell.level;
    const addedInstances = Math.max(0, slotLevel - spell.level) * perLevel;
    return {
      instanceCount: baseCount + addedInstances,
      instanceDice: spell.upcast.dice ?? null,
    };
  }

  return {
    instanceCount: 1,
    instanceDice: null,
  };
};

const buildParticipantGroups = (participants: CombatParticipant[]) => {
  const living = participants.filter(
    (participant) => participant.status !== "dead" && participant.status !== "defeated",
  );
  const defeated = participants.filter(
    (participant) => participant.status === "dead" || participant.status === "defeated",
  );
  return { defeated, living };
};

export const InstanceTargetSelector = ({
  instanceCount,
  instanceDice = null,
  participants,
  spellCanonicalKey,
  disabled = false,
  value,
  onChange,
}: InstanceTargetSelectorProps) => {
  const normalizedValue = normalizeEffectInstanceTargets(value, instanceCount);
  const valueByIndex = new Map(normalizedValue.map((entry) => [entry.instance_index, entry.target_ref_id]));
  const { defeated, living } = buildParticipantGroups(participants);

  return (
    <div className="mt-5 space-y-3 rounded-2xl border border-white/10 bg-slate-950/50 p-4">
      <div className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
          Alvos por instância
        </p>
        <p className="text-xs text-slate-400">Escolha um alvo para cada instância da magia.</p>
      </div>

      <div className="space-y-3">
        {Array.from({ length: instanceCount }, (_, offset) => {
          const instanceIndex = offset + 1;
          const label = getInstanceLabel(spellCanonicalKey, instanceIndex);
          return (
            <label
              key={instanceIndex}
              className="grid gap-2 rounded-2xl border border-white/5 bg-slate-900/50 p-3 md:grid-cols-[minmax(0,1fr)_140px_minmax(0,1.4fr)] md:items-center"
            >
              <span className="text-sm font-semibold text-white">{label}</span>
              <span className="text-xs text-slate-400">{instanceDice ? instanceDice : "Sem dado por instância"}</span>
              <select
                aria-label={label}
                disabled={disabled}
                value={valueByIndex.get(instanceIndex) ?? ""}
                onChange={(event) => {
                  const next = normalizeEffectInstanceTargets(
                    [
                      ...normalizedValue.filter((entry) => entry.instance_index !== instanceIndex),
                      {
                        instance_index: instanceIndex,
                        target_ref_id: event.target.value,
                      },
                    ],
                    instanceCount,
                  );
                  onChange(next);
                }}
                className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition focus:border-fuchsia-400 disabled:opacity-50"
              >
                <option value="">Escolha um alvo</option>
                {living.length > 0 ? (
                  <optgroup label="Vivos / em combate">
                    {living.map((participant) => (
                      <option key={participant.id} value={participant.ref_id}>
                        {participant.display_name} [{participant.status}]
                      </option>
                    ))}
                  </optgroup>
                ) : null}
                {defeated.length > 0 ? (
                  <optgroup label="Mortos / derrotados">
                    {defeated.map((participant) => (
                      <option key={participant.id} value={participant.ref_id} disabled>
                        {participant.display_name} [{participant.status}]
                      </option>
                    ))}
                  </optgroup>
                ) : null}
              </select>
            </label>
          );
        })}
      </div>
    </div>
  );
};
