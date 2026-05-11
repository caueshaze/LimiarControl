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
type DeclarativeEffectsState = {
  effects: SpellDeclarativeEffect[];
  onEndEffects: SpellDeclarativeEffect[];
};

type Props<TState extends DeclarativeEffectsState = DeclarativeEffectsState> = {
  state: TState;
  setState: Dispatch<SetStateAction<TState>>;
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
  "modify_weapon_damage",
  "armor_class_formula",
  "advantage_on_checks",
  "disadvantage_on_checks",
  "advantage_on_saves",
  "disadvantage_on_saves",
  "size_modifier",
  "restrict_action",
];
const TARGET_OPTIONS: SpellDeclarativeEffectTarget[] = ["selected_target", "caster"];
const DURATION_OPTIONS = ["manual", "rounds", "until_turn_start", "until_turn_end", "timed"] as const;
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
    case "modify_weapon_damage":
      return { dice: "1d4", operation: "add", minimum_total_damage: null };
    case "armor_class_formula":
      return { base_value: 13, ability: "dexterity", requires_unarmored: true };
    case "advantage_on_checks":
    case "disadvantage_on_checks":
      return { ability: "charisma", against: "any" };
    case "advantage_on_saves":
    case "disadvantage_on_saves":
      return { abilities: ["strength"] };
    case "size_modifier":
      return { value: 1 };
    case "restrict_action":
      return { action: "actions" };
  }
};

const updateEffectAtIndex = (
  effects: SpellDeclarativeEffect[],
  index: number,
  updater: (effect: SpellDeclarativeEffect) => SpellDeclarativeEffect,
): SpellDeclarativeEffect[] =>
  effects.map((entry, entryIndex) => (entryIndex === index ? updater(entry) : entry));

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
                    updateEffectAtIndex(effects, index, (entry) => ({
                      ...entry,
                      type: event.target.value as SpellDeclarativeEffectType,
                      params: retargetParams(event.target.value as SpellDeclarativeEffectType),
                    }) as SpellDeclarativeEffect),
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
                            seconds: event.target.value === "timed" ? 60 : null,
                            anchor: event.target.value === "manual" || event.target.value === "timed" ? null : "target",
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

          {effect.duration?.type === "timed" ? (
            <div className="space-y-1.5">
              <FieldLabel label="Segundos" tooltip="Quantos segundos de tempo de jogo o efeito dura." />
              <input
                type="number"
                min={1}
                value={effect.duration.seconds ?? 60}
                onChange={(event) =>
                  onChange(
                    effects.map((entry, entryIndex) =>
                      entryIndex === index
                        ? {
                            ...entry,
                            duration: {
                              ...(entry.duration ?? { type: "timed" }),
                              type: "timed",
                              seconds: event.target.value === "" ? 60 : Math.max(1, Number(event.target.value) || 60),
                              anchor: null,
                            },
                          }
                        : entry,
                    ),
                  )
                }
                className={fieldClassName}
                placeholder="60"
              />
            </div>
          ) : null}

          {"condition" in effect.params ? (
            <div className="space-y-1.5">
              <FieldLabel label="Condição" tooltip="Que condição aplicar: cego, envenenado, paralizado, etc." />
              <select
                value={effect.params.condition}
                onChange={(event) =>
                  onChange(
                    updateEffectAtIndex(effects, index, (entry) =>
                      "condition" in entry.params
                        ? ({
                            ...entry,
                            params: {
                              condition: event.target.value as SpellDeclarativeConditionType,
                            },
                          } as SpellDeclarativeEffect)
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

          {effect.type === "modify_weapon_damage" && "dice" in effect.params ? (
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5">
                <FieldLabel label="Dado" tooltip="Dado somado ou subtraído do dano de arma, por exemplo 1d4." />
                <input
                  value={effect.params.dice}
                  onChange={(event) =>
                    onChange(
                      updateEffectAtIndex(effects, index, (entry) =>
                        entry.type === "modify_weapon_damage" && "dice" in entry.params
                          ? ({
                              ...entry,
                              params: { ...entry.params, dice: event.target.value },
                            } as SpellDeclarativeEffect)
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                  placeholder="1d4"
                />
              </div>
              <div className="space-y-1.5">
                <FieldLabel label="Operação" tooltip="Somar ou subtrair o dado do dano de arma." />
                <select
                  value={effect.params.operation ?? "add"}
                  onChange={(event) =>
                    onChange(
                      updateEffectAtIndex(effects, index, (entry) =>
                        entry.type === "modify_weapon_damage"
                          ? ({
                              ...entry,
                              params: { ...entry.params, operation: event.target.value as "add" | "subtract" },
                            } as SpellDeclarativeEffect)
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                >
                  <option value="add">{localizeSpellAdminValue("add", locale)}</option>
                  <option value="subtract">{localizeSpellAdminValue("subtract", locale)}</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <FieldLabel label="Dano mínimo" tooltip="Dano total mínimo depois da modificação; vazio para nenhum mínimo específico." />
                <input
                  type="number"
                  min={0}
                  value={effect.params.minimum_total_damage ?? ""}
                  onChange={(event) =>
                    onChange(
                      updateEffectAtIndex(effects, index, (entry) =>
                        entry.type === "modify_weapon_damage"
                          ? ({
                              ...entry,
                              params: {
                                ...entry.params,
                                minimum_total_damage: event.target.value === "" ? null : Math.max(0, Number(event.target.value) || 0),
                              },
                            } as SpellDeclarativeEffect)
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                />
              </div>
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
                      updateEffectAtIndex(effects, index, (entry) =>
                        "stat" in entry.params
                          ? ({
                              ...entry,
                              params: {
                                ...entry.params,
                                stat: event.target.value as SpellDeclarativeModifyStat,
                              },
                            } as SpellDeclarativeEffect)
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
                      updateEffectAtIndex(effects, index, (entry) =>
                        "stat" in entry.params
                          ? ({
                              ...entry,
                              params: {
                                ...entry.params,
                                value: event.target.value === "" ? 0 : Number(event.target.value) || 0,
                              },
                            } as SpellDeclarativeEffect)
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                />
              </div>
            </div>
          ) : null}

          {(
            (effect.type === "advantage_on_saves" || effect.type === "disadvantage_on_saves")
            && "abilities" in effect.params
          ) ? (
            <div className="space-y-1.5">
              <FieldLabel label="Salvaguardas" tooltip="Habilidades cujas salvaguardas recebem vantagem ou desvantagem." />
              <div className="grid gap-2 sm:grid-cols-3">
                {ABILITY_OPTIONS.map((ability) => (
                  <label key={ability} className="flex items-center gap-2 rounded-2xl border border-white/8 bg-slate-950/40 px-4 py-3 text-sm text-slate-200">
                    <input
                      type="checkbox"
                      checked={effect.params.abilities.includes(ability)}
                      onChange={(event) =>
                        onChange(
                          updateEffectAtIndex(effects, index, (entry) => {
                            if (
                              (entry.type !== "advantage_on_saves" && entry.type !== "disadvantage_on_saves")
                              || !("abilities" in entry.params)
                            ) {
                              return entry;
                            }
                            const nextAbilities = event.target.checked
                              ? [...entry.params.abilities, ability]
                              : entry.params.abilities.filter((entryAbility) => entryAbility !== ability);
                            return {
                              ...entry,
                              params: { ...entry.params, abilities: nextAbilities.length > 0 ? nextAbilities : [ability] },
                            } as SpellDeclarativeEffect;
                          }),
                        )
                      }
                      className="h-4 w-4 rounded border-white/10 bg-slate-900 text-violet-400"
                    />
                    <span>{localizeSpellAdminValue(ability, locale)}</span>
                  </label>
                ))}
              </div>
            </div>
          ) : null}

          {effect.type === "size_modifier" && "value" in effect.params ? (
            <div className="space-y-1.5">
              <FieldLabel label="Tamanho" tooltip="Ajuste temporário de categoria de tamanho: +1 aumenta, -1 reduz." />
              <select
                value={effect.params.value}
                onChange={(event) =>
                  onChange(
                    updateEffectAtIndex(effects, index, (entry) =>
                      entry.type === "size_modifier" && "value" in entry.params
                        ? ({
                            ...entry,
                            params: { value: Number(event.target.value) === -1 ? -1 : 1 },
                          } as SpellDeclarativeEffect)
                        : entry,
                    ),
                  )
                }
                className={fieldClassName}
              >
                <option value={1}>+1</option>
                <option value={-1}>-1</option>
              </select>
            </div>
          ) : null}

          {effect.type === "armor_class_formula" && "base_value" in effect.params ? (
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5">
                <FieldLabel label="Base" tooltip="Valor base da fórmula de CA: por exemplo, 13 em 13 + DEX." />
                <input
                  type="number"
                  min={0}
                  value={effect.params.base_value}
                  onChange={(event) =>
                    onChange(
                      updateEffectAtIndex(effects, index, (entry) =>
                        entry.type === "armor_class_formula" && "base_value" in entry.params
                          ? ({
                              ...entry,
                              params: {
                                ...entry.params,
                                base_value: event.target.value === "" ? 0 : Math.max(0, Number(event.target.value) || 0),
                              },
                            } as SpellDeclarativeEffect)
                          : entry,
                      ),
                    )
                  }
                  className={fieldClassName}
                />
              </div>

              <div className="space-y-1.5">
                <FieldLabel label="Habilidade" tooltip="Modificador somado à base: normalmente Destreza para fórmulas como Armadura Arcana." />
                <select
                  value={effect.params.ability}
                  onChange={(event) =>
                    onChange(
                      updateEffectAtIndex(effects, index, (entry) =>
                        entry.type === "armor_class_formula" && "ability" in entry.params
                          ? ({
                              ...entry,
                              params: { ...entry.params, ability: event.target.value as (typeof ABILITY_OPTIONS)[number] },
                            } as SpellDeclarativeEffect)
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

              <label className="flex items-center gap-2 rounded-2xl border border-white/8 bg-slate-950/40 px-4 py-3 text-sm text-slate-200">
                <input
                  type="checkbox"
                  checked={effect.params.requires_unarmored === true}
                  onChange={(event) =>
                    onChange(
                      updateEffectAtIndex(effects, index, (entry) =>
                        entry.type === "armor_class_formula" && "requires_unarmored" in entry.params
                          ? ({
                              ...entry,
                              params: {
                                ...entry.params,
                                requires_unarmored: event.target.checked,
                              },
                            } as SpellDeclarativeEffect)
                          : entry,
                      ),
                    )
                  }
                  className="h-4 w-4 rounded border-white/10 bg-slate-900 text-violet-400"
                />
                <span>Requer estar sem armadura</span>
              </label>
            </div>
          ) : null}

          {(
            (effect.type === "advantage_on_checks" || effect.type === "disadvantage_on_checks")
            && "ability" in effect.params
          ) ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <FieldLabel label="Habilidade" tooltip="Qual teste: Força, Destreza, Constituição, Inteligência, Sabedoria, Carisma" />
                <select
                  value={effect.params.ability}
                  onChange={(event) =>
                    onChange(
                      updateEffectAtIndex(effects, index, (entry) =>
                        "ability" in entry.params
                          ? ({
                              ...entry,
                              params: { ...entry.params, ability: event.target.value as (typeof ABILITY_OPTIONS)[number] },
                            } as SpellDeclarativeEffect)
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
                      updateEffectAtIndex(effects, index, (entry) =>
                        "ability" in entry.params
                          ? ({
                              ...entry,
                              params: { ...entry.params, against: event.target.value as "any" | "effect_target" | "selected_target" },
                            } as SpellDeclarativeEffect)
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
                    updateEffectAtIndex(effects, index, (entry) =>
                      "action" in entry.params
                        ? ({
                            ...entry,
                            params: {
                              action: event.target.value as SpellDeclarativeRestrictActionKind,
                            },
                          } as SpellDeclarativeEffect)
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

export const SpellCatalogDeclarativeEffectsFields = <TState extends DeclarativeEffectsState>({
  state,
  setState,
}: Props<TState>) => (
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
