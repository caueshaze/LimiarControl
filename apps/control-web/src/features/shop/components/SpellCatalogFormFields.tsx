import type { Dispatch, SetStateAction } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import { SpellAoeFootprintPreview } from "../../../pages/SystemSpellCatalogPage/SpellAoeFootprintPreview";
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
import { SpellCantripScalingFields } from "./SpellCantripScalingFields";
import { SpellCatalogResolutionFields } from "./SpellCatalogResolutionFields";
import { SpellCatalogTargetingRequirements } from "./SpellCatalogTargetingRequirements";
import { SpellCatalogDeclarativeEffectsFields } from "./SpellCatalogDeclarativeEffectsFields";
import {
    SPELL_CLASS_OPTIONS,
    SPELL_COMPONENT_OPTIONS,
    SPELL_CASTING_TIME_TYPE_OPTIONS,
    SPELL_LEVEL_OPTIONS,
    SPELL_SCHOOL_OPTIONS,
    SPELL_AREA_SHAPE_OPTIONS,
    SPELL_ATTACK_TYPE_OPTIONS,
    SPELL_TARGET_TYPE_OPTIONS,
    SPELL_EFFECT_TIMING_OPTIONS,
    SPELL_ORIGIN_TYPE_OPTIONS,
    SPELL_RANGE_KIND_OPTIONS,
    SPELL_SELECTION_TYPE_OPTIONS,
    SPELL_TARGET_ANCHOR_OPTIONS,
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

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
      {title}
    </p>
    <div className="space-y-4">{children}</div>
  </div>
);

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
    state.upcastMode === "extra_heal_dice" ||
    state.upcastMode === "additional_effect_instances";
  const showUpcastFlatField = state.upcastMode === "flat_bonus";
  const showUpcastPerLevelField = Boolean(state.upcastMode);
  const showUpcastMaxLevelField = Boolean(state.upcastMode);
  const showEffectScalingFields = state.upcastMode === "effect_scaling";
  const showExtraEffectFields = state.upcastMode === "extra_effect";
  const showBaseEffectInstances = state.upcastMode === "additional_effect_instances";
  const showRadiusField = state.areaShape === "sphere" || state.areaShape === "cylinder";
  const showLengthField = state.areaShape === "cone" || state.areaShape === "line";
  const showSideField = state.areaShape === "cube";

  return (
    <div className="space-y-5">
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

      <Section title={t("catalog.spells.form.classes")}>
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
      </Section>

      <Section title={t("catalog.spells.castingTime")}>
        <div className="grid gap-4 sm:grid-cols-2">
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
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
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
          <SpellCatalogField label={t("catalog.spells.form.maxTargets")}>
            <input
              type="number"
              min={1}
              step={1}
              value={state.maxTargets}
              onChange={(event) =>
                setState((current) => ({ ...current, maxTargets: event.target.value }))
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
      </Section>

      <Section title="Componentes">
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
      </Section>

      <Section title="Propriedades">
        <div className="flex flex-wrap gap-3">
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
      </Section>

      <Section title="Targeting">
        <div className="grid gap-4 sm:grid-cols-3">
          <SpellCatalogField label={t("catalog.spells.form.selectionType")}>
            <select
              value={state.selectionType}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  selectionType: event.target.value as SpellCatalogEditorState["selectionType"],
                }))
              }
              className={fieldClassName}
            >
              <option value="">{selectPlaceholder}</option>
              {SPELL_SELECTION_TYPE_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {localizeSpellAdminValue(value, locale)}
                </option>
              ))}
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.originType")}>
            <select
              value={state.originType}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  originType: event.target.value as SpellCatalogEditorState["originType"],
                }))
              }
              className={fieldClassName}
            >
              <option value="">{selectPlaceholder}</option>
              {SPELL_ORIGIN_TYPE_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {localizeSpellAdminValue(value, locale)}
                </option>
              ))}
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.targetAnchor")}>
            <select
              value={state.targetAnchor}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  targetAnchor: event.target.value as SpellCatalogEditorState["targetAnchor"],
                }))
              }
              className={fieldClassName}
            >
              <option value="">{selectPlaceholder}</option>
              {SPELL_TARGET_ANCHOR_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {localizeSpellAdminValue(value, locale)}
                </option>
              ))}
            </select>
          </SpellCatalogField>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <SpellCatalogField label={t("catalog.spells.form.attackType")}>
            <select
              value={state.attackType}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  attackType: event.target.value as SpellCatalogEditorState["attackType"],
                }))
              }
              className={fieldClassName}
            >
              <option value="">{selectPlaceholder}</option>
              {SPELL_ATTACK_TYPE_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {localizeSpellAdminValue(value, locale)}
                </option>
              ))}
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.rangeKind")}>
            <select
              value={state.rangeKind}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  rangeKind: event.target.value as SpellCatalogEditorState["rangeKind"],
                }))
              }
              className={fieldClassName}
            >
              <option value="">{selectPlaceholder}</option>
              {SPELL_RANGE_KIND_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {localizeSpellAdminValue(value, locale)}
                </option>
              ))}
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.effectTiming")}>
            <select
              value={state.effectTiming}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  effectTiming: event.target.value as SpellCatalogEditorState["effectTiming"],
                }))
              }
              className={fieldClassName}
            >
              <option value="">{selectPlaceholder}</option>
              {SPELL_EFFECT_TIMING_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {localizeSpellAdminValue(value, locale)}
                </option>
              ))}
            </select>
          </SpellCatalogField>
        </div>

        <SpellCatalogField label={t("catalog.spells.rangeText")}>
          <input
            value={state.rangeText}
            onChange={(event) =>
              setState((current) => ({ ...current, rangeText: event.target.value }))
            }
            className={fieldClassName}
          />
        </SpellCatalogField>
      </Section>

      <Section title="Área">
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

        {(showRadiusField || showLengthField || showSideField) ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {showRadiusField && (
              <SpellCatalogField label={t("catalog.spells.form.radiusMeters")}>
                <input
                  type="number"
                  min={0.5}
                  step={0.5}
                  value={state.radiusMeters}
                  onChange={(event) =>
                    setState((current) => ({ ...current, radiusMeters: event.target.value }))
                  }
                  className={fieldClassName}
                />
              </SpellCatalogField>
            )}
            {showLengthField && (
              <SpellCatalogField label={t("catalog.spells.form.lengthMeters")}>
                <input
                  type="number"
                  min={0.5}
                  step={0.5}
                  value={state.lengthMeters}
                  onChange={(event) =>
                    setState((current) => ({ ...current, lengthMeters: event.target.value }))
                  }
                  className={fieldClassName}
                />
              </SpellCatalogField>
            )}
            {showSideField && (
              <SpellCatalogField label={t("catalog.spells.form.sideMeters")}>
                <input
                  type="number"
                  min={0.5}
                  step={0.5}
                  value={state.sideMeters}
                  onChange={(event) =>
                    setState((current) => ({ ...current, sideMeters: event.target.value }))
                  }
                  className={fieldClassName}
                />
              </SpellCatalogField>
            )}
          </div>
        ) : null}

        <SpellAoeFootprintPreview
          areaShape={state.areaShape}
          radiusMeters={state.radiusMeters}
          lengthMeters={state.lengthMeters}
          sideMeters={state.sideMeters}
        />
      </Section>

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

      <SpellCatalogDeclarativeEffectsFields
        state={state}
        setState={setState}
      />

      <SpellCatalogTargetingRequirements
        state={state}
        setState={setState}
        t={t}
        booleanSelectValue={booleanSelectValue}
        parseBooleanSelectValue={parseBooleanSelectValue}
      />

      {state.level > 0 ? (
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
          showBaseEffectInstances={showBaseEffectInstances}
          showEffectScalingFields={showEffectScalingFields}
          showExtraEffectFields={showExtraEffectFields}
        />
      ) : (
        <SpellCantripScalingFields
          state={state}
          setState={setState}
          t={t}
          selectPlaceholder={selectPlaceholder}
        />
      )}

      <Section title="Descrição">
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
      </Section>
    </div>
  );
};
