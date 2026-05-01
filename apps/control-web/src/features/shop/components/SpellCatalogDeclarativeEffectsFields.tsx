import type { Dispatch, SetStateAction } from "react";
import type {
  SpellDeclarativeConditionType,
  SpellDeclarativeEffect,
  SpellDeclarativeEffectTarget,
  SpellDeclarativeEffectType,
  SpellDeclarativeModifyStat,
  SpellDeclarativeRestrictActionKind,
} from "../../../entities/base-spell";
import { useLocale } from "../../../shared/hooks/useLocale";
import { localizeSpellAdminValue } from "../../../shared/i18n/domainLabels";
import type { SpellCatalogEditorState } from "../utils/spellCatalogForm";

type Props = {
  state: SpellCatalogEditorState;
  setState: Dispatch<SetStateAction<SpellCatalogEditorState>>;
};

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

const FieldLabel = ({ label, tooltip }: { label: string; tooltip: string }) => (
  <div className="flex items-center gap-1.5">
    <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
      {label}
    </span>
    <div className="group relative inline-block">
      <span className="cursor-help text-xs text-slate-500 transition hover:text-slate-300">
        ⓘ
      </span>
      <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-48 -translate-x-1/2 transform rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-200 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100">
        {tooltip}
        <div className="absolute top-full left-1/2 h-0 w-0 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
      </div>
    </div>
  </div>
);

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
const AGAINST_OPTIONS = ["any", "effect_target", "selected_target"] as const;

const createDefaultEffect = (): SpellDeclarativeEffect => ({
  type: "apply_condition",
  target: "selected_target",
  duration: { type: "manual" },
  params: { condition: "charmed" },
  stacking: "replace",
});

const retargetParams = (effectType: SpellDeclarativeEffectType): SpellDeclarativeEffect["params"] => {
  switch (effectType) {
    case "apply_condition":
      return { condition: "charmed" };
    case "modify_stat":
      return { stat: "temp_ac_bonus", value: 1 };
    case "advantage_on_checks":
    case "disadvantage_on_checks":
      return { ability: "charisma", against: "any" };
    case "restrict_action":
      return { action: "actions" };
  }
};

export const SpellCatalogEffectEditor = ({
  title,
  effects,
  onChange,
}: {
  title: string;
  effects: SpellDeclarativeEffect[];
  onChange: (next: SpellDeclarativeEffect[]) => void;
}) => {
  const { locale } = useLocale();
  return (
  <Section title={title}>
    <div className="space-y-3">
      {effects.map((effect, index) => (
        <div
          key={`${title}-${index}`}
          className="space-y-3 rounded-2xl border border-white/8 bg-slate-950/50 p-4"
        >
          {effect.target === "selected_target" && effect.type === "advantage_on_checks" && effect.params && "against" in effect.params && effect.params.against === "selected_target" && (
            <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-200">
              ⚠️ Aviso: efeito aplicado ao alvo contra ele mesmo (sem sentido semântico)
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-1.5">
              <FieldLabel label="Tipo de efeito" tooltip="Que tipo de efeito este é: aplicar condição, modificar atributo, ou dar vantagem/desvantagem em testes" />
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
                    {localizeSpellAdminValue(option, locale)}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <FieldLabel label="Alvo do efeito" tooltip="Quem recebe o efeito: o conjurador (caster) ou a criatura alvo (selected_target)" />
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
                    {localizeSpellAdminValue(option, locale)}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <FieldLabel label="Tipo de duração" tooltip="Como o efeito expira: manual (nunca), rodadas de combate, ou no início/fim do turno do alvo" />
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
                  {localizeSpellAdminValue(option, locale)}
                </option>
              ))}
            </select>
            </div>

            <div className="space-y-1.5">
              <FieldLabel label="Acumulação" tooltip="Replace: novo efeito remove o anterior. Stack: múltiplos efeitos podem coexistir" />
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
                <option value="replace">{localizeSpellAdminValue("replace", locale)}</option>
                <option value="stack">{localizeSpellAdminValue("stack", locale)}</option>
              </select>
            </div>
          </div>

          {effect.duration?.type === "rounds" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <FieldLabel label="Rodadas" tooltip="Quantas rodadas de combate o efeito dura (cada rodada = 6 segundos, todos os participantes contam de 1)" />
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
                                rounds: event.target.value === "" ? 1 : Math.max(1, Number(event.target.value) || 1),
                              },
                            }
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                  placeholder="Rounds"
                />
              </div>
              <div className="space-y-1.5">
                <FieldLabel label="Âncora da duração" tooltip="A quem a duração está atrelada: ao conjurador (caster) ou ao alvo do efeito (target)" />
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
                      {localizeSpellAdminValue(option, locale)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : null}

          {"condition" in effect.params ? (
            <div className="space-y-1.5">
              <FieldLabel label="Condição" tooltip="Que condição aplicar: cego, envenenado, paralizado, etc." />
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
                    {localizeSpellAdminValue(option, locale)}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          {"stat" in effect.params ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <FieldLabel label="Atributo" tooltip="Qual bônus modificar: classe de armadura, bônus de ataque, bônus de dano" />
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
                      {localizeSpellAdminValue(option, locale)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <FieldLabel label="Valor" tooltip="Quanto adicionar: +2 CA, +1 ataque, +1d6 dano, etc." />
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
                                value: event.target.value === "" ? 0 : Number(event.target.value) || 0,
                              },
                            }
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                />
              </div>
            </div>
          ) : null}

          {"ability" in effect.params ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <FieldLabel label="Habilidade" tooltip="Qual teste: Força, Destreza, Constituição, Inteligência, Sabedoria, Carisma" />
                <select
                  value={effect.params.ability}
                  onChange={(event) =>
                    onChange(
                      effects.map((entry, entryIndex) =>
                        entryIndex === index && "ability" in entry.params
                          ? {
                              ...entry,
                              params: { ...entry.params, ability: event.target.value as (typeof ABILITY_OPTIONS)[number] },
                            }
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                >
                  {ABILITY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {localizeSpellAdminValue(option, locale)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <FieldLabel label="Contra quem" tooltip="Quando a vantagem se aplica: contra qualquer um, apenas contra o alvo do efeito, ou apenas contra o alvo selecionado da magia" />
                <select
                  value={effect.params.against ?? "any"}
                  onChange={(event) =>
                    onChange(
                      effects.map((entry, entryIndex) =>
                        entryIndex === index && "ability" in entry.params
                          ? { ...entry, params: { ...entry.params, against: event.target.value as "any" | "effect_target" | "selected_target" } }
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                >
                  {AGAINST_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {localizeSpellAdminValue(option, locale)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : null}

          {"action" in effect.params ? (
            <div className="space-y-1.5">
              <FieldLabel label="Ação bloqueada" tooltip="Qual ação restringir: ações, ações bônus, reações, movimento" />
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
                    {localizeSpellAdminValue(option, locale)}
                  </option>
                ))}
              </select>
            </div>
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
};

export const SpellCatalogDeclarativeEffectsFields = ({
  state,
  setState,
}: Props) => (
  <div className="space-y-5">
    <SpellCatalogEffectEditor
      title="Efeitos declarativos"
      effects={state.effects}
      onChange={(next) => setState((current) => ({ ...current, effects: next }))}
    />
    <SpellCatalogEffectEditor
      title="Efeitos ao terminar"
      effects={state.onEndEffects}
      onChange={(next) => setState((current) => ({ ...current, onEndEffects: next }))}
    />
  </div>
);
