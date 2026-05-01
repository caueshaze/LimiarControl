import { useState } from "react";
import {
  findManualNotesForTarget,
  formatManualNotesByTarget,
  originLabel,
  resolveTargetVariantLabel,
} from "../spellVariantUi";
import type { CombatParticipant } from "../../../shared/api/combatRepo";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  pendingSaves: Array<CombatParticipant & { pending_save: NonNullable<CombatParticipant["pending_save"]> }>;
  submitting: boolean;
  onResolveSave: (targetParticipantId: string, pendingSaveId: string, rollSource: "system" | "manual", manualRoll?: number) => void;
};

export const GmPendingSavesPanel = ({
  pendingSaves,
  submitting,
  onResolveSave,
}: Props) => {
  const { t } = useLocale();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [manualValue, setManualValue] = useState("");

  if (pendingSaves.length === 0) return null;

  return (
    <section className="rounded-4xl border border-fuchsia-500/25 bg-fuchsia-500/10 p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <h3 className="text-sm font-bold uppercase tracking-widest text-fuchsia-200">Testes de Resistencia Pendentes</h3>
      <div className="mt-4 space-y-3">
        {pendingSaves.map((p) => {
          const save = p.pending_save;
          const isExpanded = expandedId === p.id;
          const variantLabel = resolveTargetVariantLabel({
            targetVariantAssignments: save.target_variant_assignments,
            manualNotesByTarget: save.manual_notes_by_target,
            selectedVariantKey: save.selected_variant_key,
            selectedVariantLabel: save.selected_variant_label,
            targetParticipantId: p.id,
            targetRefId: p.ref_id,
          });
          const manualNotesEntry = findManualNotesForTarget(save.manual_notes_by_target, {
            targetParticipantId: p.id,
            targetRefId: p.ref_id,
          });
          const manualNoteLines = formatManualNotesByTarget(
            manualNotesEntry ? [manualNotesEntry] : null,
          );
          return (
            <div key={p.id} className="rounded-2xl bg-slate-950/40 p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <span className="text-sm font-semibold text-slate-200">{p.display_name}</span>
                  <p className="mt-1 text-xs text-slate-400">
                    {save.spell_name} — save de {save.save_ability} CD {save.save_dc}
                    {save.attacker_display_name ? ` (lancado por ${save.attacker_display_name})` : ""}
                  </p>
                  {variantLabel ? (
                    <p className="mt-1 text-xs text-fuchsia-200">Variante: {variantLabel}</p>
                  ) : null}
                  {originLabel(save.context_origin) ? (
                    <p className="mt-1 text-xs text-sky-200">Origem: {originLabel(save.context_origin)}</p>
                  ) : null}
                  {save.concentration_group ? (
                    <p className="mt-1 text-xs text-sky-200">Concentração: {save.concentration_group}</p>
                  ) : null}
                  {manualNoteLines.length ? (
                    <div className="mt-2 space-y-1 text-xs text-amber-100">
                      {manualNoteLines.map((line, index) => (
                        <p key={`${p.id}:${index}`}>
                          {line.replace(`${p.display_name}: `, "")}
                        </p>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
              {isExpanded ? (
                <div className="space-y-3 border-t border-white/8 pt-3">
                  <div className="flex items-center gap-3">
                    <label className="text-xs text-slate-400">Valor manual:</label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={manualValue}
                      onChange={(e) => setManualValue(e.target.value)}
                      className="w-20 rounded-xl border border-white/10 bg-slate-950/70 px-3 py-1.5 text-sm text-white outline-none focus:border-fuchsia-400"
                      placeholder="1-20"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => {
                        const roll = parseInt(manualValue, 10);
                        if (roll >= 1 && roll <= 20) {
                          onResolveSave(p.id, save.id, "manual", roll);
                          setExpandedId(null);
                          setManualValue("");
                        }
                      }}
                      className="rounded-full bg-fuchsia-500/20 border border-fuchsia-500/30 px-3 py-1.5 text-xs font-semibold uppercase text-fuchsia-300 hover:bg-fuchsia-500/30 disabled:opacity-50"
                    >
                      Rolar Manual
                    </button>
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => {
                        setExpandedId(null);
                        setManualValue("");
                      }}
                      className="rounded-full bg-white/5 border border-white/10 px-3 py-1.5 text-xs font-semibold uppercase text-slate-300 hover:bg-white/10 disabled:opacity-50"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={() => onResolveSave(p.id, save.id, "system")}
                    className="rounded-full bg-emerald-500/20 border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold uppercase text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-50"
                  >
                    Rolar Auto
                  </button>
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={() => setExpandedId(p.id)}
                    className="rounded-full bg-white/5 border border-white/10 px-3 py-1.5 text-xs font-semibold uppercase text-slate-300 hover:bg-white/10 disabled:opacity-50"
                  >
                    Manual
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};
