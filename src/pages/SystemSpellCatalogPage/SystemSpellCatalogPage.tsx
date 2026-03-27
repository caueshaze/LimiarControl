import { useDeferredValue, useEffect, useState } from "react";

import type {
  BaseSpell,
  BaseSpellWritePayload,
  CastingTimeType,
  ResolutionType,
  SaveSuccessOutcome,
  SpellDamageType,
  SpellSavingThrow,
  SpellSchool,
  SpellSource,
  TargetMode,
  UpcastMode,
} from "../../entities/base-spell";
import {
  CastingTimeType as CastingTimeTypeValues,
  ResolutionType as ResolutionTypeValues,
  SaveSuccessOutcome as SaveSuccessOutcomeValues,
  SpellDamageType as SpellDamageTypeValues,
  SpellSavingThrow as SpellSavingThrowValues,
  SpellSchool as SpellSchoolValues,
  SpellSource as SpellSourceValues,
  TargetMode as TargetModeValues,
  UpcastMode as UpcastModeValues,
} from "../../entities/base-spell";
import { adminBaseSpellsRepo } from "../../shared/api/adminBaseSpellsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  localizeSaveSuccessOutcome,
  localizeSpellAdminValue,
  localizeSpellSchool,
} from "../../shared/i18n/domainLabels";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type ActiveFilter = "all" | "active" | "inactive";
type LevelFilter = "ALL" | number;
type SchoolFilter = "ALL" | SpellSchool;

const SYSTEM_OPTIONS = ["DND5E"] as const;
const LEVEL_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;
const SCHOOL_OPTIONS = Object.values(SpellSchoolValues);
const CASTING_TIME_TYPE_OPTIONS = Object.values(CastingTimeTypeValues);
const TARGET_MODE_OPTIONS = Object.values(TargetModeValues);
const RESOLUTION_TYPE_OPTIONS = Object.values(ResolutionTypeValues);
const DAMAGE_TYPE_OPTIONS = Object.values(SpellDamageTypeValues);
const SAVING_THROW_OPTIONS = Object.values(SpellSavingThrowValues);
const SAVE_SUCCESS_OUTCOME_OPTIONS = Object.values(SaveSuccessOutcomeValues);
const UPCAST_MODE_OPTIONS = Object.values(UpcastModeValues);
const SOURCE_OPTIONS = Object.values(SpellSourceValues);
const CLASS_OPTIONS = [
  "Bard",
  "Cleric",
  "Druid",
  "Paladin",
  "Ranger",
  "Sorcerer",
  "Warlock",
  "Wizard",
] as const;
const COMPONENT_OPTIONS = ["V", "S", "M"] as const;

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

type FormState = {
  system: BaseSpell["system"];
  canonicalKey: string;
  nameEn: string;
  namePt: string;
  descriptionEn: string;
  descriptionPt: string;
  level: number;
  school: SpellSchool;
  classesJson: string[];
  castingTimeType: CastingTimeType | "";
  castingTime: string;
  rangeMeters: string;
  rangeText: string;
  targetMode: TargetMode | "";
  duration: string;
  componentsJson: string[];
  materialComponentText: string;
  concentration: boolean;
  ritual: boolean;
  resolutionType: ResolutionType | "";
  savingThrow: SpellSavingThrow | "";
  saveSuccessOutcome: SaveSuccessOutcome | "";
  damageDice: string;
  damageType: SpellDamageType | "";
  healDice: string;
  upcastMode: UpcastMode | "";
  upcastValue: string;
  source: SpellSource;
  sourceRef: string;
  isSrd: boolean;
  isActive: boolean;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-violet-400/50 focus:outline-none";
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

const parseOptionalInteger = (
  value: string,
  label: string,
): { value?: number; error?: string } => {
  const normalized = value.trim();
  if (!normalized) return {};
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || !Number.isInteger(parsed))
    return { error: `${label} precisa ser inteiro.` };
  return { value: parsed };
};

const createEmptyForm = (): FormState => ({
  system: "DND5E",
  canonicalKey: "",
  nameEn: "",
  namePt: "",
  descriptionEn: "",
  descriptionPt: "",
  level: 0,
  school: SpellSchoolValues.EVOCATION,
  classesJson: [],
  castingTimeType: CastingTimeTypeValues.ACTION,
  castingTime: "",
  rangeMeters: "",
  rangeText: "",
  targetMode: "",
  duration: "",
  componentsJson: [],
  materialComponentText: "",
  concentration: false,
  ritual: false,
  resolutionType: "",
  savingThrow: "",
  saveSuccessOutcome: "",
  damageDice: "",
  damageType: "",
  healDice: "",
  upcastMode: UpcastModeValues.NONE,
  upcastValue: "",
  source: SpellSourceValues.ADMIN_PANEL,
  sourceRef: "",
  isSrd: false,
  isActive: true,
});

const formFromSpell = (spell: BaseSpell): FormState => ({
  system: spell.system,
  canonicalKey: spell.canonicalKey,
  nameEn: spell.nameEn,
  namePt: spell.namePt ?? "",
  descriptionEn: spell.descriptionEn,
  descriptionPt: spell.descriptionPt ?? "",
  level: spell.level,
  school: spell.school,
  classesJson: spell.classesJson ?? [],
  castingTimeType: spell.castingTimeType ?? "",
  castingTime: spell.castingTime ?? "",
  rangeMeters: spell.rangeMeters != null ? String(spell.rangeMeters) : "",
  rangeText: spell.rangeText ?? "",
  targetMode: spell.targetMode ?? "",
  duration: spell.duration ?? "",
  componentsJson: spell.componentsJson ?? [],
  materialComponentText: spell.materialComponentText ?? "",
  concentration: spell.concentration,
  ritual: spell.ritual,
  resolutionType: spell.resolutionType ?? "",
  savingThrow: spell.savingThrow ?? "",
  saveSuccessOutcome: spell.saveSuccessOutcome ?? "",
  damageDice: spell.damageDice ?? "",
  damageType: spell.damageType ?? "",
  healDice: spell.healDice ?? "",
  upcastMode: spell.upcastMode ?? "",
  upcastValue: spell.upcastValue ?? "",
  source: spell.source ?? SpellSourceValues.ADMIN_PANEL,
  sourceRef: spell.sourceRef ?? "",
  isSrd: spell.isSrd,
  isActive: spell.isActive,
});

const buildPayload = (
  form: FormState,
  isNew: boolean,
): { payload?: BaseSpellWritePayload; error?: string } => {
  const canonicalKey = normalizeCanonicalKey(form.canonicalKey);
  if (!canonicalKey) return { error: "Canonical key é obrigatório." };

  const nameEn = normalizeOptionalText(form.nameEn);
  if (!nameEn) return { error: "Nome EN é obrigatório." };

  const descriptionEn = normalizeOptionalText(form.descriptionEn);
  if (!descriptionEn) return { error: "Descrição EN é obrigatória." };

  const rangeMeters = parseOptionalInteger(form.rangeMeters, "Alcance (m)");
  if (rangeMeters.error) return { error: rangeMeters.error };
  if (rangeMeters.value !== undefined && rangeMeters.value < 0)
    return { error: "Alcance (m) não pode ser negativo." };

  const showSavingThrow = form.resolutionType === "saving_throw";
  const showHealDice = form.resolutionType === "heal";
  const showDamage =
    form.resolutionType === "spell_attack" ||
    form.resolutionType === "saving_throw" ||
    form.resolutionType === "automatic";

  if (showSavingThrow && !form.savingThrow) {
    return { error: "Saving throw ability é obrigatória para resolutionType saving_throw." };
  }
  if (showHealDice && !form.healDice.trim()) {
    return { error: "Heal dice é obrigatório para resolutionType heal." };
  }

  return {
    payload: {
      ...(isNew
        ? { system: form.system, canonicalKey }
        : {}),
      nameEn,
      namePt: normalizeOptionalText(form.namePt) ?? null,
      descriptionEn,
      descriptionPt: normalizeOptionalText(form.descriptionPt) ?? null,
      level: form.level,
      school: form.school,
      classesJson: form.classesJson.length > 0 ? form.classesJson : null,
      castingTimeType: form.castingTimeType || null,
      castingTime: normalizeOptionalText(form.castingTime) ?? null,
      rangeMeters: rangeMeters.value ?? null,
      rangeText: normalizeOptionalText(form.rangeText) ?? null,
      targetMode: form.targetMode || null,
      duration: normalizeOptionalText(form.duration) ?? null,
      componentsJson: form.componentsJson.length > 0 ? form.componentsJson : null,
      materialComponentText:
        form.componentsJson.includes("M")
          ? normalizeOptionalText(form.materialComponentText) ?? null
          : null,
      concentration: form.concentration,
      ritual: form.ritual,
      resolutionType: form.resolutionType || null,
      savingThrow: showSavingThrow ? form.savingThrow || null : null,
      saveSuccessOutcome:
        showSavingThrow ? form.saveSuccessOutcome || null : null,
      damageDice: showDamage ? normalizeOptionalText(form.damageDice) ?? null : null,
      damageType: showDamage ? form.damageType || null : null,
      healDice: showHealDice ? normalizeOptionalText(form.healDice) ?? null : null,
      upcastMode: form.upcastMode || null,
      upcastValue:
        form.upcastMode && form.upcastMode !== "none"
          ? normalizeOptionalText(form.upcastValue) ?? null
          : null,
      source: form.source,
      sourceRef: normalizeOptionalText(form.sourceRef) ?? null,
      isSrd: form.isSrd,
      isActive: form.isActive,
    },
  };
};

const toggleListValue = (current: string[], value: string) =>
  current.includes(value)
    ? current.filter((entry) => entry !== value)
    : [...current, value];

const SCHOOL_COLORS: Record<string, string> = {
  abjuration: "text-blue-300 border-blue-400/30 bg-blue-400/10",
  conjuration: "text-yellow-300 border-yellow-400/30 bg-yellow-400/10",
  divination: "text-cyan-300 border-cyan-400/30 bg-cyan-400/10",
  enchantment: "text-pink-300 border-pink-400/30 bg-pink-400/10",
  evocation: "text-red-300 border-red-400/30 bg-red-400/10",
  illusion: "text-purple-300 border-purple-400/30 bg-purple-400/10",
  necromancy: "text-green-300 border-green-400/30 bg-green-400/10",
  transmutation: "text-orange-300 border-orange-400/30 bg-orange-400/10",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const SystemSpellCatalogPage = () => {
  const { locale, t } = useLocale();
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

  // Conditional field visibility
  const showSavingThrowFields = form.resolutionType === "saving_throw";
  const showDamageFields =
    form.resolutionType === "spell_attack" ||
    form.resolutionType === "saving_throw" ||
    form.resolutionType === "automatic";
  const showHealFields = form.resolutionType === "heal";
  const showUpcastValue = Boolean(form.upcastMode) && form.upcastMode !== "none";
  const showMaterialComponent = form.componentsJson.includes("M");

  const loadSpells = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminBaseSpellsRepo.list({
        system: "DND5E",
        level: levelFilter === "ALL" ? undefined : levelFilter,
        school: schoolFilter === "ALL" ? undefined : schoolFilter,
        search: deferredSearch.trim() || undefined,
        isActive:
          activeFilter === "all" ? undefined : activeFilter === "active",
      });
      setSpells(result);
      setSelectedSpellId((currentId) =>
        currentId && result.some((s) => s.id === currentId)
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
        saveError instanceof Error
          ? saveError.message
          : "Falha ao salvar a magia.";
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
        deleteError instanceof Error
          ? deleteError.message
          : "Falha ao remover a magia.";
      setError(message);
      setLoadingMessage(null);
    }
  };

  const formatSpellChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeSpellAdminValue(value, locale);
  const selectedLabel = selectedSpellId ? t("catalog.edit") : t("catalog.createAction");

  return (
    <section className="space-y-6">
      {/* Header */}
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
        {/* Sidebar: filters + list */}
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
                placeholder={t("catalog.admin.filters.searchSpellsPlaceholder")}
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  {t("catalog.admin.filters.level")}
                </span>
                <select
                  value={String(levelFilter)}
                  onChange={(event) =>
                    setLevelFilter(
                      event.target.value === "ALL"
                        ? "ALL"
                        : Number(event.target.value),
                    )
                  }
                  className={`${inputClassName} mt-2`}
                >
                  <option value="ALL">{t("catalog.admin.filters.allLevels")}</option>
                  {LEVEL_OPTIONS.map((level) => (
                    <option key={level} value={level}>
                      {level === 0 ? t("catalog.spells.cantrip") : `${t("catalog.spells.levelLabel")} ${level}`}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  {t("catalog.spells.schoolFilterLabel")}
                </span>
                <select
                  value={schoolFilter}
                  onChange={(event) =>
                    setSchoolFilter(event.target.value as SchoolFilter)
                  }
                  className={`${inputClassName} mt-2`}
                >
                  <option value="ALL">{t("catalog.admin.filters.allCategories")}</option>
                  {SCHOOL_OPTIONS.map((school) => (
                    <option key={school} value={school}>
                      {localizeSpellSchool(school, locale)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

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

          <div className="rounded-3xl border border-white/8 bg-black/20 px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.filtersTitle")}
            </p>
            <p className="mt-2 text-2xl font-black text-white">{spells.length}</p>
            <p className="text-sm text-slate-400">{t("catalog.spells.filtersResults")}</p>
          </div>

          {loading && (
            <div className="rounded-3xl border border-white/8 bg-black/20 px-4 py-6 text-sm text-slate-400">
              {t("catalog.spells.loading")}
            </div>
          )}

          {!loading && (
            <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
              {spells.map((spell) => (
                <button
                  key={spell.id}
                  type="button"
                  onClick={() => handleSelectSpell(spell)}
                  className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
                    selectedSpellId === spell.id
                      ? "border-violet-300/40 bg-violet-300/10"
                      : "border-white/8 bg-black/20 hover:border-white/15 hover:bg-white/5"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {spell.namePt || spell.nameEn}
                      </p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.22em] text-slate-500">
                        {spell.canonicalKey}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${
                        spell.isActive
                          ? "bg-emerald-400/12 text-emerald-200"
                          : "bg-rose-400/12 text-rose-200"
                      }`}
                    >
                      {spell.isActive ? t("catalog.admin.table.active") : t("catalog.admin.table.inactive")}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                    <span
                      className={`rounded-full border px-2 py-1 ${
                        SCHOOL_COLORS[spell.school] ?? "border-white/10"
                      }`}
                    >
                      {localizeSpellSchool(spell.school, locale)}
                    </span>
                    <span className="rounded-full border border-white/10 px-2 py-1">
                      {spell.level === 0
                        ? t("catalog.spells.cantrip")
                        : `${t("catalog.spells.levelLabel")} ${spell.level}`}
                    </span>
                    {spell.concentration && (
                      <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-amber-200">
                        C
                      </span>
                    )}
                    {spell.ritual && (
                      <span className="rounded-full border border-teal-400/30 bg-teal-400/10 px-2 py-1 text-teal-200">
                        R
                      </span>
                    )}
                  </div>
                </button>
              ))}
              {spells.length === 0 && (
                <div className="rounded-[24px] border border-dashed border-white/10 px-4 py-8 text-sm text-slate-400">
                  {t("catalog.spells.empty")}
                </div>
              )}
            </div>
          )}
        </aside>

        {/* Main: Editor form */}
        <div className={`${panelClassName} space-y-5`}>
          <div className="flex flex-col gap-2 border-b border-white/8 pb-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                {t("catalog.edit")}
              </p>
              <h2 className="mt-1 text-2xl font-black tracking-tight text-white">
                {selectedLabel}
              </h2>
            </div>
            {loadingMessage && (
              <p className="text-sm text-violet-200">{loadingMessage}</p>
            )}
          </div>

          {error && (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          )}

          {/* Identity */}
          <div className="grid gap-4 md:grid-cols-3">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.admin.table.system")}
              </span>
              <select
                value={form.system}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    system: event.target.value as BaseSpell["system"],
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                {SYSTEM_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {formatSpellChoiceLabel(s)}
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
                  setForm((c) => ({ ...c, canonicalKey: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="fireball"
              />
            </label>

            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.admin.table.level")}
              </span>
              <select
                value={form.level}
                onChange={(event) =>
                  setForm((c) => ({ ...c, level: Number(event.target.value) }))
                }
                className={`${inputClassName} mt-2`}
              >
                {LEVEL_OPTIONS.map((level) => (
                  <option key={level} value={level}>
                    {level === 0 ? t("catalog.spells.cantrip") : `${t("catalog.spells.levelLabel")} ${level}`}
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
                  setForm((c) => ({ ...c, nameEn: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="Fireball"
              />
            </label>
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("catalog.admin.table.namePt")}
              </span>
              <input
                value={form.namePt}
                onChange={(event) =>
                  setForm((c) => ({ ...c, namePt: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="Bola de Fogo"
              />
            </label>
          </div>

          {/* School */}
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.admin.table.school")}
            </span>
            <select
              value={form.school}
              onChange={(event) =>
                setForm((c) => ({
                  ...c,
                  school: event.target.value as SpellSchool,
                }))
              }
              className={`${inputClassName} mt-2`}
            >
              {SCHOOL_OPTIONS.map((school) => (
                <option key={school} value={school}>
                  {localizeSpellSchool(school, locale)}
                </option>
              ))}
            </select>
          </label>

          {/* Classes */}
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Classes
            </span>
            <div className="mt-2 flex flex-wrap gap-2">
              {CLASS_OPTIONS.map((cls) => (
                <button
                  key={cls}
                  type="button"
                  onClick={() =>
                    setForm((c) => ({
                      ...c,
                      classesJson: toggleListValue(c.classesJson, cls),
                    }))
                  }
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                    form.classesJson.includes(cls)
                      ? "border-violet-300/40 bg-violet-400/15 text-violet-100"
                      : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
                  }`}
                >
                  {cls}
                </button>
              ))}
            </div>
          </div>

          {/* Casting */}
          <div className="grid gap-4 md:grid-cols-4">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Casting time type
              </span>
              <select
                value={form.castingTimeType}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    castingTimeType: event.target.value as CastingTimeType | "",
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {CASTING_TIME_TYPE_OPTIONS.map((ctt) => (
                  <option key={ctt} value={ctt}>
                    {formatSpellChoiceLabel(ctt)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Casting time (editorial)
              </span>
              <input
                value={form.castingTime}
                onChange={(event) =>
                  setForm((c) => ({ ...c, castingTime: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="1 action"
              />
            </label>

            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Alcance (m)
              </span>
              <input
                type="number"
                min={0}
                value={form.rangeMeters}
                onChange={(event) =>
                  setForm((c) => ({ ...c, rangeMeters: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="0"
              />
            </label>

            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Range text (editorial)
              </span>
              <input
                value={form.rangeText}
                onChange={(event) =>
                  setForm((c) => ({ ...c, rangeText: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="120 ft / Self"
              />
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Target mode
              </span>
              <select
                value={form.targetMode}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    targetMode: event.target.value as TargetMode | "",
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                <option value="">—</option>
                {TARGET_MODE_OPTIONS.map((tm) => (
                  <option key={tm} value={tm}>
                    {formatSpellChoiceLabel(tm)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Duração (editorial)
              </span>
              <input
                value={form.duration}
                onChange={(event) =>
                  setForm((c) => ({ ...c, duration: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="Instantaneous"
              />
            </label>

            <div className="flex items-end gap-3 pb-1">
              <button
                type="button"
                onClick={() =>
                  setForm((c) => ({
                    ...c,
                    concentration: !c.concentration,
                  }))
                }
                className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
                  form.concentration
                    ? "border-amber-300/40 bg-amber-400/15 text-amber-100"
                    : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
                }`}
              >
                Concentration
              </button>
              <button
                type="button"
                onClick={() =>
                  setForm((c) => ({ ...c, ritual: !c.ritual }))
                }
                className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
                  form.ritual
                    ? "border-teal-300/40 bg-teal-400/15 text-teal-100"
                    : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
                }`}
              >
                Ritual
              </button>
            </div>
          </div>

          {/* Components */}
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Componentes
            </span>
            <div className="mt-2 flex flex-wrap gap-2">
              {COMPONENT_OPTIONS.map((comp) => (
                <button
                  key={comp}
                  type="button"
                  onClick={() =>
                    setForm((c) => ({
                      ...c,
                      componentsJson: toggleListValue(c.componentsJson, comp),
                    }))
                  }
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                    form.componentsJson.includes(comp)
                      ? "border-violet-300/40 bg-violet-400/15 text-violet-100"
                      : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
                  }`}
                >
                  {comp}
                </button>
              ))}
            </div>
          </div>

          {showMaterialComponent && (
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Material component
              </span>
              <input
                value={form.materialComponentText}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    materialComponentText: event.target.value,
                  }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="a tiny ball of bat guano and sulfur"
              />
            </label>
          )}

          {/* Resolution */}
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
              <>
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

                <label className="block">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    {t("catalog.spells.form.saveSuccessOutcome")}
                  </span>
                  <select
                    value={form.saveSuccessOutcome}
                    onChange={(event) =>
                      setForm((c) => ({
                        ...c,
                        saveSuccessOutcome: event.target
                          .value as SaveSuccessOutcome | "",
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
              </>
            )}
          </div>

          {/* Effect: damage */}
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

          {/* Effect: heal */}
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

          {/* Upcast */}
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

            {showUpcastValue && (
              <label className="block">
                <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Upcast value
                </span>
                <input
                  value={form.upcastValue}
                  onChange={(event) =>
                    setForm((c) => ({
                      ...c,
                      upcastValue: event.target.value,
                    }))
                  }
                  className={`${inputClassName} mt-2`}
                  placeholder="1d6"
                />
              </label>
            )}
          </div>

          {/* Descriptions */}
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Descrição EN
              </span>
              <textarea
                value={form.descriptionEn}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    descriptionEn: event.target.value,
                  }))
                }
                className={`${inputClassName} mt-2 min-h-28`}
              />
            </label>
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Descrição PT
              </span>
              <textarea
                value={form.descriptionPt}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    descriptionPt: event.target.value,
                  }))
                }
                className={`${inputClassName} mt-2 min-h-28`}
              />
            </label>
          </div>

          {/* Metadata */}
          <div className="grid gap-4 md:grid-cols-3">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Source
              </span>
              <select
                value={form.source}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    source: event.target.value as SpellSource,
                  }))
                }
                className={`${inputClassName} mt-2`}
              >
                {SOURCE_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {formatSpellChoiceLabel(s)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Source ref
              </span>
              <input
                value={form.sourceRef}
                onChange={(event) =>
                  setForm((c) => ({ ...c, sourceRef: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="PHB p.241"
              />
            </label>

            <div className="flex items-end gap-3 pb-1">
              <button
                type="button"
                onClick={() => setForm((c) => ({ ...c, isSrd: !c.isSrd }))}
                className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
                  form.isSrd
                    ? "border-emerald-300/40 bg-emerald-400/15 text-emerald-100"
                    : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
                }`}
              >
                SRD
              </button>
              <button
                type="button"
                onClick={() =>
                  setForm((c) => ({ ...c, isActive: !c.isActive }))
                }
                className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
                  form.isActive
                    ? "border-emerald-300/40 bg-emerald-400/15 text-emerald-100"
                    : "border-rose-300/40 bg-rose-400/15 text-rose-100"
                }`}
              >
                {form.isActive ? "Ativo" : "Inativo"}
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3 border-t border-white/8 pt-4">
            <button
              type="button"
              onClick={handleSave}
              className="rounded-2xl border border-violet-400/30 bg-violet-400/12 px-5 py-3 text-sm font-semibold text-violet-100 transition hover:bg-violet-400/18"
            >
              {selectedSpellId ? "Salvar alterações" : "Criar magia"}
            </button>
            {selectedSpellId && (
              <button
                type="button"
                onClick={handleDelete}
                className="rounded-2xl border border-rose-400/30 bg-rose-400/8 px-5 py-3 text-sm font-semibold text-rose-200 transition hover:bg-rose-400/15"
              >
                Remover
              </button>
            )}
            <button
              type="button"
              onClick={handleCreateNew}
              className="rounded-2xl border border-white/10 bg-white/4 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-white/20 hover:bg-white/8"
            >
              Limpar
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};
