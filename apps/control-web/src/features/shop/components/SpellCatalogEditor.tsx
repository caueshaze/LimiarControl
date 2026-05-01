import { useEffect, useState } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import type { BaseSpellUpdatePayload } from "../../../shared/api/baseSpellsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { SpellCatalogFormFields } from "./SpellCatalogFormFields";
import {
  buildSpellUpdatePayload,
  createSpellEditorState,
  getSpellCatalogEditorVariantErrors,
  getUnsupportedSpellEditorValues,
} from "../utils/spellCatalogForm";

type Props = {
  spell: BaseSpell;
  onSave: (spellId: string, payload: BaseSpellUpdatePayload) => boolean | Promise<boolean>;
  onCancel: () => void;
};

export const SpellCatalogEditor = ({ spell, onSave, onCancel }: Props) => {
  const { t } = useLocale();
  const [state, setState] = useState(() => createSpellEditorState(spell));
  const [isSaving, setIsSaving] = useState(false);
  const unsupportedValues = getUnsupportedSpellEditorValues(spell);

  useEffect(() => {
    setState(createSpellEditorState(spell));
  }, [spell]);

  const canSave =
    Boolean(state.nameEn.trim()) &&
    Boolean(state.descriptionEn.trim()) &&
    state.level >= 0 &&
    state.level <= 9 &&
    getSpellCatalogEditorVariantErrors(state).length === 0;

  const handleSave = async () => {
    if (!canSave || isSaving) {
      return;
    }

    setIsSaving(true);
    try {
      const updated = await onSave(spell.id, buildSpellUpdatePayload(state));
      if (updated) {
        onCancel();
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <article className="relative overflow-hidden rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(8,12,28,0.96),rgba(2,6,23,0.98))] p-5 shadow-[0_18px_50px_rgba(2,6,23,0.3)]">
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("catalog.edit")}
            </p>
            <h3 className="mt-2 text-xl font-bold text-white">{spell.nameEn}</h3>
          </div>
          <span className="rounded-full border border-white/10 bg-white/4 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-300">
            {spell.canonicalKey}
          </span>
        </div>

        <SpellCatalogFormFields
          state={state}
          setState={setState}
          unsupportedValues={unsupportedValues}
        />

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave || isSaving}
            className={`rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${
              !canSave || isSaving
                ? "cursor-not-allowed border border-white/8 text-slate-600"
                : "border border-violet-300/25 bg-violet-400/12 text-violet-100 hover:bg-violet-400/18"
            }`}
          >
            {isSaving ? t("catalog.saving") : t("catalog.save")}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full border border-white/10 bg-white/4 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 hover:border-white/20 hover:bg-white/8"
          >
            {t("catalog.cancel")}
          </button>
        </div>
      </div>
    </article>
  );
};
