import type { Dispatch, SetStateAction } from "react";
import type { Locale, LocaleKey } from "../../../shared/i18n";
import { localizeSpellAdminValue } from "../../../shared/i18n/domainLabels";
import { SpellCatalogField } from "./SpellCatalogEditorControls";
import {
    SPELL_DICE_COUNT_OPTIONS,
    SPELL_DIE_SIZE_OPTIONS,
    SPELL_UPCAST_MODE_OPTIONS,
    type SpellCatalogEditorState,
} from "../utils/spellCatalogForm";

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
  showEffectScalingFields,
  showExtraEffectFields,
}: Props) => (
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
    </div>

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
  </div>
);
