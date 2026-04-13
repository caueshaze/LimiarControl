import type { Dispatch, SetStateAction } from "react";

import type { BaseItem, BaseItemSource } from "../../entities/base-item";
import { BaseItemArmorCategory as BaseItemArmorCategoryValues, BaseItemKind as BaseItemKindValues } from "../../entities/base-item";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  AUTOMATION_DICE_OPTIONS,
  AUTOMATION_HEAL_BONUS_OPTIONS,
  buildAutomationSelectOptions,
} from "../../shared/lib/itemAutomationOptions";
import { localizeBaseItemAdminValue } from "../../shared/i18n/domainLabels";
import { SystemCatalogArmorFields } from "./SystemCatalogArmorFields";
import { SystemCatalogGeneralFields } from "./SystemCatalogGeneralFields";
import { SystemCatalogWeaponFields } from "./SystemCatalogWeaponFields";
import {
  type FormState,
  ITEM_KIND_OPTIONS,
  SOURCE_OPTIONS,
  SYSTEM_OPTIONS,
  inputClassName,
  panelClassName,
} from "./systemCatalog.types";

type Props = {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
  selectedItemId: string | null;
  loadingMessage: string | null;
  error: string | null;
  onSave: () => void;
  onCreateNew: () => void;
  onDelete: () => void;
};

export const SystemCatalogItemForm = ({
  form,
  setForm,
  selectedItemId,
  loadingMessage,
  error,
  onSave,
  onCreateNew,
  onDelete,
}: Props) => {
  const { locale, t } = useLocale();

  const formatItemChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeBaseItemAdminValue(value, locale);

  const supportsWeaponFields = form.itemKind === BaseItemKindValues.WEAPON;
  const supportsArmorFields = form.itemKind === BaseItemKindValues.ARMOR;
  const supportsConsumableFields = form.itemKind === BaseItemKindValues.CONSUMABLE;
  const isShieldArmor =
    supportsArmorFields && form.armorCategory === BaseItemArmorCategoryValues.SHIELD;
  const selectedKindLabel = selectedItemId ? t("catalog.edit") : t("catalog.createAction");

  return (
    <div className={`${panelClassName} space-y-5`}>
      <div className="flex flex-col gap-2 border-b border-white/8 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            {t("catalog.edit")}
          </p>
          <h2 className="mt-1 text-2xl font-black tracking-tight text-white">
            {selectedKindLabel}
          </h2>
        </div>
        {loadingMessage && <p className="text-sm text-amber-200">{loadingMessage}</p>}
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.system")}
          </span>
          <select
            value={form.system}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                system: event.target.value as BaseItem["system"],
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            {SYSTEM_OPTIONS.map((system) => (
              <option key={system} value={system}>
                {formatItemChoiceLabel(system)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.canonicalKey")}
          </span>
          <input
            value={form.canonicalKey}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                canonicalKey: event.target.value,
              }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="longsword"
          />
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.kind")}
          </span>
          <select
            value={form.itemKind}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                itemKind: event.target.value as FormState["itemKind"],
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            {ITEM_KIND_OPTIONS.map((itemKind) => (
              <option key={itemKind} value={itemKind}>
                {formatItemChoiceLabel(itemKind)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <SystemCatalogGeneralFields form={form} setForm={setForm} />

      {supportsConsumableFields && (
        <div className="space-y-4 rounded-[24px] border border-white/8 bg-black/20 p-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("catalog.admin.table.healDice")}
            </p>
            <p className="mt-1 text-sm text-slate-400">
              Estruture a fórmula de cura automática para consumíveis.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("shop.form.healDice")}
              </span>
              <select
                value={form.healDice}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    healDice: event.target.value,
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                {buildAutomationSelectOptions(form.healDice, AUTOMATION_DICE_OPTIONS).map((value) => (
                  <option key={value || "none"} value={value}>
                    {value || t("catalog.admin.selectPlaceholder")}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("shop.form.healBonus")}
              </span>
              <select
                value={form.healBonus}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    healBonus: event.target.value,
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                {buildAutomationSelectOptions(form.healBonus, AUTOMATION_HEAL_BONUS_OPTIONS).map((value) => (
                  <option key={value || "none"} value={value}>
                    {value || t("catalog.admin.selectPlaceholder")}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      )}

      {supportsWeaponFields && <SystemCatalogWeaponFields form={form} setForm={setForm} />}
      {supportsArmorFields && <SystemCatalogArmorFields form={form} setForm={setForm} />}

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Source
          </span>
          <select
            value={form.source}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                source: event.target.value as BaseItemSource,
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            {SOURCE_OPTIONS.map((source) => (
              <option key={source} value={source}>
                {formatItemChoiceLabel(source)}
              </option>
            ))}
          </select>
        </label>

        <label className="block md:col-span-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Source ref
          </span>
          <input
            value={form.sourceRef}
            onChange={(event) =>
              setForm((current) => ({ ...current, sourceRef: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="PHB p.149"
          />
        </label>
      </div>

      <div className="grid gap-3 rounded-[24px] border border-white/8 bg-black/20 p-4 sm:grid-cols-4">
        {supportsArmorFields && !isShieldArmor && (
          <label className="flex items-center gap-3 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={form.stealthDisadvantage}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  stealthDisadvantage: event.target.checked,
                }))
              }
            />
            stealth disadvantage
          </label>
        )}

        {supportsArmorFields && (
          <label className="flex items-center gap-3 text-sm text-slate-300">
            <input type="checkbox" checked={isShieldArmor} readOnly />
            shield
          </label>
        )}

        <label className="flex items-center gap-3 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={form.isSrd}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                isSrd: event.target.checked,
              }))
            }
          />
          SRD
        </label>

        <label className="flex items-center gap-3 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={form.isActive}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                isActive: event.target.checked,
              }))
            }
          />
          ativo
        </label>
      </div>

      <div className="flex flex-wrap gap-3 border-t border-white/8 pt-4">
        <button
          type="button"
          onClick={onSave}
          className="rounded-2xl border border-emerald-400/30 bg-emerald-400/12 px-4 py-3 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/18"
        >
          {selectedItemId ? "Salvar alterações" : "Criar item base"}
        </button>
        <button
          type="button"
          onClick={onCreateNew}
          className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:bg-white/6"
        >
          Limpar editor
        </button>
        {selectedItemId && (
          <button
            type="button"
            onClick={onDelete}
            className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/16"
          >
            Deletar item
          </button>
        )}
      </div>
    </div>
  );
};
