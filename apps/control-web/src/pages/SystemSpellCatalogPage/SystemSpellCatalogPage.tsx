import { useDeferredValue, useEffect, useState } from "react";

import type { BaseSpell } from "../../entities/base-spell";
import { adminBaseSpellsRepo } from "../../shared/api/adminBaseSpellsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { SystemSpellCatalogSidebar } from "./SystemSpellCatalogSidebar";
import { SystemSpellCatalogSpellForm } from "./SystemSpellCatalogSpellForm";
import { buildPayload, createEmptyForm, formFromSpell } from "./systemSpellCatalog.helpers";
import {
  type ActiveFilter,
  type FormState,
  type LevelFilter,
  type SchoolFilter,
  panelClassName,
} from "./systemSpellCatalog.types";

export const SystemSpellCatalogPage = () => {
  const { t } = useLocale();
  const [spells, setSpells] = useState<BaseSpell[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpellId, setSelectedSpellId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(createEmptyForm());
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState<LevelFilter>("ALL");
  const [schoolFilter, setSchoolFilter] = useState<SchoolFilter>("ALL");
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>("all");
  const deferredSearch = useDeferredValue(search);

  const loadSpells = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminBaseSpellsRepo.list({
        system: "DND5E",
        level: levelFilter === "ALL" ? undefined : levelFilter,
        school: schoolFilter === "ALL" ? undefined : schoolFilter,
        search: deferredSearch.trim() || undefined,
        isActive: activeFilter === "all" ? undefined : activeFilter === "active",
      });
      setSpells(result);
      setSelectedSpellId((currentId) =>
        currentId && result.some((s) => s.id === currentId) ? currentId : null,
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
    void loadSpells();
  }, [deferredSearch, levelFilter, schoolFilter, activeFilter]);

  useEffect(() => {
    if (!selectedSpellId) return;
    const selectedSpell = spells.find((s) => s.id === selectedSpellId);
    if (!selectedSpell) {
      setForm(createEmptyForm());
      return;
    }
    setForm(formFromSpell(selectedSpell));
  }, [spells, selectedSpellId]);

  const handleSelectSpell = (spell: BaseSpell) => {
    setSelectedSpellId(spell.id);
    setForm(formFromSpell(spell));
    setError(null);
  };

  const handleCreateNew = () => {
    setSelectedSpellId(null);
    setForm(createEmptyForm());
    setError(null);
    setLoadingMessage(null);
  };

  const handleSave = async () => {
    const isNew = !selectedSpellId;
    const built = buildPayload(form, isNew);
    if (!built.payload) {
      setError(built.error ?? "Payload inválido.");
      return;
    }
    setLoadingMessage(isNew ? "Criando magia..." : "Salvando magia...");
    setError(null);
    try {
      const saved = isNew
        ? await adminBaseSpellsRepo.create(built.payload)
        : await adminBaseSpellsRepo.update(selectedSpellId, built.payload);
      await loadSpells();
      setSelectedSpellId(saved.id);
      setForm(formFromSpell(saved));
      setLoadingMessage(isNew ? "Magia criada." : "Alterações salvas.");
    } catch (saveError) {
      const message =
        saveError instanceof Error ? saveError.message : "Falha ao salvar a magia.";
      setError(message);
      setLoadingMessage(null);
    }
  };

  const handleDelete = async () => {
    if (!selectedSpellId) return;
    if (!window.confirm("Remover esta magia base do catálogo global?")) return;
    setLoadingMessage("Removendo magia...");
    setError(null);
    try {
      await adminBaseSpellsRepo.delete(selectedSpellId);
      handleCreateNew();
      await loadSpells();
      setLoadingMessage("Magia removida.");
    } catch (deleteError) {
      const message =
        deleteError instanceof Error ? deleteError.message : "Falha ao remover a magia.";
      setError(message);
      setLoadingMessage(null);
    }
  };

  return (
    <section className="space-y-6">
      <div className={panelClassName}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-violet-300/70">
              {t("catalog.admin.spellSystemTitle")}
            </p>
            <h1 className="text-3xl font-black tracking-tight text-white">
              {t("catalog.admin.spellSystemTitle")}
            </h1>
            <p className="max-w-3xl text-sm leading-6 text-slate-300">
              {t("catalog.admin.spellSystemDescription")}
            </p>
          </div>
          <button
            type="button"
            onClick={handleCreateNew}
            className="rounded-2xl border border-violet-400/30 bg-violet-400/12 px-4 py-3 text-sm font-semibold text-violet-100 transition hover:bg-violet-400/18"
          >
            {t("catalog.createAction")}
          </button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <SystemSpellCatalogSidebar
          spells={spells}
          loading={loading}
          search={search}
          setSearch={setSearch}
          levelFilter={levelFilter}
          setLevelFilter={setLevelFilter}
          schoolFilter={schoolFilter}
          setSchoolFilter={setSchoolFilter}
          activeFilter={activeFilter}
          setActiveFilter={setActiveFilter}
          selectedSpellId={selectedSpellId}
          onSelectSpell={handleSelectSpell}
        />
        <SystemSpellCatalogSpellForm
          form={form}
          setForm={setForm}
          selectedSpellId={selectedSpellId}
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
