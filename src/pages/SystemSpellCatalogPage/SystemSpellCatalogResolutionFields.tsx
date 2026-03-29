import type { Dispatch, SetStateAction } from "react";

import type {
  ResolutionType,
  SaveSuccessOutcome,
  SpellDamageType,
  SpellSavingThrow,
  UpcastMode,
} from "../../entities/base-spell";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  localizeSaveSuccessOutcome,
  localizeSpellAdminValue,
} from "../../shared/i18n/domainLabels";
import {
  DAMAGE_TYPE_OPTIONS,
  type FormState,
  RESOLUTION_TYPE_OPTIONS,
  SAVE_SUCCESS_OUTCOME_OPTIONS,
  SAVING_THROW_OPTIONS,
  UPCAST_MODE_OPTIONS,
  inputClassName,
} from "./systemSpellCatalog.types";

type Props = {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
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
    form.upcastMode === "extra_heal_dice";
  const showUpcastFlatField =
    form.upcastMode === "extra_damage_dice" ||
    form.upcastMode === "extra_heal_dice" ||
    form.upcastMode === "flat_bonus";
  const showUpcastPerLevelField = Boolean(form.upcastMode);
  const showUpcastMaxLevelField = Boolean(form.upcastMode);
  const showEffectScalingFields = form.upcastMode === "effect_scaling";
  const showExtraEffectFields = form.upcastMode === "extra_effect";

  return (
    <>
      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Resolution type
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
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Saving throw ability
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
                  {st}
                </option>
              ))}
            </select>
          </label>
        )}

        {showSaveSuccessOutcome && (
          <label className="block">
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
        )}
      </div>

      {showDamageFields && (
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Damage dice
            </span>
            <input
              value={form.damageDice}
              onChange={(event) =>
                setForm((c) => ({ ...c, damageDice: event.target.value }))
              }
              className={`${inputClassName} mt-2`}
              placeholder="8d6"
            />
          </label>

          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Damage type
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
      )}

      {showHealFields && (
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Heal dice
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
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Upcast mode
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

        {showUpcastDiceField ? (
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Upcast dice
            </span>
            <input
              value={form.upcastDice}
              onChange={(event) =>
                setForm((c) => ({ ...c, upcastDice: event.target.value }))
              }
              className={`${inputClassName} mt-2`}
              placeholder="1d6"
            />
          </label>
        ) : null}
      </div>

      {(showUpcastFlatField || showUpcastPerLevelField || showUpcastMaxLevelField) ? (
        <div className="grid gap-4 md:grid-cols-3">
          {showUpcastFlatField ? (
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Upcast flat
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
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Upcast por nível
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
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Nível máximo do slot
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
      ) : null}

      {showEffectScalingFields && (
        <div className="rounded-2xl border border-amber-400/20 bg-amber-400/5 p-4 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-400/70">
            Effect scaling — o que escala ao upcasting
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Scaling key <span className="text-red-400">*</span>
              </span>
              <input
                value={form.upcastScalingKey}
                onChange={(event) =>
                  setForm((c) => ({ ...c, upcastScalingKey: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="armor_class_bonus"
              />
            </label>
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Scaling summary <span className="text-red-400">*</span>
              </span>
              <input
                value={form.upcastScalingSummary}
                onChange={(event) =>
                  setForm((c) => ({ ...c, upcastScalingSummary: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="+1 to AC per slot level above 1st"
              />
            </label>
          </div>
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Scaling editorial
            </span>
            <input
              value={form.upcastScalingEditorial}
              onChange={(event) =>
                setForm((c) => ({ ...c, upcastScalingEditorial: event.target.value }))
              }
              className={`${inputClassName} mt-2`}
              placeholder="Optional editorial note about the scaling behavior"
            />
          </label>
        </div>
      )}

      {showExtraEffectFields && (
        <div className="rounded-2xl border border-violet-400/20 bg-violet-400/5 p-4 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-400/70">
            Extra effect — o que é destravado ao upcasting
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Unlock key <span className="text-red-400">*</span>
              </span>
              <input
                value={form.upcastUnlockKey}
                onChange={(event) =>
                  setForm((c) => ({ ...c, upcastUnlockKey: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="additional_beam"
              />
            </label>
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Unlock summary <span className="text-red-400">*</span>
              </span>
              <input
                value={form.upcastUnlockSummary}
                onChange={(event) =>
                  setForm((c) => ({ ...c, upcastUnlockSummary: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="Create one additional beam per slot level above 5th"
              />
            </label>
          </div>
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Unlock editorial
            </span>
            <input
              value={form.upcastUnlockEditorial}
              onChange={(event) =>
                setForm((c) => ({ ...c, upcastUnlockEditorial: event.target.value }))
              }
              className={`${inputClassName} mt-2`}
              placeholder="Optional editorial note about the unlocked effect"
            />
          </label>
        </div>
      )}
    </>
  );
};
