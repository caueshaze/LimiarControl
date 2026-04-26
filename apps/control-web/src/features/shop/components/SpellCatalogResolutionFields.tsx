import type { Dispatch, SetStateAction } from "react";
import type { Locale, LocaleKey } from "../../../shared/i18n";
import {
  localizeDamageType,
  localizeSaveSuccessOutcome,
  localizeSpellAdminValue,
} from "../../../shared/i18n/domainLabels";
import { SpellCatalogField } from "./SpellCatalogEditorControls";
import {
  SPELL_DICE_COUNT_OPTIONS,
  SPELL_DAMAGE_TYPE_OPTIONS,
  SPELL_DIE_SIZE_OPTIONS,
  SPELL_RESOLUTION_TYPE_OPTIONS,
  SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS,
  SPELL_SAVING_THROW_OPTIONS,
  type SpellCatalogEditorState,
} from "../utils/spellCatalogForm";

type Props = {
  state: SpellCatalogEditorState;
  setState: Dispatch<SetStateAction<SpellCatalogEditorState>>;
  t: (key: LocaleKey) => string;
  locale: Locale;
  selectPlaceholder: string;
  showSavingThrowFields: boolean;
  showSaveSuccessOutcome: boolean;
  showDamageFields: boolean;
  showHealFields: boolean;
};

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

export const SpellCatalogResolutionFields = ({
  state,
  setState,
  t,
  locale,
  selectPlaceholder,
  showSavingThrowFields,
  showSaveSuccessOutcome,
  showDamageFields,
  showHealFields,
}: Props) => (
  <>
    <div className="grid gap-4 sm:grid-cols-3">
      <SpellCatalogField label={t("catalog.spells.form.resolutionType")}>
        <select
          value={state.resolutionType}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              resolutionType: event.target.value as SpellCatalogEditorState["resolutionType"],
            }))
          }
          className={fieldClassName}
        >
          <option value="">{selectPlaceholder}</option>
          {SPELL_RESOLUTION_TYPE_OPTIONS.map((resolutionType) => (
            <option key={resolutionType} value={resolutionType}>
              {localizeSpellAdminValue(resolutionType, locale)}
            </option>
          ))}
        </select>
      </SpellCatalogField>
      {showSavingThrowFields ? (
        <SpellCatalogField label={t("catalog.spells.form.savingThrow")}>
          <select
            value={state.savingThrow}
            onChange={(event) =>
              setState((current) => ({ ...current, savingThrow: event.target.value }))
            }
            className={fieldClassName}
          >
            <option value="">{selectPlaceholder}</option>
            {SPELL_SAVING_THROW_OPTIONS.map((savingThrow) => (
              <option key={savingThrow} value={savingThrow}>
                {savingThrow}
              </option>
            ))}
          </select>
        </SpellCatalogField>
      ) : null}
      {showSaveSuccessOutcome ? (
        <SpellCatalogField label={t("catalog.spells.form.saveSuccessOutcome")}>
          <select
            value={state.saveSuccessOutcome}
            onChange={(event) =>
              setState((current) => ({ ...current, saveSuccessOutcome: event.target.value }))
            }
            className={fieldClassName}
          >
            <option value="">{selectPlaceholder}</option>
            {SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS.map((outcome) => (
              <option key={outcome} value={outcome}>
                {localizeSaveSuccessOutcome(outcome, locale)}
              </option>
            ))}
          </select>
        </SpellCatalogField>
      ) : null}
    </div>

    {showDamageFields ? (
      <div className="grid gap-4 sm:grid-cols-4">
        <SpellCatalogField
          label={t("catalog.spells.form.damageDiceCount")}
          help={t("catalog.spells.form.damageDiceCountHelp")}
        >
          <select
            value={state.damageDiceCount}
            onChange={(event) =>
              setState((current) => ({ ...current, damageDiceCount: event.target.value }))
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
        <SpellCatalogField
          label={t("catalog.spells.form.damageDieSize")}
          help={t("catalog.spells.form.damageDieSizeHelp")}
        >
          <select
            value={state.damageDieSize}
            onChange={(event) =>
              setState((current) => ({ ...current, damageDieSize: event.target.value }))
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
        <SpellCatalogField
          label={t("catalog.spells.form.damageFixedBonus")}
          help={t("catalog.spells.form.damageFixedBonusHelp")}
        >
          <input
            type="number"
            step={1}
            value={state.damageFixedBonus}
            onChange={(event) =>
              setState((current) => ({ ...current, damageFixedBonus: event.target.value }))
            }
            className={fieldClassName}
            placeholder="0"
          />
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.form.damageType")}>
          <select
            value={state.damageType}
            onChange={(event) =>
              setState((current) => ({ ...current, damageType: event.target.value }))
            }
            className={fieldClassName}
          >
            <option value="">{selectPlaceholder}</option>
            {SPELL_DAMAGE_TYPE_OPTIONS.map((damageType) => (
              <option key={damageType} value={damageType}>
                {localizeDamageType(damageType, locale)}
              </option>
            ))}
          </select>
        </SpellCatalogField>
      </div>
    ) : null}

    {showHealFields ? (
      <SpellCatalogField label={t("catalog.spells.form.healDice")}>
        <input
          value={state.healDice}
          onChange={(event) =>
            setState((current) => ({ ...current, healDice: event.target.value }))
          }
          className={fieldClassName}
          placeholder="1d8"
        />
      </SpellCatalogField>
    ) : null}
  </>
);
