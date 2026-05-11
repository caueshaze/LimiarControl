import { useLocale } from "../../../shared/hooks/useLocale";
import { formatEffectiveCreatureSize, groupActiveEffectsForDisplay } from "../../active-effects";
import { getCombatEffectLabel, getCombatStatusLabel, getTurnResourceLabel } from "../combatUi.helpers";
import type { CombatParticipantView } from "../types";
import { ActiveEffectDebugPanel } from "./ActiveEffectDebugPanel";

type Props = {
  onRemoveEffect?: (participantId: string, effectId: string) => void | Promise<void>;
  participants: CombatParticipantView[];
  subtitle?: string | null;
  title: string;
};

export const CombatParticipantRoster = ({
  onRemoveEffect,
  participants,
  subtitle = null,
  title,
}: Props) => {
  const { t } = useLocale();

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.94))] p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
          {t("combatUi.participantsEyebrow")}
        </p>
        <h3 className="mt-2 text-lg font-semibold text-white">{title}</h3>
        {subtitle ? <p className="mt-2 text-sm text-slate-400">{subtitle}</p> : null}
      </div>

      <div className="mt-4 space-y-2">
        {participants.map((participant, index) => {
          const effectiveSizeLabel = formatEffectiveCreatureSize(participant, "pt");
          const activeEffectGroups = groupActiveEffectsForDisplay(participant.activeEffects);
          return (
            <article
              key={participant.id}
              className={`rounded-3xl border px-4 py-3 transition-colors ${
                participant.isCurrentTurn
                  ? "border-amber-400/35 bg-amber-500/12"
                  : "border-white/6 bg-white/4"
              }`}
            >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-mono text-slate-500">{index + 1}.</span>
                  <h4 className="truncate text-sm font-semibold text-white">
                    {participant.display_name}
                    {participant.isSelf ? ` · ${t("combatUi.you")}` : ""}
                  </h4>
                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-300">
                    {getCombatStatusLabel(t, participant.status)}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                  <span>{participant.kind === "player" ? t("combatUi.kind.player") : t("combatUi.kind.entity")}</span>
                  {participant.initiative != null ? (
                    <span>
                      {t("combatUi.initiative")}: {participant.initiative}
                    </span>
                  ) : null}
                  {participant.currentHp != null ? (
                    <span>
                      {t("combatUi.hp")}: {participant.maxHp != null ? `${participant.currentHp}/${participant.maxHp}` : participant.currentHp}
                    </span>
                  ) : null}
                  {effectiveSizeLabel ? <span>{effectiveSizeLabel}</span> : null}
                </div>
              </div>

              {participant.turnResources ? (
                <div className="flex flex-col items-end gap-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">
                  <span>{getTurnResourceLabel(t, "action", participant.turnResources.action_used)}</span>
                  <span>{getTurnResourceLabel(t, "bonus", participant.turnResources.bonus_action_used)}</span>
                  <span>{getTurnResourceLabel(t, "reaction", participant.turnResources.reaction_used)}</span>
                </div>
              ) : null}
            </div>

            {participant.activeEffects.length > 0 ? (
              <>
                <div className="mt-3 flex flex-wrap gap-2">
                  {activeEffectGroups.map((group, groupIndex) => (
                    <span
                      key={group.groupKey ?? String(groupIndex)}
                      className="inline-flex items-center gap-1 rounded-full border border-fuchsia-500/25 bg-fuchsia-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-fuchsia-100"
                    >
                      {group.title ?? getCombatEffectLabel(t, group.effects[0] as any)}
                      {onRemoveEffect ? (
                        (group.effects as typeof participant.activeEffects).map((effect) => (
                          <button
                            key={effect.id}
                            type="button"
                            onClick={() => {
                              void onRemoveEffect(participant.id, effect.id);
                            }}
                            className="text-fuchsia-200 transition-colors hover:text-white"
                            aria-label={t("combatUi.removeEffect")}
                          >
                            x
                          </button>
                        ))
                      ) : null}
                    </span>
                  ))}
                </div>
                <ActiveEffectDebugPanel
                  effects={participant.activeEffects}
                  targetDisplayName={participant.display_name}
                />
              </>
            ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
};
