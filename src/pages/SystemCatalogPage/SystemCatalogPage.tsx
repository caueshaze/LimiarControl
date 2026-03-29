import { useDeferredValue, useEffect, useState } from "react";

import type { BaseItem } from "../../entities/base-item";
import { adminBaseItemsRepo } from "../../shared/api/adminBaseItemsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { SystemCatalogItemForm } from "./SystemCatalogItemForm";
import { SystemCatalogSidebar } from "./SystemCatalogSidebar";
import { buildPayload, createEmptyForm, formFromItem } from "./systemCatalog.helpers";
import {
  type ActiveFilter,
  type EquipmentCategoryFilter,
  type FormState,
  type ItemKindFilter,
  panelClassName,
} from "./systemCatalog.types";

export const SystemCatalogPage = () => {
  const { t } = useLocale();
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

  const loadItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminBaseItemsRepo.list({
        system: "DND5E",
        itemKind: itemKindFilter === "ALL" ? undefined : itemKindFilter,
        equipmentCategory:
          equipmentCategoryFilter === "ALL" ? undefined : equipmentCategoryFilter,
        search: deferredSearch.trim() || undefined,
        isActive: activeFilter === "all" ? undefined : activeFilter === "active",
      });
      setItems(result);
      setSelectedItemId((currentId) =>
        currentId && result.some((item) => item.id === currentId) ? currentId : null,
      );
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : "Falha ao carregar o catálogo.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadItems();
  }, [deferredSearch, itemKindFilter, equipmentCategoryFilter, activeFilter]);

  useEffect(() => {
    if (!selectedItemId) return;
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

  const handleSyncSeed = async () => {
    setLoadingMessage("Sincronizando catálogo base...");
    setError(null);
    try {
      const result = await adminBaseItemsRepo.syncSeed();
      await loadItems();
      setLoadingMessage(
        `Catálogo sincronizado. ${result.inserted} inseridos, ${result.updated} atualizados.`,
      );
    } catch (syncError) {
      const message =
        syncError instanceof Error ? syncError.message : "Falha ao sincronizar o catálogo base.";
      setError(message);
      setLoadingMessage(null);
    }
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
        saveError instanceof Error ? saveError.message : "Falha ao salvar o item.";
      setError(message);
      setLoadingMessage(null);
    }
  };

  const handleDelete = async () => {
    if (!selectedItemId) return;
    if (!window.confirm("Remover este item base do catálogo global?")) return;
    setLoadingMessage("Removendo item...");
    setError(null);
    try {
      await adminBaseItemsRepo.delete(selectedItemId);
      handleCreateNew();
      await loadItems();
      setLoadingMessage("Item removido.");
    } catch (deleteError) {
      const message =
        deleteError instanceof Error ? deleteError.message : "Falha ao remover o item.";
      setError(message);
      setLoadingMessage(null);
    }
  };

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
          <div className="flex flex-wrap items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => {
                void handleSyncSeed();
              }}
              className="rounded-2xl border border-sky-400/30 bg-sky-400/12 px-4 py-3 text-sm font-semibold text-sky-100 transition hover:bg-sky-400/18"
            >
              Sincronizar seed
            </button>
            <button
              type="button"
              onClick={handleCreateNew}
              className="rounded-2xl border border-amber-400/30 bg-amber-400/12 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:bg-amber-400/18"
            >
              {t("catalog.createAction")}
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <SystemCatalogSidebar
          items={items}
          loading={loading}
          search={search}
          setSearch={setSearch}
          itemKindFilter={itemKindFilter}
          setItemKindFilter={setItemKindFilter}
          equipmentCategoryFilter={equipmentCategoryFilter}
          setEquipmentCategoryFilter={setEquipmentCategoryFilter}
          activeFilter={activeFilter}
          setActiveFilter={setActiveFilter}
          selectedItemId={selectedItemId}
          onSelectItem={handleSelectItem}
        />
        <SystemCatalogItemForm
          form={form}
          setForm={setForm}
          selectedItemId={selectedItemId}
          loadingMessage={loadingMessage}
          error={error}
          onSave={handleSave}
          onCreateNew={handleCreateNew}
          onDelete={handleDelete}
        />
      </div>
    </section>
  );
};
