import { useDeferredValue, useEffect, useState } from "react";

import type {
  BaseItem,
  BaseItemArmorCategory,
  BaseItemCostUnit,
  BaseItemDamageType,
  BaseItemDexBonusRule,
  BaseItemEquipmentCategory,
  BaseItemKind,
  BaseItemSource,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
  BaseItemWritePayload,
} from "../../entities/base-item";
import {
  BaseItemArmorCategory as BaseItemArmorCategoryValues,
  BaseItemCostUnit as BaseItemCostUnitValues,
  BaseItemDamageType as BaseItemDamageTypeValues,
  BaseItemDexBonusRule as BaseItemDexBonusRuleValues,
  BaseItemEquipmentCategory as BaseItemEquipmentCategoryValues,
  BaseItemKind as BaseItemKindValues,
  BaseItemSource as BaseItemSourceValues,
  BaseItemWeaponCategory as BaseItemWeaponCategoryValues,
  BaseItemWeaponRangeType as BaseItemWeaponRangeTypeValues,
} from "../../entities/base-item";
import {
  type ItemPropertySlug,
  WEAPON_PROPERTY_SLUGS,
} from "../../entities/item";
import { ItemPropertiesSelector } from "../../features/shop/components/ItemPropertiesSelector";
import { adminBaseItemsRepo } from "../../shared/api/adminBaseItemsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  localizeBaseItemAdminValue,
  localizeBaseItemCostUnit,
  localizeDamageType,
} from "../../shared/i18n/domainLabels";

type ActiveFilter = "all" | "active" | "inactive";
type ItemKindFilter = "ALL" | BaseItemKind;
type EquipmentCategoryFilter = "ALL" | BaseItemEquipmentCategory;

type FormState = {
  system: BaseItem["system"];
  canonicalKey: string;
  nameEn: string;
  namePt: string;
  descriptionEn: string;
  descriptionPt: string;
  itemKind: BaseItemKind;
  equipmentCategory: BaseItemEquipmentCategory | "";
  costQuantity: string;
  costUnit: BaseItemCostUnit | "";
  weight: string;
  weaponCategory: BaseItemWeaponCategory | "";
  weaponRangeType: BaseItemWeaponRangeType | "";
  damageDice: string;
  damageType: BaseItemDamageType | "";
  rangeNormalMeters: string;
  rangeLongMeters: string;
  versatileDamage: string;
  weaponPropertiesJson: ItemPropertySlug[];
  armorCategory: BaseItemArmorCategory | "";
  armorClassBase: string;
  dexBonusRule: BaseItemDexBonusRule | "";
  strengthRequirement: string;
  stealthDisadvantage: boolean;
  source: BaseItemSource;
  sourceRef: string;
  isSrd: boolean;
  isActive: boolean;
};

const SYSTEM_OPTIONS = ["DND5E"] as const;
const ITEM_KIND_OPTIONS = Object.values(BaseItemKindValues);
const EQUIPMENT_CATEGORY_OPTIONS = Object.values(BaseItemEquipmentCategoryValues);
const COST_UNIT_OPTIONS = Object.values(BaseItemCostUnitValues);
const WEAPON_CATEGORY_OPTIONS = Object.values(BaseItemWeaponCategoryValues);
const WEAPON_RANGE_OPTIONS = Object.values(BaseItemWeaponRangeTypeValues);
const ARMOR_CATEGORY_OPTIONS = Object.values(BaseItemArmorCategoryValues);
const DAMAGE_TYPE_OPTIONS = Object.values(BaseItemDamageTypeValues);
const DEX_BONUS_RULE_OPTIONS = Object.values(BaseItemDexBonusRuleValues);
const SOURCE_OPTIONS = Object.values(BaseItemSourceValues);

const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-amber-400/50 focus:outline-none";
const panelClassName =
  "rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(14,17,31,0.92),rgba(3,7,18,0.98))] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)]";

const normalizeOptionalText = (value: string) => {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
};

const normalizeCanonicalKey = (value: string) =>
  value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");

const parseOptionalNumber = (
  value: string,
  label: string,
): { value?: number; error?: string } => {
  const normalized = value.trim();
  if (!normalized) {
    return {};
  }
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return { error: `${label} precisa ser numérico.` };
  }
  return { value: parsed };
};

const parseOptionalInteger = (
  value: string,
  label: string,
): { value?: number; error?: string } => {
  const result = parseOptionalNumber(value, label);
  if (result.error || result.value === undefined) {
    return result;
  }
  if (!Number.isInteger(result.value)) {
    return { error: `${label} precisa ser inteiro.` };
  }
  return { value: result.value };
};

const createEmptyForm = (): FormState => ({
  system: "DND5E",
  canonicalKey: "",
  nameEn: "",
  namePt: "",
  descriptionEn: "",
  descriptionPt: "",
  itemKind: BaseItemKindValues.GEAR,
  equipmentCategory: "",
  costQuantity: "",
  costUnit: "",
  weight: "",
  weaponCategory: "",
  weaponRangeType: "",
  damageDice: "",
  damageType: "",
  rangeNormalMeters: "",
  rangeLongMeters: "",
  versatileDamage: "",
  weaponPropertiesJson: [],
  armorCategory: "",
  armorClassBase: "",
  dexBonusRule: "",
  strengthRequirement: "",
  stealthDisadvantage: false,
  source: BaseItemSourceValues.ADMIN_PANEL,
  sourceRef: "",
  isSrd: false,
  isActive: true,
});

const formFromItem = (item: BaseItem): FormState => ({
  system: item.system,
  canonicalKey: item.canonicalKey,
  nameEn: item.nameEn ?? "",
  namePt: item.namePt ?? "",
  descriptionEn: item.descriptionEn ?? "",
  descriptionPt: item.descriptionPt ?? "",
  itemKind: item.itemKind,
  equipmentCategory: item.equipmentCategory ?? "",
  costQuantity: item.costQuantity != null ? String(item.costQuantity) : "",
  costUnit: item.costUnit ?? "",
  weight: item.weight != null ? String(item.weight) : "",
  weaponCategory: item.weaponCategory ?? "",
  weaponRangeType: item.weaponRangeType ?? "",
  damageDice: item.damageDice ?? "",
  damageType: item.damageType ?? "",
  rangeNormalMeters: item.rangeNormalMeters != null ? String(item.rangeNormalMeters) : "",
  rangeLongMeters: item.rangeLongMeters != null ? String(item.rangeLongMeters) : "",
  versatileDamage: item.versatileDamage ?? "",
  weaponPropertiesJson: item.weaponPropertiesJson ?? [],
  armorCategory: item.armorCategory ?? "",
  armorClassBase: item.armorClassBase != null ? String(item.armorClassBase) : "",
  dexBonusRule: item.dexBonusRule ?? "",
  strengthRequirement:
    item.strengthRequirement != null ? String(item.strengthRequirement) : "",
  stealthDisadvantage: Boolean(item.stealthDisadvantage),
  source: item.source ?? BaseItemSourceValues.ADMIN_PANEL,
  sourceRef: item.sourceRef ?? "",
  isSrd: item.isSrd,
  isActive: item.isActive,
});

const buildPayload = (
  form: FormState,
): { payload?: BaseItemWritePayload; error?: string } => {
  const canonicalKey = normalizeCanonicalKey(form.canonicalKey);
  if (!canonicalKey) {
    return { error: "Canonical key é obrigatório." };
  }

  const nameEn = normalizeOptionalText(form.nameEn);
  const namePt = normalizeOptionalText(form.namePt);
  if (!nameEn && !namePt) {
    return { error: "Preencha ao menos um nome." };
  }

  const costQuantity = parseOptionalNumber(form.costQuantity, "Custo");
  if (costQuantity.error) {
    return { error: costQuantity.error };
  }
  const weight = parseOptionalNumber(form.weight, "Peso");
  if (weight.error) {
    return { error: weight.error };
  }
  const rangeNormalMeters = parseOptionalInteger(form.rangeNormalMeters, "Alcance normal (m)");
  if (rangeNormalMeters.error) {
    return { error: rangeNormalMeters.error };
  }
  const rangeLongMeters = parseOptionalInteger(form.rangeLongMeters, "Alcance longo (m)");
  if (rangeLongMeters.error) {
    return { error: rangeLongMeters.error };
  }
  const armorClassBase = parseOptionalInteger(form.armorClassBase, "CA base");
  if (armorClassBase.error) {
    return { error: armorClassBase.error };
  }
  const strengthRequirement = parseOptionalInteger(
    form.strengthRequirement,
    "Força mínima",
  );
  if (strengthRequirement.error) {
    return { error: strengthRequirement.error };
  }

  const isWeapon = form.itemKind === BaseItemKindValues.WEAPON;
  const isArmor = form.itemKind === BaseItemKindValues.ARMOR;
  const hasThrownProperty = form.weaponPropertiesJson.includes("thrown");
  const supportsLongRangeField =
    isWeapon &&
    (form.weaponRangeType === BaseItemWeaponRangeTypeValues.RANGED ||
      hasThrownProperty);
  const hasVersatileProperty = form.weaponPropertiesJson.includes("versatile");
  const isShieldArmor =
    isArmor && form.armorCategory === BaseItemArmorCategoryValues.SHIELD;

  if (isWeapon && !form.weaponCategory) {
    return { error: "Armas precisam de categoria de arma." };
  }
  if (isWeapon && !form.weaponRangeType) {
    return { error: "Armas precisam de tipo de alcance." };
  }
  if (isWeapon && !normalizeOptionalText(form.damageDice)) {
    return { error: "Armas precisam de dado de dano." };
  }
  if (isWeapon && !form.damageType) {
    return { error: "Armas precisam de tipo de dano." };
  }
  if (isWeapon && rangeNormalMeters.value === undefined) {
    return { error: "Armas precisam de alcance normal em metros." };
  }

  if (isArmor && !form.armorCategory) {
    return { error: "Armaduras precisam de categoria." };
  }
  if (isArmor && armorClassBase.value === undefined) {
    return { error: "Armaduras precisam de CA base." };
  }
  if (isArmor && !isShieldArmor && !form.dexBonusRule) {
    return { error: "Armaduras não-escudo precisam de regra de DEX." };
  }

  return {
    payload: {
      system: form.system,
      canonicalKey,
      nameEn,
      namePt,
      descriptionEn: normalizeOptionalText(form.descriptionEn),
      descriptionPt: normalizeOptionalText(form.descriptionPt),
      itemKind: form.itemKind,
      equipmentCategory: form.equipmentCategory || undefined,
      costQuantity: costQuantity.value,
      costUnit: form.costUnit || undefined,
      weight: weight.value,
      weaponCategory: isWeapon ? form.weaponCategory || undefined : undefined,
      weaponRangeType: isWeapon ? form.weaponRangeType || undefined : undefined,
      damageDice: isWeapon ? normalizeOptionalText(form.damageDice) : undefined,
      damageType: isWeapon ? form.damageType || undefined : undefined,
      rangeNormalMeters: isWeapon ? rangeNormalMeters.value : undefined,
      rangeLongMeters: supportsLongRangeField ? rangeLongMeters.value : undefined,
      versatileDamage:
        isWeapon && hasVersatileProperty
          ? normalizeOptionalText(form.versatileDamage)
          : undefined,
      weaponPropertiesJson: isWeapon ? form.weaponPropertiesJson : [],
      armorCategory: isArmor ? form.armorCategory || undefined : undefined,
      armorClassBase: isArmor ? armorClassBase.value : undefined,
      dexBonusRule:
        isArmor && !isShieldArmor ? form.dexBonusRule || undefined : undefined,
      strengthRequirement:
        isArmor && !isShieldArmor ? strengthRequirement.value : undefined,
      stealthDisadvantage:
        isArmor && !isShieldArmor ? form.stealthDisadvantage : false,
      isShield: isShieldArmor,
      source: form.source,
      sourceRef: normalizeOptionalText(form.sourceRef),
      isSrd: form.isSrd,
      isActive: form.isActive,
    },
  };
};

const currencyLabel = (value?: BaseItem["costUnit"] | "") =>
  value ? value.toUpperCase() : "sem custo";

export const SystemCatalogPage = () => {
  const { locale, t } = useLocale();
  const [items, setItems] = useState<BaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(createEmptyForm());
  const [search, setSearch] = useState("");
  const [itemKindFilter, setItemKindFilter] = useState<ItemKindFilter>("ALL");
  const [equipmentCategoryFilter, setEquipmentCategoryFilter] =
    useState<EquipmentCategoryFilter>("ALL");
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>("all");
  const deferredSearch = useDeferredValue(search);

  const supportsWeaponFields = form.itemKind === BaseItemKindValues.WEAPON;
  const supportsArmorFields = form.itemKind === BaseItemKindValues.ARMOR;
  const hasThrownProperty =
    supportsWeaponFields && form.weaponPropertiesJson.includes("thrown");
  const supportsLongRangeField =
    supportsWeaponFields &&
    (form.weaponRangeType === BaseItemWeaponRangeTypeValues.RANGED ||
      hasThrownProperty);
  const hasVersatileProperty =
    supportsWeaponFields && form.weaponPropertiesJson.includes("versatile");
  const isShieldArmor =
    supportsArmorFields && form.armorCategory === BaseItemArmorCategoryValues.SHIELD;

  const loadItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminBaseItemsRepo.list({
        system: "DND5E",
        itemKind: itemKindFilter === "ALL" ? undefined : itemKindFilter,
        equipmentCategory:
          equipmentCategoryFilter === "ALL"
            ? undefined
            : equipmentCategoryFilter,
        search: deferredSearch.trim() || undefined,
        isActive:
          activeFilter === "all" ? undefined : activeFilter === "active",
      });
      setItems(result);
      setSelectedItemId((currentId) =>
        currentId && result.some((item) => item.id === currentId)
          ? currentId
          : null,
      );
    } catch (loadError) {
      const message =
        loadError instanceof Error
          ? loadError.message
          : "Falha ao carregar o catálogo.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadItems();
  }, [deferredSearch, itemKindFilter, equipmentCategoryFilter, activeFilter]);

  useEffect(() => {
    if (!selectedItemId) {
      return;
    }
    const selectedItem = items.find((item) => item.id === selectedItemId);
    if (!selectedItem) {
      setForm(createEmptyForm());
      return;
    }
    setForm(formFromItem(selectedItem));
  }, [items, selectedItemId]);

  const handleSelectItem = (item: BaseItem) => {
    setSelectedItemId(item.id);
    setForm(formFromItem(item));
    setError(null);
  };

  const handleCreateNew = () => {
    setSelectedItemId(null);
    setForm(createEmptyForm());
    setError(null);
    setLoadingMessage(null);
  };

  const handleSave = async () => {
    const built = buildPayload(form);
    if (!built.payload) {
      setError(built.error ?? "Payload inválido.");
      return;
    }

    setLoadingMessage(selectedItemId ? "Salvando item..." : "Criando item...");
    setError(null);
    try {
      const saved = selectedItemId
        ? await adminBaseItemsRepo.update(selectedItemId, built.payload)
        : await adminBaseItemsRepo.create(built.payload);
      await loadItems();
      setSelectedItemId(saved.id);
      setForm(formFromItem(saved));
      setLoadingMessage(selectedItemId ? "Alterações salvas." : "Item criado.");
    } catch (saveError) {
      const message =
        saveError instanceof Error
          ? saveError.message
          : "Falha ao salvar o item.";
      setError(message);
      setLoadingMessage(null);
    }
  };

  const handleDelete = async () => {
    if (!selectedItemId) {
      return;
    }
    if (!window.confirm("Remover este item base do catálogo global?")) {
      return;
    }

    setLoadingMessage("Removendo item...");
    setError(null);
    try {
      await adminBaseItemsRepo.delete(selectedItemId);
      handleCreateNew();
      await loadItems();
      setLoadingMessage("Item removido.");
    } catch (deleteError) {
      const message =
        deleteError instanceof Error
          ? deleteError.message
          : "Falha ao remover o item.";
      setError(message);
      setLoadingMessage(null);
    }
  };

  const formatItemChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeBaseItemAdminValue(value, locale);
  const selectedKindLabel = selectedItemId ? t("catalog.edit") : t("catalog.createAction");

  return (
    <section className="space-y-6">
      <div className={panelClassName}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-amber-300/70">
              {t("catalog.admin.systemTitle")}
            </p>
            <h1 className="text-3xl font-black tracking-tight text-white">
              {t("catalog.admin.systemTitle")}
            </h1>
            <p className="max-w-3xl text-sm leading-6 text-slate-300">
              {t("catalog.admin.systemDescription")}
            </p>
          </div>
          <button
            type="button"
            onClick={handleCreateNew}
            className="rounded-2xl border border-amber-400/30 bg-amber-400/12 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:bg-amber-400/18"
          >
            {t("catalog.createAction")}
          </button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className={`${panelClassName} space-y-5`}>
          <div className="grid gap-3">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.admin.filters.search")}
              </span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className={`${inputClassName} mt-2`}
                placeholder={t("catalog.admin.filters.searchItemsPlaceholder")}
              />
            </label>

            <div className="grid gap-3">
              <label className="block">
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  {t("catalog.admin.filters.kind")}
                </span>
                <select
                  value={itemKindFilter}
                  onChange={(event) =>
                    setItemKindFilter(event.target.value as ItemKindFilter)
                  }
                  className={`${inputClassName} mt-2`}
                >
                  <option value="ALL">{t("catalog.admin.filters.allKinds")}</option>
                  {ITEM_KIND_OPTIONS.map((itemKind) => (
                    <option key={itemKind} value={itemKind}>
                      {formatItemChoiceLabel(itemKind)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  {t("catalog.admin.filters.category")}
                </span>
                <select
                  value={equipmentCategoryFilter}
                  onChange={(event) =>
                    setEquipmentCategoryFilter(
                      event.target.value as EquipmentCategoryFilter,
                    )
                  }
                  className={`${inputClassName} mt-2`}
                >
                  <option value="ALL">{t("catalog.admin.filters.allCategories")}</option>
                  {EQUIPMENT_CATEGORY_OPTIONS.map((category) => (
                    <option key={category} value={category}>
                      {formatItemChoiceLabel(category)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  {t("catalog.admin.filters.status")}
                </span>
                <select
                  value={activeFilter}
                  onChange={(event) =>
                    setActiveFilter(event.target.value as ActiveFilter)
                  }
                  className={`${inputClassName} mt-2`}
                >
                  <option value="all">{t("catalog.admin.filters.allStatuses")}</option>
                  <option value="active">{t("catalog.admin.table.active")}</option>
                  <option value="inactive">{t("catalog.admin.table.inactive")}</option>
                </select>
              </label>
            </div>
          </div>

          <div className="rounded-3xl border border-white/8 bg-black/20 px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.filtersTitle")}
            </p>
            <p className="mt-2 text-2xl font-black text-white">{items.length}</p>
            <p className="text-sm text-slate-400">{t("catalog.filtersResults")}</p>
          </div>

          {loading && (
            <div className="rounded-3xl border border-white/8 bg-black/20 px-4 py-6 text-sm text-slate-400">
              {t("catalog.loading")}
            </div>
          )}

          {!loading && (
            <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSelectItem(item)}
                  className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
                    selectedItemId === item.id
                      ? "border-amber-300/40 bg-amber-300/10"
                      : "border-white/8 bg-black/20 hover:border-white/15 hover:bg-white/5"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {item.namePt || item.nameEn}
                      </p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.22em] text-slate-500">
                        {item.canonicalKey}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${
                        item.isActive
                          ? "bg-emerald-400/12 text-emerald-200"
                          : "bg-rose-400/12 text-rose-200"
                      }`}
                    >
                      {item.isActive ? t("catalog.admin.table.active") : t("catalog.admin.table.inactive")}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                    <span className="rounded-full border border-white/10 px-2 py-1">
                      {formatItemChoiceLabel(item.itemKind)}
                    </span>
                    <span className="rounded-full border border-white/10 px-2 py-1">
                      {item.costUnit ? localizeBaseItemCostUnit(item.costUnit, locale) : currencyLabel(item.costUnit)}
                    </span>
                    {item.equipmentCategory && (
                      <span className="rounded-full border border-white/10 px-2 py-1">
                        {formatItemChoiceLabel(item.equipmentCategory)}
                      </span>
                    )}
                  </div>
                </button>
              ))}
              {items.length === 0 && (
                <div className="rounded-[24px] border border-dashed border-white/10 px-4 py-8 text-sm text-slate-400">
                  {t("catalog.emptyFilteredTitle")}
                </div>
              )}
            </div>
          )}
        </aside>

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
                    itemKind: event.target.value as BaseItemKind,
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

          {supportsWeaponFields && (
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
                        weaponCategory:
                          event.target.value as BaseItemWeaponCategory | "",
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
                        weaponRangeType:
                          event.target.value as BaseItemWeaponRangeType | "",
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
                  <input
                    value={form.damageDice}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        damageDice: event.target.value,
                      }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder="1d8"
                  />
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
                  <input
                    value={form.rangeNormalMeters}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        rangeNormalMeters: event.target.value,
                      }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder="2, 6, 24..."
                  />
                </label>

                {supportsLongRangeField && (
                  <label className="block">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                      Alcance longo (m)
                    </span>
                    <input
                      value={form.rangeLongMeters}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          rangeLongMeters: event.target.value,
                        }))
                      }
                      className={`${inputClassName} mt-2`}
                      placeholder="96"
                    />
                  </label>
                )}

                {hasVersatileProperty && (
                  <label className="block">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                      Dano versátil
                    </span>
                    <input
                      value={form.versatileDamage}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          versatileDamage: event.target.value,
                        }))
                      }
                      className={`${inputClassName} mt-2`}
                      placeholder="1d10"
                    />
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
          )}

          {supportsArmorFields && (
            <div className="space-y-4 rounded-[24px] border border-white/8 bg-black/20 p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                    Campos de armadura
                  </p>
                  <p className="mt-1 text-sm text-slate-400">
                    O formulário esconde campos irrelevantes e trata escudo como caso
                    especial.
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
                  <input
                    value={form.armorClassBase}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        armorClassBase: event.target.value,
                      }))
                    }
                    className={`${inputClassName} mt-2`}
                    placeholder="16"
                  />
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
                          dexBonusRule:
                            event.target.value as BaseItemDexBonusRule | "",
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
                    <input
                      value={form.strengthRequirement}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          strengthRequirement: event.target.value,
                        }))
                      }
                      className={`${inputClassName} mt-2`}
                      placeholder="15"
                    />
                  </label>
                )}
              </div>
            </div>
          )}

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
              onClick={handleSave}
              className="rounded-2xl border border-emerald-400/30 bg-emerald-400/12 px-4 py-3 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/18"
            >
              {selectedItemId ? "Salvar alterações" : "Criar item base"}
            </button>
            <button
              type="button"
              onClick={handleCreateNew}
              className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:bg-white/6"
            >
              Limpar editor
            </button>
            {selectedItemId && (
              <button
                type="button"
                onClick={handleDelete}
                className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/16"
              >
                Deletar item
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
