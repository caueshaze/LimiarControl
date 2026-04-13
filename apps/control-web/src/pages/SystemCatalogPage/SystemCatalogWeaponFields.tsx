import type { Dispatch, SetStateAction } from "react";

import type {
  BaseItemDamageType,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../entities/base-item";
import { BaseItemWeaponRangeType as BaseItemWeaponRangeTypeValues } from "../../entities/base-item";
import { ItemPropertiesSelector } from "../../features/shop/components/ItemPropertiesSelector";
import { WEAPON_PROPERTY_SLUGS } from "../../entities/item";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  AUTOMATION_DICE_OPTIONS,
  AUTOMATION_RANGE_OPTIONS,
  buildAutomationSelectOptions,
} from "../../shared/lib/itemAutomationOptions";
import {
  localizeBaseItemAdminValue,
  localizeDamageType,
} from "../../shared/i18n/domainLabels";
import {
  DAMAGE_TYPE_OPTIONS,
  type FormState,
  inputClassName,
  WEAPON_CATEGORY_OPTIONS,
  WEAPON_RANGE_OPTIONS,
} from "./systemCatalog.types";

type Props = {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
};

export const SystemCatalogWeaponFields = ({ form, setForm }: Props) => {
  const { locale, t } = useLocale();

  const formatItemChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeBaseItemAdminValue(value, locale);

  const hasThrownProperty = form.weaponPropertiesJson.includes("thrown");
  const supportsLongRangeField =
    form.weaponRangeType === BaseItemWeaponRangeTypeValues.RANGED || hasThrownProperty;
  const hasVersatileProperty = form.weaponPropertiesJson.includes("versatile");

  return (
    <div className="space-y-4 rounded-[24px] border border-white/8 bg-black/20 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            Campos de arma
          </p>
          <p className="mt-1 text-sm text-slate-400">
            Apenas escolhas fechadas para dados usados em combate.
          </p>
        </div>
        {supportsLongRangeField && (
          <span className="rounded-full border border-amber-300/15 bg-amber-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-100">
            alcance habilitado
          </span>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Categoria da arma
          </span>
          <select
            value={form.weaponCategory}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                weaponCategory: event.target.value as BaseItemWeaponCategory | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">{t("catalog.admin.selectPlaceholder")}</option>
            {WEAPON_CATEGORY_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatItemChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Tipo de alcance
          </span>
          <select
            value={form.weaponRangeType}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                weaponRangeType: event.target.value as BaseItemWeaponRangeType | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">{t("catalog.admin.selectPlaceholder")}</option>
            {WEAPON_RANGE_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatItemChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Dano
          </span>
          <select
            value={form.damageDice}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                damageDice: event.target.value,
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            {buildAutomationSelectOptions(form.damageDice, AUTOMATION_DICE_OPTIONS).map((value) => (
              <option key={value || "none"} value={value}>
                {value || t("catalog.admin.selectPlaceholder")}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Tipo de dano
          </span>
          <select
            value={form.damageType}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                damageType: event.target.value as BaseItemDamageType | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">{t("catalog.admin.selectPlaceholder")}</option>
            {DAMAGE_TYPE_OPTIONS.map((damageType) => (
              <option key={damageType} value={damageType}>
                {localizeDamageType(damageType, locale)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Alcance normal (m)
          </span>
          <select
            value={form.rangeNormalMeters}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                rangeNormalMeters: event.target.value,
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            {buildAutomationSelectOptions(form.rangeNormalMeters, AUTOMATION_RANGE_OPTIONS).map((value) => (
              <option key={value || "none"} value={value}>
                {value || t("catalog.admin.selectPlaceholder")}
              </option>
            ))}
          </select>
        </label>

        {supportsLongRangeField && (
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Alcance longo (m)
            </span>
            <select
              value={form.rangeLongMeters}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  rangeLongMeters: event.target.value,
                }))
              }
              className={`${inputClassName} mt-2`}
            >
              {buildAutomationSelectOptions(form.rangeLongMeters, AUTOMATION_RANGE_OPTIONS).map((value) => (
                <option key={value || "none"} value={value}>
                  {value || t("catalog.admin.selectPlaceholder")}
                </option>
              ))}
            </select>
          </label>
        )}

        {hasVersatileProperty && (
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Dano versátil
            </span>
            <select
              value={form.versatileDamage}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  versatileDamage: event.target.value,
                }))
              }
              className={`${inputClassName} mt-2`}
            >
              {buildAutomationSelectOptions(form.versatileDamage, AUTOMATION_DICE_OPTIONS).map((value) => (
                <option key={value || "none"} value={value}>
                  {value || t("catalog.admin.selectPlaceholder")}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Propriedades de arma
          </p>
          <p className="mt-1 text-sm text-slate-400">
            Multi-select fechado. Nada de texto livre em propriedades usadas pela
            automação.
          </p>
        </div>
        <ItemPropertiesSelector
          available={WEAPON_PROPERTY_SLUGS}
          value={form.weaponPropertiesJson}
          onChange={(next) =>
            setForm((current) => ({
              ...current,
              weaponPropertiesJson: next,
            }))
          }
        />
      </div>
    </div>
  );
};
