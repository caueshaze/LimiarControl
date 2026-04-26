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

const thresholdFields = [
  {
    level: 1,
    countKey: "cantripLevel1DiceCount",
    dieKey: "cantripLevel1DieSize",
    bonusKey: "cantripLevel1FixedBonus",
  },
  {
    level: 5,
    countKey: "cantripLevel5DiceCount",
    dieKey: "cantripLevel5DieSize",
    bonusKey: "cantripLevel5FixedBonus",
  },
  {
    level: 11,
    countKey: "cantripLevel11DiceCount",
    dieKey: "cantripLevel11DieSize",
    bonusKey: "cantripLevel11FixedBonus",
  },
  {
    level: 17,
    countKey: "cantripLevel17DiceCount",
    dieKey: "cantripLevel17DieSize",
    bonusKey: "cantripLevel17FixedBonus",
  },
] as const;

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
          <option value="character_level">Character level</option>
        </select>
      </SpellCatalogField>
    </div>

    {state.cantripScalingMode === "character_level" ? (
      <div className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          {t("catalog.spells.form.cantripScalingThresholds")}
        </p>
        {thresholdFields.map((threshold) => (
          <div key={threshold.level} className="grid gap-4 sm:grid-cols-[90px_repeat(3,minmax(0,1fr))]">
            <div className="flex items-end pb-3 text-xs font-semibold text-slate-300">
              Nível {threshold.level}
            </div>
            <SpellCatalogField label={t("catalog.spells.form.damageDiceCount")}>
              <select
                value={state[threshold.countKey]}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    [threshold.countKey]: event.target.value,
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
                value={state[threshold.dieKey]}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    [threshold.dieKey]: event.target.value,
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
                value={state[threshold.bonusKey]}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    [threshold.bonusKey]: event.target.value,
                  }))
                }
                className={fieldClassName}
                placeholder="0"
              />
            </SpellCatalogField>
          </div>
        ))}
      </div>
    ) : null}
  </div>
);
