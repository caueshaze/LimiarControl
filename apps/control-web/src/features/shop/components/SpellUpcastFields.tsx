import { useMemo } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { Locale, LocaleKey } from "../../../shared/i18n";
import {
  localizeUpcastModeDescription,
  localizeUpcastModeExample,
  localizeSpellAdminValue,
} from "../../../shared/i18n/domainLabels";
import { SpellCatalogField } from "./SpellCatalogEditorControls";
import {
  SPELL_DICE_COUNT_OPTIONS,
  SPELL_DIE_SIZE_OPTIONS,
  SPELL_UPCAST_MODE_OPTIONS,
  type SpellCatalogEditorState,
} from "../utils/spellCatalogForm";
import {
  computeUpcastPreviewRows,
  computeUpcastValidationWarnings,
} from "../utils/upcastPreview";

type Props = {
  state: SpellCatalogEditorState;
  setState: Dispatch<SetStateAction<SpellCatalogEditorState>>;
  t: (key: LocaleKey) => string;
  locale: Locale;
  selectPlaceholder: string;
  showUpcastDiceField: boolean;
  showUpcastFlatField: boolean;
  showUpcastPerLevelField: boolean;
  showUpcastMaxLevelField: boolean;
  showBaseEffectInstances: boolean;
  showEffectScalingFields: boolean;
  showExtraEffectFields: boolean;
};

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

export const SpellUpcastFields = ({
  state,
  setState,
  t,
  locale,
  selectPlaceholder,
  showUpcastDiceField,
  showUpcastFlatField,
  showUpcastPerLevelField,
  showUpcastMaxLevelField,
  showBaseEffectInstances,
  showEffectScalingFields,
  showExtraEffectFields,
}: Props) => {
  const previewRows = useMemo(
    () =>
      computeUpcastPreviewRows({
        spellLevel: state.level,
        upcastMode: state.upcastMode,
        upcastDice:
          state.upcastDiceCount && state.upcastDieSize
            ? `${state.upcastDiceCount}d${state.upcastDieSize}${
                state.upcastFixedBonus ? `+${state.upcastFixedBonus}` : ""
              }`
            : null,
        upcastFlat: state.upcastFlat ? Number(state.upcastFlat) : null,
        perLevel: state.upcastPerLevel ? Number(state.upcastPerLevel) : 1,
        maxLevel: state.upcastMaxLevel ? Number(state.upcastMaxLevel) : null,
        baseEffectInstances: state.upcastBaseEffectInstances
          ? Number(state.upcastBaseEffectInstances)
          : null,
        baseDice: state.damageDice || state.healDice || null,
        baseMaxTargets: state.maxTargets ? Number(state.maxTargets) : null,
      }),
    [
      state.level,
      state.upcastMode,
      state.upcastDiceCount,
      state.upcastDieSize,
      state.upcastFixedBonus,
      state.upcastFlat,
      state.upcastPerLevel,
      state.upcastMaxLevel,
      state.upcastBaseEffectInstances,
      state.damageDice,
      state.healDice,
      state.maxTargets,
    ],
  );

  const warnings = useMemo(
    () =>
      computeUpcastValidationWarnings({
        resolutionType: state.resolutionType,
        upcastMode: state.upcastMode,
        upcastDiceCount: state.upcastDiceCount,
        upcastDieSize: state.upcastDieSize,
        upcastFlat: state.upcastFlat,
        upcastScalingKey: state.upcastScalingKey,
        upcastScalingSummary: state.upcastScalingSummary,
        upcastUnlockKey: state.upcastUnlockKey,
        upcastUnlockSummary: state.upcastUnlockSummary,
      }),
    [
      state.resolutionType,
      state.upcastMode,
      state.upcastDiceCount,
      state.upcastDieSize,
      state.upcastFlat,
      state.upcastScalingKey,
      state.upcastScalingSummary,
      state.upcastUnlockKey,
      state.upcastUnlockSummary,
    ],
  );

  const description =
    state.upcastMode && state.upcastMode in Object.fromEntries(SPELL_UPCAST_MODE_OPTIONS.map((m) => [m, m]))
      ? localizeUpcastModeDescription(state.upcastMode, locale)
      : "";
  const example =
    state.upcastMode
      ? localizeUpcastModeExample(state.upcastMode, locale)
      : "";

  return (
    <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
      <p className="text-xs leading-5 text-slate-400">
        {t("catalog.spells.form.upcastIntro")}
      </p>

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
      </div>

      {description ? (
        <p className="text-xs leading-5 text-slate-300">{description}</p>
      ) : null}
      {example ? (
        <p className="text-[11px] italic leading-5 text-slate-500">{example}</p>
      ) : null}

      {showUpcastDiceField ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <SpellCatalogField
            label={t("catalog.spells.form.upcastDiceCount")}
            help={t("catalog.spells.form.upcastDiceCountHelp")}
          >
            <select
              value={state.upcastDiceCount}
              onChange={(event) =>
                setState((current) => ({ ...current, upcastDiceCount: event.target.value }))
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
            label={t("catalog.spells.form.upcastDieSize")}
            help={t("catalog.spells.form.upcastDieSizeHelp")}
          >
            <select
              value={state.upcastDieSize}
              onChange={(event) =>
                setState((current) => ({ ...current, upcastDieSize: event.target.value }))
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
            label={t("catalog.spells.form.upcastFixedBonus")}
            help={t("catalog.spells.form.upcastFixedBonusHelp")}
          >
            <input
              type="number"
              step={1}
              value={state.upcastFixedBonus}
              onChange={(event) =>
                setState((current) => ({ ...current, upcastFixedBonus: event.target.value }))
              }
              className={fieldClassName}
              placeholder="0"
            />
          </SpellCatalogField>
        </div>
      ) : null}

      {showBaseEffectInstances ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <SpellCatalogField
            label={t("catalog.spells.form.baseEffectInstances")}
            help="Number of effect instances at the spell's base level. Ex.: Magic Missile has 3."
          >
            <input
              type="number"
              min={1}
              step={1}
              value={state.upcastBaseEffectInstances}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  upcastBaseEffectInstances: event.target.value,
                }))
              }
              className={fieldClassName}
              placeholder="3"
            />
          </SpellCatalogField>
        </div>
      ) : null}

      {showUpcastFlatField || showUpcastPerLevelField || showUpcastMaxLevelField ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {showUpcastFlatField ? (
            <SpellCatalogField
              label={t("catalog.spells.form.upcastFlat")}
              help={t("catalog.spells.form.upcastFlatHelp")}
            >
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
            <SpellCatalogField
              label={t("catalog.spells.form.upcastPerLevel")}
              help={t("catalog.spells.form.upcastPerLevelHelp")}
            >
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
            <SpellCatalogField
              label={t("catalog.spells.form.upcastMaxLevel")}
              help={t("catalog.spells.form.upcastMaxLevelHelp")}
            >
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
              placeholder={t("catalog.spells.form.armorClassBonus")}
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
              placeholder={t("catalog.spells.form.additionalBeam")}
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

      {warnings.length > 0 ? (
        <div className="rounded-xl border border-amber-300/15 bg-amber-400/10 px-4 py-3 space-y-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-200/90">
            {t("catalog.spells.form.upcastValidationTitle")}
          </p>
          {warnings.map((w) => (
            <p key={w.key} className="text-xs leading-5 text-amber-100">
              {t(w.key as LocaleKey)}
            </p>
          ))}
        </div>
      ) : null}

      {previewRows.length > 1 ? (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.spells.form.upcastPreviewTitle")}
          </p>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/5 text-left text-[10px] uppercase tracking-[0.18em] text-slate-500">
                <th className="pb-2 pr-4">{t("catalog.spells.form.upcastPreviewSlot")}</th>
                <th className="pb-2">{t("catalog.spells.form.upcastPreviewResult")}</th>
              </tr>
            </thead>
            <tbody>
              {previewRows.map((row) => (
                <tr
                  key={row.slotLevel}
                  className={row.isBase ? "text-slate-300" : "text-white"}
                >
                  <td className="py-1 pr-4 font-mono text-[11px]">
                    {row.isBase ? (
                      <span className="text-slate-400">{row.label}</span>
                    ) : (
                      row.label
                    )}
                  </td>
                  <td className="py-1 font-mono text-[11px]">{row.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
};
