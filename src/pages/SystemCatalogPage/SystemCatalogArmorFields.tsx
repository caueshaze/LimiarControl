import type { Dispatch, SetStateAction } from "react";

import type { BaseItemArmorCategory, BaseItemDexBonusRule } from "../../entities/base-item";
import { BaseItemArmorCategory as BaseItemArmorCategoryValues } from "../../entities/base-item";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  AUTOMATION_ARMOR_CLASS_OPTIONS,
  AUTOMATION_STRENGTH_REQUIREMENT_OPTIONS,
  buildAutomationSelectOptions,
} from "../../shared/lib/itemAutomationOptions";
import { localizeBaseItemAdminValue } from "../../shared/i18n/domainLabels";
import {
  ARMOR_CATEGORY_OPTIONS,
  DEX_BONUS_RULE_OPTIONS,
  type FormState,
  inputClassName,
} from "./systemCatalog.types";

type Props = {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
};

export const SystemCatalogArmorFields = ({ form, setForm }: Props) => {
  const { locale, t } = useLocale();

  const formatItemChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeBaseItemAdminValue(value, locale);

  const isShieldArmor = form.armorCategory === BaseItemArmorCategoryValues.SHIELD;

  return (
    <div className="space-y-4 rounded-[24px] border border-white/8 bg-black/20 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            Campos de armadura
          </p>
          <p className="mt-1 text-sm text-slate-400">
            O formulário esconde campos irrelevantes e trata escudo como caso especial.
          </p>
        </div>
        {isShieldArmor && (
          <span className="rounded-full border border-sky-300/15 bg-sky-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-100">
            escudo detectado
          </span>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Categoria
          </span>
          <select
            value={form.armorCategory}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                armorCategory: event.target.value as BaseItemArmorCategory | "",
                dexBonusRule:
                  event.target.value === BaseItemArmorCategoryValues.SHIELD
                    ? ""
                    : current.dexBonusRule,
                stealthDisadvantage:
                  event.target.value === BaseItemArmorCategoryValues.SHIELD
                    ? false
                    : current.stealthDisadvantage,
                strengthRequirement:
                  event.target.value === BaseItemArmorCategoryValues.SHIELD
                    ? ""
                    : current.strengthRequirement,
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">{t("catalog.admin.selectPlaceholder")}</option>
            {ARMOR_CATEGORY_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatItemChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            CA base
          </span>
          <select
            value={form.armorClassBase}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                armorClassBase: event.target.value,
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            {buildAutomationSelectOptions(form.armorClassBase, AUTOMATION_ARMOR_CLASS_OPTIONS).map((value) => (
              <option key={value || "none"} value={value}>
                {value || t("catalog.admin.selectPlaceholder")}
              </option>
            ))}
          </select>
        </label>

        {!isShieldArmor && (
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Regra de DEX
            </span>
            <select
              value={form.dexBonusRule}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  dexBonusRule: event.target.value as BaseItemDexBonusRule | "",
                }))
              }
              className={`${inputClassName} mt-2`}
            >
              <option value="">{t("catalog.admin.selectPlaceholder")}</option>
              {DEX_BONUS_RULE_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {formatItemChoiceLabel(value)}
                </option>
              ))}
            </select>
          </label>
        )}

        {!isShieldArmor && (
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Força mínima
            </span>
            <select
              value={form.strengthRequirement}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  strengthRequirement: event.target.value,
                }))
              }
              disabled={isShieldArmor}
              className={`${inputClassName} mt-2`}
            >
              {buildAutomationSelectOptions(form.strengthRequirement, AUTOMATION_STRENGTH_REQUIREMENT_OPTIONS).map((value) => (
                <option key={value || "none"} value={value}>
                  {value || t("catalog.admin.selectPlaceholder")}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
    </div>
  );
};
