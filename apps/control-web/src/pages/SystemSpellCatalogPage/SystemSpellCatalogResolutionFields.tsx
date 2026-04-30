import type { Dispatch, SetStateAction } from "react";
import { useMemo } from "react";

import { SpellCatalogDeclarativeEffectsFields } from "../../features/shop/components/SpellCatalogDeclarativeEffectsFields";
import type {
  ResolutionType,
  SaveSuccessOutcome,
  SpellDamageType,
  SpellSavingThrow,
  UpcastMode,
} from "../../entities/base-spell";
import { useLocale } from "../../shared/hooks/useLocale";
import type { LocaleKey } from "../../shared/i18n";
import {
  localizeSaveSuccessOutcome,
  localizeSpellAdminValue,
  localizeSpellSavingThrow,
  localizeUpcastModeDescription,
  localizeUpcastModeExample,
} from "../../shared/i18n/domainLabels";
import { SystemSpellCatalogFormSection } from "./SystemSpellCatalogFormSection";
import {
  COVER_APPLIES_TO_SAVE_OPTIONS,
  DAMAGE_TYPE_OPTIONS,
  DICE_COUNT_OPTIONS,
  DIE_SIZE_OPTIONS,
  type FormState,
  RESOLUTION_TYPE_OPTIONS,
  SAVE_SUCCESS_OUTCOME_OPTIONS,
  SAVING_THROW_OPTIONS,
  UPCAST_MODE_OPTIONS,
  inputClassName,
} from "./systemSpellCatalog.types";
import {
  computeUpcastPreviewRows,
  computeUpcastValidationWarnings,
} from "../../features/shop/utils/upcastPreview";

type Props = {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
};

const FieldHelpIcon = ({ text }: { text: string }) => (
  <span className="group relative inline-flex" tabIndex={0} aria-label={text}>
    <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-500/60 text-[10px] font-bold leading-none text-slate-400 transition group-hover:border-violet-300/70 group-hover:text-violet-100 group-focus-visible:border-violet-300/70 group-focus-visible:text-violet-100">
      i
    </span>
    <span className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 hidden w-56 -translate-x-1/2 rounded-md border border-white/10 bg-slate-950 px-3 py-2 text-[11px] normal-case leading-5 text-slate-100 shadow-xl group-hover:block group-focus-visible:block">
      {text}
    </span>
  </span>
);

const SystemUpcastValidationAndPreview = ({
  form,
  locale,
  t,
}: {
  form: FormState;
  locale: string;
  t: (key: LocaleKey) => string;
}) => {
  const warnings = useMemo(
    () =>
      computeUpcastValidationWarnings({
        resolutionType: form.resolutionType,
        upcastMode: form.upcastMode,
        upcastDiceCount: form.upcastDiceCount,
        upcastDieSize: form.upcastDieSize,
        upcastFlat: form.upcastFlat,
        upcastScalingKey: form.upcastScalingKey,
        upcastScalingSummary: form.upcastScalingSummary,
        upcastUnlockKey: form.upcastUnlockKey,
        upcastUnlockSummary: form.upcastUnlockSummary,
      }),
    [
      form.resolutionType,
      form.upcastMode,
      form.upcastDiceCount,
      form.upcastDieSize,
      form.upcastFlat,
      form.upcastScalingKey,
      form.upcastScalingSummary,
      form.upcastUnlockKey,
      form.upcastUnlockSummary,
    ],
  );

  const previewRows = useMemo(
    () =>
      computeUpcastPreviewRows({
        spellLevel: form.level,
        upcastMode: form.upcastMode,
        upcastDice:
          form.upcastDiceCount && form.upcastDieSize
            ? `${form.upcastDiceCount}d${form.upcastDieSize}${
                form.upcastFixedBonus ? `+${form.upcastFixedBonus}` : ""
              }`
            : null,
        upcastFlat: form.upcastFlat ? Number(form.upcastFlat) : null,
        perLevel: form.upcastPerLevel ? Number(form.upcastPerLevel) : 1,
        maxLevel: form.upcastMaxLevel ? Number(form.upcastMaxLevel) : null,
        baseEffectInstances: form.upcastBaseEffectInstances
          ? Number(form.upcastBaseEffectInstances)
          : null,
        baseDice: form.damageDice || form.healDice || null,
        baseMaxTargets: form.maxTargets ? Number(form.maxTargets) : null,
      }),
    [
      form.level,
      form.upcastMode,
      form.upcastDiceCount,
      form.upcastDieSize,
      form.upcastFixedBonus,
      form.upcastFlat,
      form.upcastPerLevel,
      form.upcastMaxLevel,
      form.upcastBaseEffectInstances,
      form.damageDice,
      form.healDice,
      form.maxTargets,
    ],
  );

  if (!form.upcastMode || warnings.length === 0 && previewRows.length <= 1) return null;

  return (
    <>
      {warnings.length > 0 ? (
        <div className="rounded-xl border border-amber-300/15 bg-amber-400/10 px-4 py-3 space-y-1 mt-3">
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
        <div className="space-y-2 mt-3">
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
    </>
  );
};

export const SystemSpellCatalogResolutionFields = ({ form, setForm }: Props) => {
  const { locale, t } = useLocale();

  const formatSpellChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeSpellAdminValue(value, locale);

  const showSavingThrowFields =
    form.resolutionType === "damage" ||
    form.resolutionType === "control" ||
    form.resolutionType === "debuff";
  const showSaveSuccessOutcome =
    form.resolutionType === "damage" && Boolean(form.savingThrow);
  const showDamageFields = form.resolutionType === "damage";
  const showHealFields = form.resolutionType === "heal";
  const showUpcastDiceField =
    form.upcastMode === "extra_damage_dice" ||
    form.upcastMode === "extra_heal_dice" ||
    form.upcastMode === "additional_effect_instances";
  const showUpcastFlatField = form.upcastMode === "flat_bonus";
  const showUpcastPerLevelField = Boolean(form.upcastMode);
  const showUpcastMaxLevelField = Boolean(form.upcastMode);
  const showEffectScalingFields = form.upcastMode === "effect_scaling";
  const showExtraEffectFields = form.upcastMode === "extra_effect";
  const showBaseEffectInstances = form.upcastMode === "additional_effect_instances";

  return (
    <>
      <SystemSpellCatalogFormSection title="Resolução">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.resolutionTypeDetailed")}
            </span>
            <select
              value={form.resolutionType}
              onChange={(event) =>
                setForm((c) => ({
                  ...c,
                  resolutionType: event.target.value as ResolutionType | "",
                }))
              }
              className={`${inputClassName} mt-2`}
            >
              <option value="">—</option>
              {RESOLUTION_TYPE_OPTIONS.map((rt) => (
                <option key={rt} value={rt}>
                  {formatSpellChoiceLabel(rt)}
                </option>
              ))}
            </select>
          </label>

          {showSavingThrowFields && (
            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.spells.form.savingThrowAbility")}
              </span>
              <select
                value={form.savingThrow}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    savingThrow: event.target.value as SpellSavingThrow | "",
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {SAVING_THROW_OPTIONS.map((st) => (
                  <option key={st} value={st}>
                    {localizeSpellSavingThrow(st, locale)}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        {showSaveSuccessOutcome && (
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.spells.form.saveSuccessOutcome")}
              </span>
              <select
                value={form.saveSuccessOutcome}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    saveSuccessOutcome: event.target.value as SaveSuccessOutcome | "",
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {SAVE_SUCCESS_OUTCOME_OPTIONS.map((outcome) => (
                  <option key={outcome} value={outcome}>
                    {localizeSaveSuccessOutcome(outcome, locale)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block min-w-0">
              <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                <span>{t("catalog.spells.form.coverAppliesToSaveDetailed")}</span>
                <FieldHelpIcon text="Se cover físico aplica à saving throw. &quot;physical&quot; = alvo com cover recebe bônus. &quot;none&quot; = cover não aplica." />
              </span>
              <select
                value={form.coverAppliesToSave}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    coverAppliesToSave: event.target.value as FormState["coverAppliesToSave"],
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {COVER_APPLIES_TO_SAVE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}

        {showSavingThrowFields && !showSaveSuccessOutcome && (
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block min-w-0">
              <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                <span>{t("catalog.spells.form.coverAppliesToSaveDetailed")}</span>
                <FieldHelpIcon text="Se cover físico aplica à saving throw. &quot;physical&quot; = alvo com cover recebe bônus. &quot;none&quot; = cover não aplica." />
              </span>
              <select
                value={form.coverAppliesToSave}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    coverAppliesToSave: event.target.value as FormState["coverAppliesToSave"],
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {COVER_APPLIES_TO_SAVE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </SystemSpellCatalogFormSection>

      {showDamageFields && (
        <SystemSpellCatalogFormSection title="Dano">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="block min-w-0">
              <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                <span>{t("catalog.spells.form.damageDiceCount")}</span>
                <FieldHelpIcon text="Quantidade de dados do efeito base. Ex.: 3 em 3d4+3." />
              </span>
              <select
                value={form.damageDiceCount}
                onChange={(event) =>
                  setForm((c) => ({ ...c, damageDiceCount: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {DICE_COUNT_OPTIONS.map((count) => (
                  <option key={count} value={count}>
                    {count}
                  </option>
                ))}
              </select>
            </label>

            <label className="block min-w-0">
              <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                <span>{t("catalog.spells.form.damageDie")}</span>
                <FieldHelpIcon text="Tipo do dado do efeito base. Ex.: d4." />
              </span>
              <select
                value={form.damageDieSize}
                onChange={(event) =>
                  setForm((c) => ({ ...c, damageDieSize: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {DIE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    d{size}
                  </option>
                ))}
              </select>
            </label>

            <label className="block min-w-0">
              <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                <span>{t("catalog.spells.form.damageFixedBonus")}</span>
                <FieldHelpIcon text="Bônus fixo somado ao efeito base. Ex.: +3 em 3d4+3." />
              </span>
              <input
                type="number"
                step={1}
                value={form.damageFixedBonus}
                onChange={(event) =>
                  setForm((c) => ({ ...c, damageFixedBonus: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="0"
              />
            </label>

            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.admin.table.damageType")}
              </span>
              <select
                value={form.damageType}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    damageType: event.target.value as SpellDamageType | "",
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {DAMAGE_TYPE_OPTIONS.map((dt) => (
                  <option key={dt} value={dt}>
                    {dt}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </SystemSpellCatalogFormSection>
      )}

      {showHealFields && (
        <SystemSpellCatalogFormSection title="Cura">
          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.healDiceDetailed")}
            </span>
            <input
              value={form.healDice}
              onChange={(event) =>
                setForm((c) => ({ ...c, healDice: event.target.value }))
              }
              className={`${inputClassName} mt-2`}
              placeholder="1d8"
            />
          </label>
        </SystemSpellCatalogFormSection>
      )}

      {form.level > 0 && (
        <SystemSpellCatalogFormSection
          title={t("catalog.spells.form.upcast")}
          collapsible
        >
          <p className="text-xs leading-5 text-slate-400 mb-2">
            {t("catalog.spells.form.upcastIntro")}
          </p>

          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.upcastModeDetailed")}
            </span>
            <select
              value={form.upcastMode}
              onChange={(event) =>
                setForm((c) => ({
                  ...c,
                  upcastMode: event.target.value as UpcastMode | "",
                }))
              }
              className={`${inputClassName} mt-2`}
            >
              <option value="">—</option>
              {UPCAST_MODE_OPTIONS.map((um) => (
                <option key={um} value={um}>
                  {formatSpellChoiceLabel(um)}
                </option>
              ))}
            </select>
          </label>

          {form.upcastMode ? (
            <>
              <p className="text-xs leading-5 text-slate-300 mt-2">
                {localizeUpcastModeDescription(form.upcastMode, locale)}
              </p>
              {localizeUpcastModeExample(form.upcastMode, locale) ? (
                <p className="text-[11px] italic leading-5 text-slate-500">
                  {localizeUpcastModeExample(form.upcastMode, locale)}
                </p>
              ) : null}
            </>
          ) : null}

          {showUpcastDiceField && (
            <div className="grid gap-4 md:grid-cols-3">
              <label className="block min-w-0">
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  <span>{t("catalog.spells.form.upcastDiceCount")}</span>
                  <FieldHelpIcon text="Dados por incremento ou instância extra. Ex.: 1 em 1d4+1." />
                </span>
                <select
                  value={form.upcastDiceCount}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, upcastDiceCount: event.target.value }))
                  }
                  className={`${inputClassName} mt-2`}
                >
                  <option value="">—</option>
                  {DICE_COUNT_OPTIONS.map((count) => (
                    <option key={count} value={count}>
                      {count}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block min-w-0">
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  <span>{t("catalog.spells.form.upcastDie")}</span>
                  <FieldHelpIcon text="Dado do incremento de upcast. Ex.: d4." />
                </span>
                <select
                  value={form.upcastDieSize}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, upcastDieSize: event.target.value }))
                  }
                  className={`${inputClassName} mt-2`}
                >
                  <option value="">—</option>
                  {DIE_SIZE_OPTIONS.map((size) => (
                    <option key={size} value={size}>
                      d{size}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block min-w-0">
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  <span>{t("catalog.spells.form.upcastFixedBonus")}</span>
                  <FieldHelpIcon text="Bônus por incremento. Ex.: +1 por míssil extra." />
                </span>
                <input
                  type="number"
                  step={1}
                  value={form.upcastFixedBonus}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, upcastFixedBonus: event.target.value }))
                  }
                  className={`${inputClassName} mt-2`}
                  placeholder="0"
                />
              </label>
            </div>
          )}

          {showBaseEffectInstances && (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block min-w-0">
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  <span>{t("catalog.spells.form.baseEffectInstances")}</span>
                  <FieldHelpIcon text="Número de instâncias no nível base da magia. Ex.: Magic Missile tem 3." />
                </span>
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={form.upcastBaseEffectInstances}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, upcastBaseEffectInstances: event.target.value }))
                  }
                  className={`${inputClassName} mt-2`}
                  placeholder="3"
                />
              </label>
            </div>
          )}

          {(showUpcastFlatField || showUpcastPerLevelField || showUpcastMaxLevelField) && (
            <div className="grid gap-4 md:grid-cols-3">
              {showUpcastFlatField ? (
                <label className="block min-w-0">
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    <span>{t("catalog.spells.form.upcastFlatDetailed")}</span>
                    <FieldHelpIcon text="Bônus fixo sem dado; use para escalas numéricas simples." />
                  </span>
                  <input
                    value={form.upcastFlat}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, upcastFlat: event.target.value }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder="1"
                  />
                </label>
              ) : null}

              {showUpcastPerLevelField ? (
                <label className="block min-w-0">
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    <span>{t("catalog.spells.form.upcastPerLevelDetailed")}</span>
                    <FieldHelpIcon text="Incrementos por slot acima do nível base. Normalmente 1." />
                  </span>
                  <input
                    value={form.upcastPerLevel}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, upcastPerLevel: event.target.value }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder="1"
                  />
                </label>
              ) : null}

              {showUpcastMaxLevelField ? (
                <label className="block min-w-0">
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    <span>{t("catalog.spells.form.upcastMaxLevelDetailed")}</span>
                    <FieldHelpIcon text="Limite de escala; vazio usa qualquer slot válido." />
                  </span>
                  <input
                    value={form.upcastMaxLevel}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, upcastMaxLevel: event.target.value }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder="9"
                  />
                </label>
              ) : null}
            </div>
          )}

          {showEffectScalingFields && (
            <div className="rounded-2xl border border-amber-400/20 bg-amber-400/5 p-4 space-y-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-400/70">
                {t("catalog.spells.form.effectScalingTitle")}
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block min-w-0">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    {t("catalog.spells.form.scalingKey")} <span className="text-red-400">*</span>
                  </span>
                  <input
                    value={form.upcastScalingKey}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, upcastScalingKey: event.target.value }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder={t("catalog.spells.form.armorClassBonus")}
                  />
                </label>
                <label className="block min-w-0">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    {t("catalog.spells.form.scalingSummary")} <span className="text-red-400">*</span>
                  </span>
                  <input
                    value={form.upcastScalingSummary}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, upcastScalingSummary: event.target.value }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder={t("catalog.spells.form.acScalingExample")}
                  />
                </label>
              </div>
              <label className="block min-w-0">
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  {t("catalog.spells.form.scalingEditorial")}
                </span>
                <input
                  value={form.upcastScalingEditorial}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, upcastScalingEditorial: event.target.value }))
                  }
                  className={`${inputClassName} mt-2`}
                  placeholder={t("catalog.spells.form.scalingEditorialNote")}
                />
              </label>
            </div>
          )}

          {showExtraEffectFields && (
            <div className="rounded-2xl border border-violet-400/20 bg-violet-400/5 p-4 space-y-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-400/70">
                {t("catalog.spells.form.extraEffectTitle")}
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block min-w-0">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    {t("catalog.spells.form.unlockKey")} <span className="text-red-400">*</span>
                  </span>
                  <input
                    value={form.upcastUnlockKey}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, upcastUnlockKey: event.target.value }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder={t("catalog.spells.form.additionalBeam")}
                  />
                </label>
                <label className="block min-w-0">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    {t("catalog.spells.form.unlockSummary")} <span className="text-red-400">*</span>
                  </span>
                  <input
                    value={form.upcastUnlockSummary}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, upcastUnlockSummary: event.target.value }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder={t("catalog.spells.form.beamScalingExample")}
                  />
                </label>
              </div>
              <label className="block min-w-0">
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  {t("catalog.spells.form.unlockEditorial")}
                </span>
                <input
                  value={form.upcastUnlockEditorial}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, upcastUnlockEditorial: event.target.value }))
                  }
                  className={`${inputClassName} mt-2`}
                  placeholder={t("catalog.spells.form.unlockEditorialNote")}
                />
              </label>
            </div>
          )}

          <SystemUpcastValidationAndPreview form={form} locale={locale} t={t} />
        </SystemSpellCatalogFormSection>
      )}

      {form.level === 0 && (
        <SystemSpellCatalogFormSection
          title={t("catalog.spells.form.cantripScaling")}
          collapsible
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.spells.form.scalingMode")}
              </span>
              <select
                value={form.cantripScalingMode}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    cantripScalingMode: event.target.value as FormState["cantripScalingMode"],
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                <option value="character_level">{t("catalog.spells.form.characterLevel")}</option>
              </select>
            </label>
          </div>
          {form.cantripScalingMode === "character_level" ? (
            <div className="space-y-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.spells.form.characterLevelThresholds")}
              </p>
              {[
                [1, "cantripLevel1DiceCount", "cantripLevel1DieSize", "cantripLevel1FixedBonus"],
                [5, "cantripLevel5DiceCount", "cantripLevel5DieSize", "cantripLevel5FixedBonus"],
                [11, "cantripLevel11DiceCount", "cantripLevel11DieSize", "cantripLevel11FixedBonus"],
                [17, "cantripLevel17DiceCount", "cantripLevel17DieSize", "cantripLevel17FixedBonus"],
              ].map(([level, countKey, dieKey, bonusKey]) => (
                <div key={level} className="grid gap-4 md:grid-cols-[80px_1fr_1fr_1fr]">
                  <div className="flex items-end pb-3 text-xs font-semibold text-slate-300">
                    Nível {level}
                  </div>
                  <label className="block min-w-0">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                      {t("catalog.spells.form.damageDiceCount")}
                    </span>
                    <select
                      value={form[countKey as keyof FormState] as string}
                      onChange={(event) =>
                        setForm((c) => ({ ...c, [countKey as string]: event.target.value }))
                      }
                      className={`${inputClassName} mt-2`}
                    >
                      <option value="">—</option>
                      {DICE_COUNT_OPTIONS.map((count) => (
                        <option key={count} value={count}>
                          {count}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block min-w-0">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                      {t("catalog.spells.form.damageDie")}
                    </span>
                    <select
                      value={form[dieKey as keyof FormState] as string}
                      onChange={(event) =>
                        setForm((c) => ({ ...c, [dieKey as string]: event.target.value }))
                      }
                      className={`${inputClassName} mt-2`}
                    >
                      <option value="">—</option>
                      {DIE_SIZE_OPTIONS.map((size) => (
                        <option key={size} value={size}>
                          d{size}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block min-w-0">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                      {t("catalog.spells.form.damageFixedBonus")}
                    </span>
                    <input
                      type="number"
                      step={1}
                      value={form[bonusKey as keyof FormState] as string}
                      onChange={(event) =>
                        setForm((c) => ({ ...c, [bonusKey as string]: event.target.value }))
                      }
                      className={`${inputClassName} mt-2`}
                      placeholder="0"
                    />
                  </label>
                </div>
              ))}
            </div>
          ) : null}
        </SystemSpellCatalogFormSection>
      )}

      {form.resolutionType === "buff" && (
        <SpellCatalogDeclarativeEffectsFields
          state={form}
          setState={setForm}
        />
      )}
    </>
  );
};
