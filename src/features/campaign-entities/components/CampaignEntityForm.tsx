import { useState } from "react";
import type { CampaignEntity, CampaignEntityPayload, EntityCategory } from "../../../entities/campaign-entity";
import { useLocale } from "../../../shared/hooks/useLocale";

const CATEGORIES: EntityCategory[] = ["npc", "enemy", "creature", "ally"];

const emptyPayload = (): CampaignEntityPayload => ({
  name: "",
  category: "npc",
  description: "",
  imageUrl: "",
  baseHp: null,
  baseAc: null,
  stats: null,
  actions: "",
  notesPrivate: "",
  notesPublic: "",
});

type Props = {
  onSave: (payload: CampaignEntityPayload) => Promise<void> | void;
  initial?: CampaignEntity | null;
  onCancel?: () => void;
};

export const CampaignEntityForm = ({ onSave, initial, onCancel }: Props) => {
  const { t } = useLocale();
  const [form, setForm] = useState<CampaignEntityPayload>(
    initial
      ? {
          name: initial.name,
          category: initial.category,
          description: initial.description ?? "",
          imageUrl: initial.imageUrl ?? "",
          baseHp: initial.baseHp ?? null,
          baseAc: initial.baseAc ?? null,
          stats: initial.stats ?? null,
          actions: initial.actions ?? "",
          notesPrivate: initial.notesPrivate ?? "",
          notesPublic: initial.notesPublic ?? "",
        }
      : emptyPayload()
  );
  const [showStats, setShowStats] = useState(!!initial?.stats);
  const [saving, setSaving] = useState(false);

  const setField = <K extends keyof CampaignEntityPayload>(key: K, value: CampaignEntityPayload[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const setStat = (key: string, value: string) => {
    const num = value === "" ? null : Number(value);
    setForm((prev) => ({
      ...prev,
      stats: { ...(prev.stats ?? {}), [key]: num },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        ...form,
        name: form.name.trim(),
        description: form.description?.trim() || null,
        imageUrl: form.imageUrl?.trim() || null,
        actions: form.actions?.trim() || null,
        notesPrivate: form.notesPrivate?.trim() || null,
        notesPublic: form.notesPublic?.trim() || null,
        stats: showStats ? form.stats : null,
      });
      if (!initial) {
        setForm(emptyPayload());
        setShowStats(false);
      }
    } finally {
      setSaving(false);
    }
  };

  const fieldClass =
    "w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none placeholder:text-slate-600";

  const statFields = ["str", "dex", "con", "int", "wis", "cha"] as const;

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      <p className="text-sm font-semibold text-slate-100">
        {initial ? t("entity.form.editTitle") : t("entity.form.title")}
      </p>

      {/* Name + Category */}
      <div className="grid grid-cols-[1fr_auto] gap-2">
        <input
          value={form.name}
          onChange={(e) => setField("name", e.target.value)}
          placeholder={t("entity.form.name")}
          required
          className={fieldClass}
        />
        <select
          value={form.category}
          onChange={(e) => setField("category", e.target.value as EntityCategory)}
          className={`${fieldClass} w-32`}
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {t(`entity.category.${c}`)}
            </option>
          ))}
        </select>
      </div>

      {/* Description */}
      <textarea
        value={form.description ?? ""}
        onChange={(e) => setField("description", e.target.value)}
        placeholder={t("entity.form.description")}
        rows={2}
        className={fieldClass}
      />

      {/* HP / AC */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            {t("entity.form.hp")}
          </label>
          <input
            type="number"
            min={0}
            value={form.baseHp ?? ""}
            onChange={(e) => setField("baseHp", e.target.value === "" ? null : Number(e.target.value))}
            placeholder="—"
            className={fieldClass}
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            {t("entity.form.ac")}
          </label>
          <input
            type="number"
            min={0}
            value={form.baseAc ?? ""}
            onChange={(e) => setField("baseAc", e.target.value === "" ? null : Number(e.target.value))}
            placeholder="—"
            className={fieldClass}
          />
        </div>
      </div>

      {/* Stats toggle */}
      <button
        type="button"
        onClick={() => setShowStats((v) => !v)}
        className="text-xs font-semibold uppercase tracking-widest text-slate-400 hover:text-slate-200"
      >
        {showStats ? "— " : "+ "}{t("entity.form.stats")}
      </button>

      {showStats && (
        <div className="grid grid-cols-3 gap-2">
          {statFields.map((stat) => (
            <div key={stat}>
              <label className="mb-1 block text-center text-[10px] font-bold uppercase tracking-widest text-slate-500">
                {stat}
              </label>
              <input
                type="number"
                min={1}
                max={30}
                value={(form.stats as Record<string, number | null | undefined> | null)?.[stat] ?? ""}
                onChange={(e) => setStat(stat, e.target.value)}
                placeholder="10"
                className={`${fieldClass} text-center`}
              />
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div>
        <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.actions")}
        </label>
        <textarea
          value={form.actions ?? ""}
          onChange={(e) => setField("actions", e.target.value)}
          placeholder={t("entity.form.actionsPlaceholder")}
          rows={2}
          className={fieldClass}
        />
      </div>

      {/* Image URL */}
      <input
        value={form.imageUrl ?? ""}
        onChange={(e) => setField("imageUrl", e.target.value)}
        placeholder={t("entity.form.imageUrl")}
        className={fieldClass}
      />

      {/* Notes */}
      <div className="grid gap-2 lg:grid-cols-2">
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            {t("entity.form.notesPrivate")}
          </label>
          <textarea
            value={form.notesPrivate ?? ""}
            onChange={(e) => setField("notesPrivate", e.target.value)}
            placeholder={t("entity.form.notesPrivatePlaceholder")}
            rows={2}
            className={fieldClass}
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            {t("entity.form.notesPublic")}
          </label>
          <textarea
            value={form.notesPublic ?? ""}
            onChange={(e) => setField("notesPublic", e.target.value)}
            placeholder={t("entity.form.notesPublicPlaceholder")}
            rows={2}
            className={fieldClass}
          />
        </div>
      </div>

      {/* Buttons */}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving || !form.name.trim()}
          className="flex-1 rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-900 disabled:opacity-50"
        >
          {saving ? t("entity.form.saving") : t("entity.form.save")}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full border border-slate-700 px-4 py-2 text-xs text-slate-400 hover:text-slate-200"
          >
            {t("entity.form.cancel")}
          </button>
        )}
      </div>
    </form>
  );
};
