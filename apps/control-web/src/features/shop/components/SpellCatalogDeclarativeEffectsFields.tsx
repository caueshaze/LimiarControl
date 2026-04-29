import type { Dispatch, SetStateAction } from "react";
import type {
  SpellDeclarativeConditionType,
  SpellDeclarativeEffect,
  SpellDeclarativeEffectTarget,
  SpellDeclarativeEffectType,
  SpellDeclarativeModifyStat,
  SpellDeclarativeRestrictActionKind,
} from "../../../entities/base-spell";
import type { SpellCatalogEditorState } from "../utils/spellCatalogForm";

type Props = {
  state: SpellCatalogEditorState;
  setState: Dispatch<SetStateAction<SpellCatalogEditorState>>;
};

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
      {title}
    </p>
    <div className="space-y-4">{children}</div>
  </div>
);

const EFFECT_TYPE_OPTIONS: SpellDeclarativeEffectType[] = [
  "apply_condition",
  "modify_stat",
  "advantage_on_checks",
  "disadvantage_on_checks",
  "restrict_action",
];
const TARGET_OPTIONS: SpellDeclarativeEffectTarget[] = ["selected_target", "caster"];
const DURATION_OPTIONS = ["manual", "rounds", "until_turn_start", "until_turn_end"] as const;
const ANCHOR_OPTIONS = ["target", "caster"] as const;
const CONDITION_OPTIONS: SpellDeclarativeConditionType[] = [
  "blinded",
  "charmed",
  "deafened",
  "frightened",
  "grappled",
  "hostile_to_caster",
  "incapacitated",
  "invisible",
  "paralyzed",
  "petrified",
  "poisoned",
  "prone",
  "restrained",
  "stunned",
  "unconscious",
];
const MODIFY_STAT_OPTIONS: SpellDeclarativeModifyStat[] = [
  "temp_ac_bonus",
  "attack_bonus",
  "damage_bonus",
];
const RESTRICT_ACTION_OPTIONS: SpellDeclarativeRestrictActionKind[] = [
  "actions",
  "bonus_actions",
  "reactions",
  "movement",
];
const ABILITY_OPTIONS = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
] as const;

const createDefaultEffect = (): SpellDeclarativeEffect => ({
  type: "apply_condition",
  target: "selected_target",
  duration: { type: "manual" },
  params: { condition: "charmed" },
  stacking: "replace",
});

const labelize = (value: string) => value.replace(/_/g, " ");

const retargetParams = (effectType: SpellDeclarativeEffectType): SpellDeclarativeEffect["params"] => {
  switch (effectType) {
    case "apply_condition":
      return { condition: "charmed" };
    case "modify_stat":
      return { stat: "temp_ac_bonus", value: 1 };
    case "advantage_on_checks":
    case "disadvantage_on_checks":
      return { ability: "charisma" };
    case "restrict_action":
      return { action: "actions" };
  }
};

const EffectEditor = ({
  title,
  effects,
  onChange,
}: {
  title: string;
  effects: SpellDeclarativeEffect[];
  onChange: (next: SpellDeclarativeEffect[]) => void;
}) => (
  <Section title={title}>
    <div className="space-y-3">
      {effects.map((effect, index) => (
        <div
          key={`${title}-${index}`}
          className="space-y-3 rounded-2xl border border-white/8 bg-slate-950/50 p-4"
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <select
              value={effect.type}
              onChange={(event) =>
                onChange(
                  effects.map((entry, entryIndex) =>
                    entryIndex === index
                      ? {
                          ...entry,
                          type: event.target.value as SpellDeclarativeEffectType,
                          params: retargetParams(event.target.value as SpellDeclarativeEffectType),
                        }
                      : entry,
                  ),
                )
              }
              className={fieldClassName}
            >
              {EFFECT_TYPE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {labelize(option)}
                </option>
              ))}
            </select>

            <select
              value={effect.target}
              onChange={(event) =>
                onChange(
                  effects.map((entry, entryIndex) =>
                    entryIndex === index
                      ? { ...entry, target: event.target.value as SpellDeclarativeEffectTarget }
                      : entry,
                  ),
                )
              }
              className={fieldClassName}
            >
              {TARGET_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {labelize(option)}
                </option>
              ))}
            </select>

            <select
              value={effect.duration?.type ?? "manual"}
              onChange={(event) =>
                onChange(
                  effects.map((entry, entryIndex) =>
                    entryIndex === index
                      ? {
                          ...entry,
                          duration: {
                            type: event.target.value as (typeof DURATION_OPTIONS)[number],
                            rounds: event.target.value === "rounds" ? 1 : null,
                            anchor: event.target.value === "manual" ? null : "target",
                          },
                        }
                      : entry,
                  ),
                )
              }
              className={fieldClassName}
            >
              {DURATION_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {labelize(option)}
                </option>
              ))}
            </select>

            <select
              value={effect.stacking ?? "replace"}
              onChange={(event) =>
                onChange(
                  effects.map((entry, entryIndex) =>
                    entryIndex === index
                      ? { ...entry, stacking: event.target.value as "stack" | "replace" }
                      : entry,
                  ),
                )
              }
              className={fieldClassName}
            >
              <option value="replace">replace</option>
              <option value="stack">stack</option>
            </select>
          </div>

          {effect.duration?.type === "rounds" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                type="number"
                min={1}
                value={effect.duration.rounds ?? 1}
                onChange={(event) =>
                  onChange(
                    effects.map((entry, entryIndex) =>
                      entryIndex === index
                        ? {
                            ...entry,
                            duration: {
                              ...(entry.duration ?? { type: "rounds", anchor: "target" }),
                              type: "rounds",
                              rounds: Math.max(1, Number(event.target.value) || 1),
                            },
                          }
                        : entry,
                    ),
                  )
                }
                className={fieldClassName}
                placeholder="Rounds"
              />
              <select
                value={effect.duration.anchor ?? "target"}
                onChange={(event) =>
                  onChange(
                    effects.map((entry, entryIndex) =>
                      entryIndex === index
                        ? {
                            ...entry,
                            duration: {
                              ...(entry.duration ?? { type: "rounds", rounds: 1 }),
                              anchor: event.target.value as "target" | "caster",
                            },
                          }
                        : entry,
                    ),
                  )
                }
                className={fieldClassName}
              >
                {ANCHOR_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {labelize(option)}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          {"condition" in effect.params ? (
            <select
              value={effect.params.condition}
              onChange={(event) =>
                onChange(
                  effects.map((entry, entryIndex) =>
                    entryIndex === index && "condition" in entry.params
                      ? {
                          ...entry,
                          params: {
                            condition: event.target.value as SpellDeclarativeConditionType,
                          },
                        }
                      : entry,
                  ),
                )
              }
              className={fieldClassName}
            >
              {CONDITION_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {labelize(option)}
                </option>
              ))}
            </select>
          ) : null}

          {"stat" in effect.params ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <select
                value={effect.params.stat}
                onChange={(event) =>
                  onChange(
                    effects.map((entry, entryIndex) =>
                      entryIndex === index && "stat" in entry.params
                        ? {
                            ...entry,
                            params: {
                              ...entry.params,
                              stat: event.target.value as SpellDeclarativeModifyStat,
                            },
                          }
                        : entry,
                    ),
                  )
                }
                className={fieldClassName}
              >
                {MODIFY_STAT_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {labelize(option)}
                  </option>
                ))}
              </select>
              <input
                type="number"
                value={effect.params.value}
                onChange={(event) =>
                  onChange(
                    effects.map((entry, entryIndex) =>
                      entryIndex === index && "stat" in entry.params
                        ? {
                            ...entry,
                            params: {
                              ...entry.params,
                              value: Number(event.target.value) || 0,
                            },
                          }
                        : entry,
                    ),
                  )
                }
                className={fieldClassName}
              />
            </div>
          ) : null}

          {"ability" in effect.params ? (
            <select
              value={effect.params.ability}
              onChange={(event) =>
                onChange(
                  effects.map((entry, entryIndex) =>
                    entryIndex === index && "ability" in entry.params
                      ? {
                          ...entry,
                          params: { ability: event.target.value as (typeof ABILITY_OPTIONS)[number] },
                        }
                      : entry,
                  ),
                )
              }
              className={fieldClassName}
            >
              {ABILITY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {labelize(option)}
                </option>
              ))}
            </select>
          ) : null}

          {"action" in effect.params ? (
            <select
              value={effect.params.action}
              onChange={(event) =>
                onChange(
                  effects.map((entry, entryIndex) =>
                    entryIndex === index && "action" in entry.params
                      ? {
                          ...entry,
                          params: {
                            action: event.target.value as SpellDeclarativeRestrictActionKind,
                          },
                        }
                      : entry,
                  ),
                )
              }
              className={fieldClassName}
            >
              {RESTRICT_ACTION_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {labelize(option)}
                </option>
              ))}
            </select>
          ) : null}

          <button
            type="button"
            onClick={() => onChange(effects.filter((_, entryIndex) => entryIndex !== index))}
            className="rounded-full border border-rose-400/20 px-3 py-2 text-xs uppercase tracking-[0.18em] text-rose-200"
          >
            Remover efeito
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...effects, createDefaultEffect()])}
        className="rounded-full border border-violet-300/20 px-3 py-2 text-xs uppercase tracking-[0.18em] text-violet-100"
      >
        Adicionar efeito
      </button>
    </div>
  </Section>
);

export const SpellCatalogDeclarativeEffectsFields = ({
  state,
  setState,
}: Props) => (
  <div className="space-y-5">
    <EffectEditor
      title="Efeitos declarativos"
      effects={state.effects}
      onChange={(next) => setState((current) => ({ ...current, effects: next }))}
    />
    <EffectEditor
      title="Efeitos ao terminar"
      effects={state.onEndEffects}
      onChange={(next) => setState((current) => ({ ...current, onEndEffects: next }))}
    />
  </div>
);
