import type { Dispatch, SetStateAction } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";
import {
  localizeSpellAdminValue,
  localizeSpellClass,
} from "../../../shared/i18n/domainLabels";
import {
  SpellCatalogField,
  SpellCatalogLegacyWarning,
  SpellCatalogToggleChip,
} from "./SpellCatalogEditorControls";
import { SpellUpcastFields } from "./SpellUpcastFields";
import { SpellCatalogResolutionFields } from "./SpellCatalogResolutionFields";
import { SpellCatalogTargetingRequirements } from "./SpellCatalogTargetingRequirements";
import {
    SPELL_CLASS_OPTIONS,
    SPELL_COMPONENT_OPTIONS,
    SPELL_CASTING_TIME_TYPE_OPTIONS,
    SPELL_LEVEL_OPTIONS,
    SPELL_SCHOOL_OPTIONS,
    SPELL_AREA_SHAPE_OPTIONS,
    SPELL_TARGET_TYPE_OPTIONS,
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
  const selectPlaceholder = t("catalog.admin.selectPlaceholder");
  const booleanSelectValue = (value: boolean | null) =>
    value === true ? "true" : value === false ? "false" : "";
  const parseBooleanSelectValue = (value: string): boolean | null =>
    value === "true" ? true : value === "false" ? false : null;
  const showSavingThrowFields =
    state.resolutionType === "damage" ||
    state.resolutionType === "control" ||
    state.resolutionType === "debuff";
  const showSaveSuccessOutcome =
    state.resolutionType === "damage" && Boolean(state.savingThrow);
  const showDamageFields = state.resolutionType === "damage";
  const showHealFields = state.resolutionType === "heal";
  const showUpcastDiceField =
    state.upcastMode === "extra_damage_dice" ||
    state.upcastMode === "extra_heal_dice";
  const showUpcastFlatField =
    state.upcastMode === "extra_damage_dice" ||
    state.upcastMode === "extra_heal_dice" ||
    state.upcastMode === "flat_bonus";
  const showUpcastPerLevelField = Boolean(state.upcastMode);
  const showUpcastMaxLevelField = Boolean(state.upcastMode);
  const showEffectScalingFields = state.upcastMode === "effect_scaling";
  const showExtraEffectFields = state.upcastMode === "extra_effect";
  const showAreaSizeField = Boolean(state.areaShape);

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
        <SpellCatalogField label={t("catalog.spells.form.castingTimeType")}>
          <select
            value={state.castingTimeType}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                castingTimeType: event.target.value as SpellCatalogEditorState["castingTimeType"],
              }))
            }
            className={fieldClassName}
          >
            <option value="">{selectPlaceholder}</option>
            {SPELL_CASTING_TIME_TYPE_OPTIONS.map((castingTimeType) => (
              <option key={castingTimeType} value={castingTimeType}>
                {localizeSpellAdminValue(castingTimeType, locale)}
              </option>
            ))}
          </select>
        </SpellCatalogField>
        <SpellCatalogField label={t("catalog.spells.form.castingTimeText")}>
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
        <SpellCatalogField label={t("catalog.spells.form.targetType")}>
          <select
            value={state.targetType}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                targetType: event.target.value as SpellCatalogEditorState["targetType"],
              }))
            }
            className={fieldClassName}
          >
            <option value="">{selectPlaceholder}</option>
            {SPELL_TARGET_TYPE_OPTIONS.map((targetType) => (
              <option key={targetType} value={targetType}>
                {localizeSpellAdminValue(targetType, locale)}
              </option>
            ))}
          </select>
        </SpellCatalogField>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <SpellCatalogField label={t("catalog.spells.form.areaShape")}>
          <select
            value={state.areaShape}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                areaShape: event.target.value as SpellCatalogEditorState["areaShape"],
              }))
            }
            className={fieldClassName}
          >
            <option value="">{selectPlaceholder}</option>
            {SPELL_AREA_SHAPE_OPTIONS.map((shape) => (
              <option key={shape} value={shape}>
                {localizeSpellAdminValue(shape, locale)}
              </option>
            ))}
          </select>
        </SpellCatalogField>
      </div>

      {showAreaSizeField ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <SpellCatalogField label={t("catalog.spells.form.areaSizeMeters")}>
            <input
              type="number"
              min={1}
              value={state.areaSizeMeters}
              onChange={(event) =>
                setState((current) => ({ ...current, areaSizeMeters: event.target.value }))
              }
              className={fieldClassName}
            />
          </SpellCatalogField>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
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

      <SpellCatalogResolutionFields
        state={state}
        setState={setState}
        t={t}
        locale={locale}
        selectPlaceholder={selectPlaceholder}
        showSavingThrowFields={showSavingThrowFields}
        showSaveSuccessOutcome={showSaveSuccessOutcome}
        showDamageFields={showDamageFields}
        showHealFields={showHealFields}
      />

      <SpellCatalogTargetingRequirements
        state={state}
        setState={setState}
        t={t}
        booleanSelectValue={booleanSelectValue}
        parseBooleanSelectValue={parseBooleanSelectValue}
      />

      <SpellUpcastFields
        state={state}
        setState={setState}
        t={t}
        locale={locale}
        selectPlaceholder={selectPlaceholder}
        showUpcastDiceField={showUpcastDiceField}
        showUpcastFlatField={showUpcastFlatField}
        showUpcastPerLevelField={showUpcastPerLevelField}
        showUpcastMaxLevelField={showUpcastMaxLevelField}
        showEffectScalingFields={showEffectScalingFields}
        showExtraEffectFields={showExtraEffectFields}
      />

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
