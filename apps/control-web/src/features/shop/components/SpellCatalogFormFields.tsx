import type { Dispatch, SetStateAction } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";
import {
  localizeDamageType,
  localizeSaveSuccessOutcome,
  localizeSpellClass,
} from "../../../shared/i18n/domainLabels";
import {
  SpellCatalogField,
  SpellCatalogLegacyWarning,
  SpellCatalogToggleChip,
} from "./SpellCatalogEditorControls";
import {
  SPELL_CLASS_OPTIONS,
  SPELL_COMPONENT_OPTIONS,
  SPELL_DAMAGE_TYPE_OPTIONS,
  SPELL_LEVEL_OPTIONS,
  SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS,
  SPELL_SAVING_THROW_OPTIONS,
  SPELL_SCHOOL_OPTIONS,
  type SpellCatalogEditorState,
  toggleSpellListValue,
} from "../utils/spellCatalogForm";

type Props = {
  state: SpellCatalogEditorState;
  setState: Dispatch<SetStateAction<SpellCatalogEditorState>>;
  showCanonicalKey?: boolean;
  unsupportedValues?: string[];
};

const schoolLabelKey = (school: string): LocaleKey =>
  `catalog.spells.school.${school}` as LocaleKey;

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

export const SpellCatalogFormFields = ({
  state,
  setState,
  showCanonicalKey = false,
  unsupportedValues = [],
}: Props) => {
  const { locale, t } = useLocale();

  return (
    <>
      {showCanonicalKey ? (
        <SpellCatalogField label={t("catalog.spells.form.canonicalKey")}>
          <input
            value={state.canonicalKey}
            onChange={(event) =>
              setState((current) => ({ ...current, canonicalKey: event.target.value }))
            }
            className={fieldClassName}
          />
        </SpellCatalogField>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <SpellCatalogField label={t("catalog.spells.form.nameEn")}>
          <input
            value={state.nameEn}
            onChange={(event) => setState((current) => ({ ...current, nameEn: event.target.value }))}
            className={fieldClassName}
          />
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.form.namePt")}>
          <input
            value={state.namePt}
            onChange={(event) => setState((current) => ({ ...current, namePt: event.target.value }))}
            className={fieldClassName}
          />
        </SpellCatalogField>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <SpellCatalogField label={t("catalog.spells.form.level")}>
          <select
            value={state.level}
            onChange={(event) =>
              setState((current) => ({ ...current, level: Number(event.target.value) }))
            }
            className={fieldClassName}
          >
            {SPELL_LEVEL_OPTIONS.map((level) => (
              <option key={level} value={level}>
                {level === 0 ? t("catalog.spells.cantrip") : `${t("catalog.spells.levelLabel")} ${level}`}
              </option>
            ))}
          </select>
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.form.school")}>
          <select
            value={state.school}
            onChange={(event) =>
              setState((current) => ({ ...current, school: event.target.value as BaseSpell["school"] }))
            }
            className={fieldClassName}
          >
            {SPELL_SCHOOL_OPTIONS.map((school) => (
              <option key={school} value={school}>
                {t(schoolLabelKey(school))}
              </option>
            ))}
          </select>
        </SpellCatalogField>
      </div>

      {unsupportedValues.length > 0 ? (
        <SpellCatalogLegacyWarning
          title={t("catalog.spells.form.legacyWarningTitle")}
          description={t("catalog.spells.form.legacyWarningDescription")}
          values={unsupportedValues}
        />
      ) : null}

      <SpellCatalogField label={t("catalog.spells.form.classes")}>
        <div className="flex flex-wrap gap-2">
          {SPELL_CLASS_OPTIONS.map((className) => (
            <SpellCatalogToggleChip
              key={className}
              active={state.classesJson.includes(className)}
              label={localizeSpellClass(className, locale)}
              onClick={() =>
                setState((current) => ({
                  ...current,
                  classesJson: toggleSpellListValue(current.classesJson, className),
                }))
              }
            />
          ))}
        </div>
      </SpellCatalogField>

      <div className="grid gap-4 sm:grid-cols-4">
        <SpellCatalogField label={t("catalog.spells.castingTime")}>
          <input
            value={state.castingTime}
            onChange={(event) =>
              setState((current) => ({ ...current, castingTime: event.target.value }))
            }
            className={fieldClassName}
          />
        </SpellCatalogField>
        <SpellCatalogField label={`${t("catalog.spells.range")} (m)`}>
          <input
            type="number"
            min={0}
            value={state.rangeMeters}
            onChange={(event) =>
              setState((current) => ({ ...current, rangeMeters: event.target.value }))
            }
            className={fieldClassName}
          />
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.rangeText")}>
          <input
            value={state.rangeText}
            onChange={(event) =>
              setState((current) => ({ ...current, rangeText: event.target.value }))
            }
            className={fieldClassName}
          />
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.duration")}>
          <input
            value={state.duration}
            onChange={(event) => setState((current) => ({ ...current, duration: event.target.value }))}
            className={fieldClassName}
          />
        </SpellCatalogField>
      </div>

      <SpellCatalogField label={t("catalog.spells.form.components")}>
        <div className="flex flex-wrap gap-2">
          {SPELL_COMPONENT_OPTIONS.map((component) => (
            <SpellCatalogToggleChip
              key={component}
              active={state.componentsJson.includes(component)}
              label={component}
              onClick={() =>
                setState((current) => ({
                  ...current,
                  componentsJson: toggleSpellListValue(current.componentsJson, component),
                }))
              }
            />
          ))}
        </div>
      </SpellCatalogField>

      {state.componentsJson.includes("M") ? (
        <SpellCatalogField label={t("catalog.spells.form.material")}>
          <input
            value={state.materialComponentText}
            onChange={(event) =>
              setState((current) => ({ ...current, materialComponentText: event.target.value }))
            }
            className={fieldClassName}
          />
        </SpellCatalogField>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <SpellCatalogField label={t("catalog.spells.form.damageType")}>
          <select
            value={state.damageType}
            onChange={(event) => setState((current) => ({ ...current, damageType: event.target.value }))}
            className={fieldClassName}
          >
            <option value="">{t("catalog.spells.form.none")}</option>
            {SPELL_DAMAGE_TYPE_OPTIONS.map((damageType) => (
              <option key={damageType} value={damageType}>
                {localizeDamageType(damageType, locale)}
              </option>
            ))}
          </select>
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.form.savingThrow")}>
          <select
            value={state.savingThrow}
            onChange={(event) =>
              setState((current) => ({ ...current, savingThrow: event.target.value }))
            }
            className={fieldClassName}
          >
            <option value="">{t("catalog.spells.form.none")}</option>
            {SPELL_SAVING_THROW_OPTIONS.map((savingThrow) => (
              <option key={savingThrow} value={savingThrow}>
                {savingThrow}
              </option>
            ))}
          </select>
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.form.saveSuccessOutcome")}>
          <select
            value={state.saveSuccessOutcome}
            onChange={(event) =>
              setState((current) => ({ ...current, saveSuccessOutcome: event.target.value }))
            }
            disabled={!state.savingThrow}
            className={`${fieldClassName} disabled:opacity-50`}
          >
            <option value="">{t("catalog.spells.form.none")}</option>
            {SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS.map((outcome) => (
              <option key={outcome} value={outcome}>
                {localizeSaveSuccessOutcome(outcome, locale)}
              </option>
            ))}
          </select>
        </SpellCatalogField>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <SpellCatalogField label={t("catalog.spells.form.descriptionEn")}>
          <textarea
            value={state.descriptionEn}
            onChange={(event) =>
              setState((current) => ({ ...current, descriptionEn: event.target.value }))
            }
            rows={5}
            className={fieldClassName}
          />
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.form.descriptionPt")}>
          <textarea
            value={state.descriptionPt}
            onChange={(event) =>
              setState((current) => ({ ...current, descriptionPt: event.target.value }))
            }
            rows={5}
            className={fieldClassName}
          />
        </SpellCatalogField>
      </div>

      <div className="flex flex-wrap gap-2">
        <SpellCatalogToggleChip
          active={state.concentration}
          label={t("catalog.spells.concentration")}
          onClick={() =>
            setState((current) => ({ ...current, concentration: !current.concentration }))
          }
        />
        <SpellCatalogToggleChip
          active={state.ritual}
          label={t("catalog.spells.ritual")}
          onClick={() => setState((current) => ({ ...current, ritual: !current.ritual }))}
        />
      </div>
    </>
  );
};
