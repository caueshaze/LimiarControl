import type { Dispatch, SetStateAction } from "react";

import type {
  BaseItemCostUnit,
  BaseItemEquipmentCategory,
} from "../../entities/base-item";
import { useLocale } from "../../shared/hooks/useLocale";
import { localizeBaseItemAdminValue } from "../../shared/i18n/domainLabels";
import {
  COST_UNIT_OPTIONS,
  EQUIPMENT_CATEGORY_OPTIONS,
  type FormState,
  inputClassName,
} from "./systemCatalog.types";

type Props = {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
};

export const SystemCatalogGeneralFields = ({ form, setForm }: Props) => {
  const { locale, t } = useLocale();

  const formatItemChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeBaseItemAdminValue(value, locale);

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.nameEn")}
          </span>
          <input
            value={form.nameEn}
            onChange={(event) =>
              setForm((current) => ({ ...current, nameEn: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="Longsword"
          />
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.namePt")}
          </span>
          <input
            value={form.namePt}
            onChange={(event) =>
              setForm((current) => ({ ...current, namePt: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="Espada Longa"
          />
        </label>

        <label className="block md:col-span-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Descrição EN
          </span>
          <textarea
            value={form.descriptionEn}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                descriptionEn: event.target.value,
              }))
            }
            className={`${inputClassName} mt-2 min-h-28`}
          />
        </label>

        <label className="block md:col-span-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Descrição PT
          </span>
          <textarea
            value={form.descriptionPt}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                descriptionPt: event.target.value,
              }))
            }
            className={`${inputClassName} mt-2 min-h-28`}
          />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <label className="block md:col-span-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Categoria
          </span>
          <select
            value={form.equipmentCategory}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                equipmentCategory:
                  event.target.value as BaseItemEquipmentCategory | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">sem categoria</option>
            {EQUIPMENT_CATEGORY_OPTIONS.map((category) => (
              <option key={category} value={category}>
                {formatItemChoiceLabel(category)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Custo
          </span>
          <input
            value={form.costQuantity}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                costQuantity: event.target.value,
              }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="15"
          />
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Unidade
          </span>
          <select
            value={form.costUnit}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                costUnit: event.target.value as BaseItemCostUnit | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">sem custo</option>
            {COST_UNIT_OPTIONS.map((costUnit) => (
              <option key={costUnit} value={costUnit}>
                {costUnit.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Peso
          </span>
          <input
            value={form.weight}
            onChange={(event) =>
              setForm((current) => ({ ...current, weight: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="3"
          />
        </label>
      </div>
    </>
  );
};
