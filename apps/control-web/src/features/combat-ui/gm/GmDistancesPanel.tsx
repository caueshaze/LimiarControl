import { useEffect, useState } from "react";
import type {
  CombatParticipant,
  CombatState,
  CombatUpdateDistancesRequest,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";

type Props = {
  highlightPair?: { fromRefId: string; toRefId: string } | null;
  participants: CombatParticipant[];
  localDistances: Record<string, Record<string, number>>;
  sessionId: string;
  onDistancesUpdated: (updatedState: CombatState) => void;
};

type PresetKey = "engaged" | "reach" | "near" | "far" | "veryFar" | "custom";

const PRESETS: { key: PresetKey; label: string; meters: string; value: number | null }[] = [
  { key: "engaged", label: "Engajado", meters: "1,5m", value: 1.5 },
  { key: "reach",   label: "Alcance",  meters: "3m",   value: 3 },
  { key: "near",    label: "Perto",    meters: "9m",   value: 9 },
  { key: "far",     label: "Longe",    meters: "18m",  value: 18 },
  { key: "veryFar", label: "M. Longe", meters: "36m",  value: 36 },
  { key: "custom",  label: "Personalizado", meters: "",  value: null },
];

export function getDistanceBetween(
  localDistances: Record<string, Record<string, number>>,
  refA: string,
  refB: string,
): number | null {
  return localDistances[refA]?.[refB] ?? localDistances[refB]?.[refA] ?? null;
}

function formatMeters(meters: number): string {
  return meters % 1 === 0 ? `${meters}m` : `${meters.toFixed(1).replace(".", ",")}m`;
}

export const GmDistancesPanel = ({
  highlightPair,
  participants,
  localDistances,
  sessionId,
  onDistancesUpdated,
}: Props) => {
  const activeParticipants = participants.filter(
    (p) => p.status !== "dead" && p.status !== "defeated",
  );

  const [fromRefId, setFromRefId] = useState(activeParticipants[0]?.ref_id ?? "");
  const [toRefId, setToRefId] = useState(activeParticipants[1]?.ref_id ?? "");

  useEffect(() => {
    if (!highlightPair) return;
    if (highlightPair.fromRefId) setFromRefId(highlightPair.fromRefId);
    if (highlightPair.toRefId) setToRefId(highlightPair.toRefId);
  }, [highlightPair]);
  const [selectedPreset, setSelectedPreset] = useState<PresetKey>("engaged");
  const [customValue, setCustomValue] = useState("5");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "err"; message: string } | null>(null);

  const pairs: { a: CombatParticipant; b: CombatParticipant; distance: number | null }[] = [];
  for (let i = 0; i < activeParticipants.length; i++) {
    for (let j = i + 1; j < activeParticipants.length; j++) {
      const a = activeParticipants[i]!;
      const b = activeParticipants[j]!;
      pairs.push({ a, b, distance: getDistanceBetween(localDistances, a.ref_id, b.ref_id) });
    }
  }

  const missingCount = pairs.filter((p) => p.distance === null).length;

  const fromOptions = activeParticipants.filter((p) => p.ref_id !== toRefId);
  const toOptions = activeParticipants.filter((p) => p.ref_id !== fromRefId);

  const handleFromChange = (newFromRefId: string) => {
    setFromRefId(newFromRefId);
    if (toRefId === newFromRefId) {
      const next = activeParticipants.find((p) => p.ref_id !== newFromRefId);
      setToRefId(next?.ref_id ?? "");
    }
  };

  const handleToChange = (newToRefId: string) => {
    setToRefId(newToRefId);
    if (fromRefId === newToRefId) {
      const next = activeParticipants.find((p) => p.ref_id !== newToRefId);
      setFromRefId(next?.ref_id ?? "");
    }
  };

  const handleUpdate = async () => {
    if (!fromRefId || !toRefId || fromRefId === toRefId) return;

    const preset = PRESETS.find((p) => p.key === selectedPreset);
    const distanceMeters =
      preset?.value !== null && preset?.value !== undefined
        ? preset.value
        : parseFloat(customValue.replace(",", "."));

    if (isNaN(distanceMeters) || distanceMeters < 0) {
      setFeedback({ kind: "err", message: "Valor inválido." });
      return;
    }

    const payload: CombatUpdateDistancesRequest = {
      distances: [{ from_ref_id: fromRefId, to_ref_id: toRefId, distance_meters: distanceMeters }],
    };

    setSubmitting(true);
    setFeedback(null);
    try {
      const updatedState = await combatRepo.updateDistances(sessionId, payload);
      setFeedback({ kind: "ok", message: "Distância atualizada." });
      onDistancesUpdated(updatedState);
    } catch {
      setFeedback({ kind: "err", message: "Falha ao atualizar distância." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="rounded-4xl border border-slate-700/50 bg-slate-900/60 p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
        Teatro da mente
      </p>
      <h3 className="mt-1 text-base font-bold text-slate-100">Distâncias de combate</h3>
      <p className="mt-1 text-xs text-slate-400">
        Defina a distância entre participantes para validação de alcance em combate sem mapa.
      </p>

      {/* Pair matrix */}
      {pairs.length > 0 ? (
        <div className="mt-4 space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Distâncias configuradas
            {missingCount > 0 ? (
              <span className="ml-2 text-rose-400">{missingCount} faltando</span>
            ) : null}
          </p>
          <div className="grid gap-1">
            {pairs.map(({ a, b, distance }) => (
              <div
                key={`${a.ref_id}-${b.ref_id}`}
                className="flex items-center justify-between rounded-xl bg-slate-950/40 px-3 py-2"
              >
                <span className="text-xs text-slate-300">
                  <span className="font-medium">{a.display_name}</span>
                  <span className="mx-1.5 text-slate-600">↔</span>
                  <span className="font-medium">{b.display_name}</span>
                </span>
                {distance !== null ? (
                  <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-semibold text-emerald-300">
                    {formatMeters(distance)}
                  </span>
                ) : (
                  <span className="rounded-full bg-rose-500/15 px-2 py-0.5 text-xs font-semibold text-rose-400">
                    —
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-4 text-xs text-slate-500">Nenhuma distância configurada ainda.</p>
      )}

      {/* Edit form */}
      {activeParticipants.length >= 2 ? (
        <div className="mt-5 space-y-3 border-t border-slate-700/40 pt-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Atualizar distância
          </p>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                De
              </label>
              <select
                value={fromRefId}
                onChange={(e) => handleFromChange(e.target.value)}
                className="w-full rounded-xl bg-slate-800 px-3 py-2 text-xs text-slate-200 outline-none ring-1 ring-slate-700 focus:ring-slate-500"
              >
                {fromOptions.map((p) => (
                  <option key={p.ref_id} value={p.ref_id}>
                    {p.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Para
              </label>
              <select
                value={toRefId}
                onChange={(e) => handleToChange(e.target.value)}
                className="w-full rounded-xl bg-slate-800 px-3 py-2 text-xs text-slate-200 outline-none ring-1 ring-slate-700 focus:ring-slate-500"
              >
                {toOptions.map((p) => (
                  <option key={p.ref_id} value={p.ref_id}>
                    {p.display_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Distância
            </label>
            <div className="flex flex-wrap gap-1.5">
              {PRESETS.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  onClick={() => setSelectedPreset(preset.key)}
                  className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                    selectedPreset === preset.key
                      ? "border-violet-500/60 bg-violet-500/20 text-violet-200"
                      : "border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600 hover:text-slate-300"
                  }`}
                >
                  {preset.label}
                  {preset.meters ? (
                    <span className="ml-1 opacity-60">{preset.meters}</span>
                  ) : null}
                </button>
              ))}
            </div>
          </div>

          {selectedPreset === "custom" ? (
            <div className="space-y-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Personalizado (m)
              </label>
              <input
                type="number"
                min="0"
                step="0.5"
                value={customValue}
                onChange={(e) => setCustomValue(e.target.value)}
                className="w-full rounded-xl bg-slate-800 px-3 py-2 text-xs text-slate-200 outline-none ring-1 ring-slate-700 focus:ring-slate-500"
              />
            </div>
          ) : null}

          {feedback ? (
            <p
              className={`text-xs font-medium ${feedback.kind === "ok" ? "text-emerald-400" : "text-rose-400"}`}
            >
              {feedback.message}
            </p>
          ) : null}

          <button
            type="button"
            disabled={submitting || !fromRefId || !toRefId}
            onClick={() => void handleUpdate()}
            className="w-full rounded-2xl bg-violet-600 px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {submitting ? "Atualizando..." : "Atualizar distância"}
          </button>
        </div>
      ) : null}
    </section>
  );
};
