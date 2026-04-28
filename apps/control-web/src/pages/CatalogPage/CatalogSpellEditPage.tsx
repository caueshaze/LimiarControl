import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { useCampaignSpells } from "../../features/shop/hooks/useCampaignSpells";
import { SpellCatalogFormFields } from "../../features/shop/components/SpellCatalogFormFields";
import {
  buildSpellUpdatePayload,
  createSpellEditorState,
  getUnsupportedSpellEditorValues,
  type SpellCatalogEditorState,
} from "../../features/shop/utils/spellCatalogForm";
import { campaignSpellsRepo } from "../../shared/api/campaignSpellsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";

export const CatalogSpellEditPage = () => {
  const { spellId } = useParams<{ spellId: string }>();
  const { selectedCampaignId } = useCampaigns();
  const navigate = useNavigate();
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();

  const {
    spells,
    loading: spellsLoading,
    refetch: refetchSpells,
  } = useCampaignSpells({ campaignId: selectedCampaignId, auto: true });

  const spell = spells.find((s) => s.id === spellId) ?? null;
  const [state, setState] = useState(() =>
    spell ? createSpellEditorState(spell) : null,
  );
  const [isSaving, setIsSaving] = useState(false);
  const unsupportedValues = spell ? getUnsupportedSpellEditorValues(spell) : [];

  useEffect(() => {
    if (spell) {
      setState(createSpellEditorState(spell));
    }
  }, [spell]);

  if (!selectedCampaignId) {
    return null;
  }

  if (spellsLoading && !spell) {
    return (
      <section className="space-y-6">
        <div className="mx-auto max-w-4xl rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(14,17,31,0.92),rgba(3,7,18,0.98))] p-8 text-center">
          <p className="text-sm text-slate-400">{t("catalog.spells.loading")}</p>
        </div>
      </section>
    );
  }

  if (!spell || !state) {
    return (
      <section className="space-y-6">
        <div className="mx-auto max-w-4xl rounded-[28px] border border-rose-400/15 bg-rose-500/5 p-8 text-center">
          <p className="text-sm text-rose-200">{t("catalog.spells.loadErrorDescription")}</p>
          <button
            type="button"
            onClick={() => navigate(routes.catalogSpells)}
            className="mt-4 rounded-full border border-white/10 bg-white/4 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-white/8"
          >
            {t("catalog.openLibrary")}
          </button>
        </div>
      </section>
    );
  }

  const formState = state;
  const setFormState = setState as React.Dispatch<React.SetStateAction<SpellCatalogEditorState>>;

  const canSave =
    Boolean(formState.nameEn.trim()) &&
    Boolean(formState.descriptionEn.trim()) &&
    formState.level >= 0 &&
    formState.level <= 9;

  const handleSave = async () => {
    if (!canSave || isSaving) return;

    setIsSaving(true);
    try {
      await campaignSpellsRepo.update(
        selectedCampaignId,
        spell.id,
        buildSpellUpdatePayload(formState),
      );
      await refetchSpells();
      showToast({
        variant: "success",
        title: t("catalog.spells.updateSuccessTitle"),
        description: t("catalog.spells.updateSuccessDescription"),
      });
      navigate(routes.catalogSpells);
    } catch (error) {
      showToast({
        variant: "error",
        title: t("catalog.spells.updateErrorTitle"),
        description:
          error instanceof Error ? error.message : t("catalog.spells.updateErrorDescription"),
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />

      <div className="mx-auto max-w-4xl">
        <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(14,17,31,0.92),rgba(3,7,18,0.98))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
          <div className="space-y-5">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/8 pb-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  {t("catalog.edit")}
                </p>
                <h2 className="mt-1 text-2xl font-black tracking-tight text-white">
                  {spell.nameEn}
                </h2>
              </div>
              <span className="rounded-full border border-white/10 bg-white/4 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-300">
                {spell.canonicalKey}
              </span>
            </div>

            <SpellCatalogFormFields
              state={formState}
              setState={setFormState}
              unsupportedValues={unsupportedValues}
            />

            <div className="flex flex-wrap gap-3 border-t border-white/8 pt-4">
              <button
                type="button"
                onClick={handleSave}
                disabled={!canSave || isSaving}
                className={`rounded-full px-5 py-3 text-sm font-semibold ${
                  !canSave || isSaving
                    ? "cursor-not-allowed border border-white/8 text-slate-600"
                    : "border border-violet-300/25 bg-violet-400/12 text-violet-100 hover:bg-violet-400/18"
                }`}
              >
                {isSaving ? t("catalog.saving") : t("catalog.save")}
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
