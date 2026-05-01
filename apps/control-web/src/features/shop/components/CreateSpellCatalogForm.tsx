import { useState } from "react";
import type { CampaignSpellCreatePayload } from "../../../shared/api/campaignSpellsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { SpellCatalogFormFields } from "./SpellCatalogFormFields";
import {
  buildSpellCreatePayload,
  createEmptySpellEditorState,
  getSpellCatalogEditorVariantErrors,
  normalizeSpellCanonicalKey,
} from "../utils/spellCatalogForm";

type Props = {
  onCreate: (payload: CampaignSpellCreatePayload) => boolean | Promise<boolean>;
};

export const CreateSpellCatalogForm = ({ onCreate }: Props) => {
  const { t } = useLocale();
  const [state, setState] = useState(createEmptySpellEditorState);
  const [isSaving, setIsSaving] = useState(false);

  const canSave =
    Boolean(normalizeSpellCanonicalKey(state.canonicalKey)) &&
    Boolean(state.nameEn.trim()) &&
    Boolean(state.descriptionEn.trim()) &&
    state.level >= 0 &&
    state.level <= 9 &&
    getSpellCatalogEditorVariantErrors(state).length === 0;

  const handleCreate = async () => {
    if (!canSave || isSaving) {
      return;
    }

    setIsSaving(true);
    try {
      const created = await onCreate(buildSpellCreatePayload(state));
      if (created) {
        setState(createEmptySpellEditorState());
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <article className="relative overflow-hidden rounded-[22px] border border-violet-300/15 bg-[linear-gradient(180deg,rgba(18,24,48,0.98),rgba(4,10,28,0.98))] p-5 shadow-[0_18px_50px_rgba(2,6,23,0.28)]">
      <div className="space-y-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-violet-200/65">
            {t("catalog.spells.formTitle")}
          </p>
          <h3 className="mt-2 text-xl font-bold text-white">
            {t("catalog.spells.formHeadline")}
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {t("catalog.spells.formDescription")}
          </p>
        </div>

        <SpellCatalogFormFields
          state={state}
          setState={setState}
          showCanonicalKey
        />

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            onClick={handleCreate}
            disabled={!canSave || isSaving}
            className={`rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${
              !canSave || isSaving
                ? "cursor-not-allowed border border-white/8 text-slate-600"
                : "border border-violet-300/25 bg-violet-400/12 text-violet-100 hover:bg-violet-400/18"
            }`}
          >
            {isSaving ? t("catalog.spells.creatingAction") : t("catalog.spells.createAction")}
          </button>
        </div>
      </div>
    </article>
  );
};
