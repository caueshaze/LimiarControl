import type { Dispatch, SetStateAction } from "react";
import type { Locale, LocaleKey } from "../../../shared/i18n";
import {
  localizeDamageType,
  localizeSaveSuccessOutcome,
  localizeSpellAdminValue,
} from "../../../shared/i18n/domainLabels";
import { SpellCatalogField } from "./SpellCatalogEditorControls";
import {
  SPELL_DAMAGE_TYPE_OPTIONS,
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
      <div className="grid gap-4 sm:grid-cols-2">
        <SpellCatalogField label={t("catalog.spells.form.damageDice")}>
          <input
            value={state.damageDice}
            onChange={(event) =>
              setState((current) => ({ ...current, damageDice: event.target.value }))
            }
            className={fieldClassName}
            placeholder="8d6"
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
