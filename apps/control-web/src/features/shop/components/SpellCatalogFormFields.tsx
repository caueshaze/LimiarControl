import type { Dispatch, SetStateAction } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";
import {
  localizeDamageType,
  localizeSaveSuccessOutcome,
  localizeSpellAdminValue,
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
    SPELL_CASTING_TIME_TYPE_OPTIONS,
    SPELL_DAMAGE_TYPE_OPTIONS,
    SPELL_LEVEL_OPTIONS,
    SPELL_RESOLUTION_TYPE_OPTIONS,
    SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS,
    SPELL_SAVING_THROW_OPTIONS,
    SPELL_SCHOOL_OPTIONS,
    SPELL_TARGET_MODE_OPTIONS,
    SPELL_UPCAST_MODE_OPTIONS,
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
        <SpellCatalogField label={t("catalog.spells.form.targetMode")}>
          <select
            value={state.targetMode}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                targetMode: event.target.value as SpellCatalogEditorState["targetMode"],
              }))
            }
            className={fieldClassName}
          >
            <option value="">{selectPlaceholder}</option>
            {SPELL_TARGET_MODE_OPTIONS.map((targetMode) => (
              <option key={targetMode} value={targetMode}>
                {localizeSpellAdminValue(targetMode, locale)}
              </option>
            ))}
          </select>
        </SpellCatalogField>
      </div>

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

      <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("catalog.spells.form.targetingRequirements")}
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <SpellCatalogField label={t("catalog.spells.form.requiresTargetSight")}>
            <select
              value={booleanSelectValue(state.requiresTargetSight)}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  requiresTargetSight: parseBooleanSelectValue(event.target.value),
                }))
              }
              className={fieldClassName}
            >
              <option value="">{t("catalog.spells.form.inherit")}</option>
              <option value="true">{t("catalog.admin.table.yes")}</option>
              <option value="false">{t("catalog.admin.table.no")}</option>
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.requiresTargetEffect")}>
            <select
              value={booleanSelectValue(state.requiresTargetEffect)}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  requiresTargetEffect: parseBooleanSelectValue(event.target.value),
                }))
              }
              className={fieldClassName}
            >
              <option value="">{t("catalog.spells.form.inherit")}</option>
              <option value="true">{t("catalog.admin.table.yes")}</option>
              <option value="false">{t("catalog.admin.table.no")}</option>
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.requiresPointSight")}>
            <select
              value={booleanSelectValue(state.requiresPointSight)}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  requiresPointSight: parseBooleanSelectValue(event.target.value),
                }))
              }
              className={fieldClassName}
            >
              <option value="">{t("catalog.spells.form.inherit")}</option>
              <option value="true">{t("catalog.admin.table.yes")}</option>
              <option value="false">{t("catalog.admin.table.no")}</option>
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.requiresPointEffect")}>
            <select
              value={booleanSelectValue(state.requiresPointEffect)}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  requiresPointEffect: parseBooleanSelectValue(event.target.value),
                }))
              }
              className={fieldClassName}
            >
              <option value="">{t("catalog.spells.form.inherit")}</option>
              <option value="true">{t("catalog.admin.table.yes")}</option>
              <option value="false">{t("catalog.admin.table.no")}</option>
            </select>
          </SpellCatalogField>
        </div>
      </div>

      <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <SpellCatalogField label={t("catalog.spells.form.upcastMode")}>
            <select
              value={state.upcastMode}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  upcastMode: event.target.value as SpellCatalogEditorState["upcastMode"],
                }))
              }
              className={fieldClassName}
            >
              <option value="">{selectPlaceholder}</option>
              {SPELL_UPCAST_MODE_OPTIONS.map((upcastMode) => (
                <option key={upcastMode} value={upcastMode}>
                  {localizeSpellAdminValue(upcastMode, locale)}
                </option>
              ))}
            </select>
          </SpellCatalogField>
          {showUpcastDiceField ? (
            <SpellCatalogField label={t("catalog.spells.form.upcastDice")}>
              <input
                value={state.upcastDice}
                onChange={(event) =>
                  setState((current) => ({ ...current, upcastDice: event.target.value }))
                }
                className={fieldClassName}
                placeholder="1d6"
              />
            </SpellCatalogField>
          ) : null}
        </div>

        {showUpcastFlatField || showUpcastPerLevelField || showUpcastMaxLevelField ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {showUpcastFlatField ? (
              <SpellCatalogField label={t("catalog.spells.form.upcastFlat")}>
                <input
                  type="number"
                  min={0}
                  value={state.upcastFlat}
                  onChange={(event) =>
                    setState((current) => ({ ...current, upcastFlat: event.target.value }))
                  }
                  className={fieldClassName}
                  placeholder="1"
                />
              </SpellCatalogField>
            ) : null}
            {showUpcastPerLevelField ? (
              <SpellCatalogField label={t("catalog.spells.form.upcastPerLevel")}>
                <input
                  type="number"
                  min={1}
                  value={state.upcastPerLevel}
                  onChange={(event) =>
                    setState((current) => ({ ...current, upcastPerLevel: event.target.value }))
                  }
                  className={fieldClassName}
                  placeholder="1"
                />
              </SpellCatalogField>
            ) : null}
            {showUpcastMaxLevelField ? (
              <SpellCatalogField label={t("catalog.spells.form.upcastMaxLevel")}>
                <input
                  type="number"
                  min={1}
                  max={9}
                  value={state.upcastMaxLevel}
                  onChange={(event) =>
                    setState((current) => ({ ...current, upcastMaxLevel: event.target.value }))
                  }
                  className={fieldClassName}
                  placeholder="9"
                />
              </SpellCatalogField>
            ) : null}
          </div>
        ) : null}

        {showEffectScalingFields ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <SpellCatalogField label={t("catalog.spells.form.upcastScalingKey")}>
              <input
                value={state.upcastScalingKey}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    upcastScalingKey: event.target.value,
                  }))
                }
                className={fieldClassName}
                placeholder="armor_class_bonus"
              />
            </SpellCatalogField>
            <SpellCatalogField label={t("catalog.spells.form.upcastScalingSummary")}>
              <input
                value={state.upcastScalingSummary}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    upcastScalingSummary: event.target.value,
                  }))
                }
                className={fieldClassName}
              />
            </SpellCatalogField>
            <SpellCatalogField label={t("catalog.spells.form.upcastScalingEditorial")}>
              <input
                value={state.upcastScalingEditorial}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    upcastScalingEditorial: event.target.value,
                  }))
                }
                className={fieldClassName}
              />
            </SpellCatalogField>
          </div>
        ) : null}

        {showExtraEffectFields ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <SpellCatalogField label={t("catalog.spells.form.upcastUnlockKey")}>
              <input
                value={state.upcastUnlockKey}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    upcastUnlockKey: event.target.value,
                  }))
                }
                className={fieldClassName}
                placeholder="additional_beam"
              />
            </SpellCatalogField>
            <SpellCatalogField label={t("catalog.spells.form.upcastUnlockSummary")}>
              <input
                value={state.upcastUnlockSummary}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    upcastUnlockSummary: event.target.value,
                  }))
                }
                className={fieldClassName}
              />
            </SpellCatalogField>
            <SpellCatalogField label={t("catalog.spells.form.upcastUnlockEditorial")}>
              <input
                value={state.upcastUnlockEditorial}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    upcastUnlockEditorial: event.target.value,
                  }))
                }
                className={fieldClassName}
              />
            </SpellCatalogField>
          </div>
        ) : null}
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
