import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { SpellCatalogFormFields } from "../../features/shop/components/SpellCatalogFormFields";
import {
  buildSpellCreatePayload,
  createEmptySpellEditorState,
  getSpellCatalogEditorVariantErrors,
  normalizeSpellCanonicalKey,
} from "../../features/shop/utils/spellCatalogForm";
import type { CampaignSpellCreatePayload } from "../../shared/api/campaignSpellsRepo";
import { campaignSpellsRepo } from "../../shared/api/campaignSpellsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";

export const CatalogSpellNewPage = () => {
  const { selectedCampaignId } = useCampaigns();
  const navigate = useNavigate();
  const { locale, t } = useLocale();
  const { toast, showToast, clearToast } = useToast();

  const [state, setState] = useState(createEmptySpellEditorState);
  const [isSaving, setIsSaving] = useState(false);

  if (!selectedCampaignId) {
    return null;
  }

  const canSave =
    Boolean(normalizeSpellCanonicalKey(state.canonicalKey)) &&
    Boolean(state.nameEn.trim()) &&
    Boolean(state.descriptionEn.trim()) &&
    state.level >= 0 &&
    state.level <= 9 &&
    getSpellCatalogEditorVariantErrors(state, locale).length === 0;

  const handleCreate = async () => {
    if (!canSave || isSaving) return;

    setIsSaving(true);
    try {
      await campaignSpellsRepo.create(selectedCampaignId, buildSpellCreatePayload(state, locale) as CampaignSpellCreatePayload);
      showToast({
        variant: "success",
        title: t("catalog.spells.createSuccessTitle"),
        description: t("catalog.spells.createSuccessDescription"),
      });
      navigate(routes.catalogSpells);
    } catch (error) {
      showToast({
        variant: "error",
        title: t("catalog.spells.createErrorTitle"),
        description:
          error instanceof Error ? error.message : t("catalog.spells.createErrorDescription"),
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />

      <div className="mx-auto max-w-4xl">
        <div className="rounded-[28px] border border-violet-300/15 bg-[linear-gradient(180deg,rgba(14,17,31,0.92),rgba(3,7,18,0.98))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
          <div className="space-y-5">
            <div className="border-b border-white/8 pb-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-violet-200/65">
                {t("catalog.spells.formTitle")}
              </p>
              <h2 className="mt-2 text-2xl font-black tracking-tight text-white">
                {t("catalog.spells.formHeadline")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                {t("catalog.spells.formDescription")}
              </p>
            </div>

            <SpellCatalogFormFields
              state={state}
              setState={setState}
              showCanonicalKey
            />

            <div className="flex flex-wrap gap-3 border-t border-white/8 pt-4">
              <button
                type="button"
                onClick={handleCreate}
                disabled={!canSave || isSaving}
                className={`rounded-full px-5 py-3 text-sm font-semibold ${
                  !canSave || isSaving
                    ? "cursor-not-allowed border border-white/8 text-slate-600"
                    : "border border-violet-300/25 bg-violet-400/12 text-violet-100 hover:bg-violet-400/18"
                }`}
              >
                {isSaving ? t("catalog.spells.creatingAction") : t("catalog.spells.createAction")}
              </button>
              <button
                type="button"
                onClick={() => navigate(routes.catalogSpells)}
                className="rounded-full border border-white/10 bg-white/4 px-5 py-3 text-sm font-semibold text-slate-200 hover:border-white/20 hover:bg-white/8"
              >
                {t("catalog.cancel")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
