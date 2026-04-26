import type { Dispatch, SetStateAction } from "react";
import type { LocaleKey } from "../../../shared/i18n";
import { SpellCatalogField } from "./SpellCatalogEditorControls";
import {
  SPELL_DICE_COUNT_OPTIONS,
  SPELL_DIE_SIZE_OPTIONS,
  type SpellCatalogEditorState,
} from "../utils/spellCatalogForm";

type Props = {
  state: SpellCatalogEditorState;
  setState: Dispatch<SetStateAction<SpellCatalogEditorState>>;
  t: (key: LocaleKey) => string;
  selectPlaceholder: string;
};

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

const THRESHOLDS = [1, 5, 11, 17] as const;

type ThresholdLevel = (typeof THRESHOLDS)[number];

const damageDiceKeys = {
  1:  { countKey: "cantripLevel1DiceCount",  dieKey: "cantripLevel1DieSize",  bonusKey: "cantripLevel1FixedBonus"  },
  5:  { countKey: "cantripLevel5DiceCount",  dieKey: "cantripLevel5DieSize",  bonusKey: "cantripLevel5FixedBonus"  },
  11: { countKey: "cantripLevel11DiceCount", dieKey: "cantripLevel11DieSize", bonusKey: "cantripLevel11FixedBonus" },
  17: { countKey: "cantripLevel17DiceCount", dieKey: "cantripLevel17DieSize", bonusKey: "cantripLevel17FixedBonus" },
} as const satisfies Record<ThresholdLevel, { countKey: keyof SpellCatalogEditorState; dieKey: keyof SpellCatalogEditorState; bonusKey: keyof SpellCatalogEditorState }>;

const instanceKeys = {
  1:  { instanceCountKey: "cantripLevel1InstanceCount",  diceCountKey: "cantripLevel1InstanceDiceCount",  dieSizeKey: "cantripLevel1InstanceDieSize",  bonusKey: "cantripLevel1InstanceFixedBonus"  },
  5:  { instanceCountKey: "cantripLevel5InstanceCount",  diceCountKey: "cantripLevel5InstanceDiceCount",  dieSizeKey: "cantripLevel5InstanceDieSize",  bonusKey: "cantripLevel5InstanceFixedBonus"  },
  11: { instanceCountKey: "cantripLevel11InstanceCount", diceCountKey: "cantripLevel11InstanceDiceCount", dieSizeKey: "cantripLevel11InstanceDieSize", bonusKey: "cantripLevel11InstanceFixedBonus" },
  17: { instanceCountKey: "cantripLevel17InstanceCount", diceCountKey: "cantripLevel17InstanceDiceCount", dieSizeKey: "cantripLevel17InstanceDieSize", bonusKey: "cantripLevel17InstanceFixedBonus" },
} as const satisfies Record<ThresholdLevel, { instanceCountKey: keyof SpellCatalogEditorState; diceCountKey: keyof SpellCatalogEditorState; dieSizeKey: keyof SpellCatalogEditorState; bonusKey: keyof SpellCatalogEditorState }>;

const INSTANCE_COUNT_OPTIONS = [1, 2, 3, 4, 5, 6] as const;

export const SpellCantripScalingFields = ({
  state,
  setState,
  t,
  selectPlaceholder,
}: Props) => (
  <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
    <div className="grid gap-4 sm:grid-cols-2">
      <SpellCatalogField label={t("catalog.spells.form.cantripScalingMode")}>
        <select
          value={state.cantripScalingMode}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              cantripScalingMode: event.target
                .value as SpellCatalogEditorState["cantripScalingMode"],
            }))
          }
          className={fieldClassName}
        >
          <option value="">{selectPlaceholder}</option>
          <option value="character_level">{t("catalog.spells.form.cantripScalingModeCharacterLevel")}</option>
        </select>
      </SpellCatalogField>

      {state.cantripScalingMode === "character_level" ? (
        <SpellCatalogField label={t("catalog.spells.form.cantripScalingEffectType")}>
          <select
            value={state.cantripScalingEffectType}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                cantripScalingEffectType: event.target
                  .value as SpellCatalogEditorState["cantripScalingEffectType"],
              }))
            }
            className={fieldClassName}
          >
            <option value="">{selectPlaceholder}</option>
            <option value="damage_dice">{t("catalog.spells.form.cantripScalingEffectTypeDamageDice")}</option>
            <option value="effect_instances">{t("catalog.spells.form.cantripScalingEffectTypeEffectInstances")}</option>
          </select>
        </SpellCatalogField>
      ) : null}
    </div>

    {state.cantripScalingMode === "character_level" && state.cantripScalingEffectType === "damage_dice" ? (
      <div className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          {t("catalog.spells.form.cantripScalingThresholds")}
        </p>
        {THRESHOLDS.map((level) => {
          const keys = damageDiceKeys[level];
          return (
            <div key={level} className="grid gap-4 sm:grid-cols-[90px_repeat(3,minmax(0,1fr))]">
              <div className="flex items-end pb-3 text-xs font-semibold text-slate-300">
                {t("catalog.spells.form.cantripThresholdLevel")} {level}
              </div>
              <SpellCatalogField label={t("catalog.spells.form.damageDiceCount")}>
                <select
                  value={state[keys.countKey] as string}
                  onChange={(event) =>
                    setState((current) => ({
                      ...current,
                      [keys.countKey]: event.target.value,
                    }))
                  }
                  className={fieldClassName}
                >
                  <option value="">{selectPlaceholder}</option>
                  {SPELL_DICE_COUNT_OPTIONS.map((count) => (
                    <option key={count} value={count}>
                      {count}
                    </option>
                  ))}
                </select>
              </SpellCatalogField>
              <SpellCatalogField label={t("catalog.spells.form.damageDieSize")}>
                <select
                  value={state[keys.dieKey] as string}
                  onChange={(event) =>
                    setState((current) => ({
                      ...current,
                      [keys.dieKey]: event.target.value,
                    }))
                  }
                  className={fieldClassName}
                >
                  <option value="">{selectPlaceholder}</option>
                  {SPELL_DIE_SIZE_OPTIONS.map((size) => (
                    <option key={size} value={size}>
                      d{size}
                    </option>
                  ))}
                </select>
              </SpellCatalogField>
              <SpellCatalogField label={t("catalog.spells.form.damageFixedBonus")}>
                <input
                  type="number"
                  step={1}
                  value={state[keys.bonusKey] as string}
                  onChange={(event) =>
                    setState((current) => ({
                      ...current,
                      [keys.bonusKey]: event.target.value,
                    }))
                  }
                  className={fieldClassName}
                  placeholder="0"
                />
              </SpellCatalogField>
            </div>
          );
        })}
      </div>
    ) : null}

    {state.cantripScalingMode === "character_level" && state.cantripScalingEffectType === "effect_instances" ? (
      <div className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          {t("catalog.spells.form.cantripScalingThresholds")}
        </p>
        {THRESHOLDS.map((level) => {
          const keys = instanceKeys[level];
          return (
            <div key={level} className="space-y-2">
              <p className="text-xs font-semibold text-slate-300">
                {t("catalog.spells.form.cantripThresholdLevel")} {level}
              </p>
              <div className="grid gap-4 sm:grid-cols-[repeat(4,minmax(0,1fr))]">
                <SpellCatalogField label={t("catalog.spells.form.cantripInstanceCount")}>
                  <select
                    value={state[keys.instanceCountKey] as string}
                    onChange={(event) =>
                      setState((current) => ({
                        ...current,
                        [keys.instanceCountKey]: event.target.value,
                      }))
                    }
                    className={fieldClassName}
                  >
                    <option value="">{selectPlaceholder}</option>
                    {INSTANCE_COUNT_OPTIONS.map((count) => (
                      <option key={count} value={count}>
                        {count}
                      </option>
                    ))}
                  </select>
                </SpellCatalogField>
                <SpellCatalogField label={t("catalog.spells.form.cantripInstanceDiceCount")}>
                  <select
                    value={state[keys.diceCountKey] as string}
                    onChange={(event) =>
                      setState((current) => ({
                        ...current,
                        [keys.diceCountKey]: event.target.value,
                      }))
                    }
                    className={fieldClassName}
                  >
                    <option value="">{selectPlaceholder}</option>
                    {SPELL_DICE_COUNT_OPTIONS.map((count) => (
                      <option key={count} value={count}>
                        {count}
                      </option>
                    ))}
                  </select>
                </SpellCatalogField>
                <SpellCatalogField label={t("catalog.spells.form.cantripInstanceDieSize")}>
                  <select
                    value={state[keys.dieSizeKey] as string}
                    onChange={(event) =>
                      setState((current) => ({
                        ...current,
                        [keys.dieSizeKey]: event.target.value,
                      }))
                    }
                    className={fieldClassName}
                  >
                    <option value="">{selectPlaceholder}</option>
                    {SPELL_DIE_SIZE_OPTIONS.map((size) => (
                      <option key={size} value={size}>
                        d{size}
                      </option>
                    ))}
                  </select>
                </SpellCatalogField>
                <SpellCatalogField label={t("catalog.spells.form.cantripInstanceFixedBonus")}>
                  <input
                    type="number"
                    step={1}
                    value={state[keys.bonusKey] as string}
                    onChange={(event) =>
                      setState((current) => ({
                        ...current,
                        [keys.bonusKey]: event.target.value,
                      }))
                    }
                    className={fieldClassName}
                    placeholder="0"
                  />
                </SpellCatalogField>
              </div>
            </div>
          );
        })}
      </div>
    ) : null}
  </div>
);
