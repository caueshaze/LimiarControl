import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  classFeatures: CharacterSheet["classFeatures"];
  featuresAndTraits: CharacterSheet["featuresAndTraits"];
  notes: CharacterSheet["notes"];
  set: SheetActions["set"];
  readOnly?: boolean;
};

const textarea =
  "w-full rounded-xl border border-white/10 bg-void-900/50 px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:border-limiar-500 focus:outline-none focus:ring-1 focus:ring-limiar-500/50 resize-none";

export const FeaturesTraits = ({ classFeatures, featuresAndTraits, notes, set, readOnly = false }: Props) => {
  const { t } = useLocale();

  return (
    <>
      <Section title={t("sheet.features.title")} color="bg-emerald-500">
        {classFeatures.length > 0 && (
          <div className="mb-4 space-y-2">
            {classFeatures.map((feature) => (
              <div
                key={feature.id}
                className="rounded-xl border border-emerald-500/15 bg-emerald-500/8 px-3 py-2"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-emerald-100">{feature.label}</p>
                  <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-emerald-300/80">
                    Nv. {feature.levelGranted}
                  </span>
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-300">{feature.description}</p>
              </div>
            ))}
          </div>
        )}
        <textarea
          rows={8}
          placeholder={t("sheet.features.placeholder")}
          value={featuresAndTraits}
          disabled={readOnly}
          onChange={(e) => set("featuresAndTraits", e.target.value)}
          className={`${textarea} ${readOnly ? "opacity-70" : ""}`}
        />
      </Section>

      <Section title={t("sheet.features.notesTitle")} color="bg-slate-500">
        <textarea
          rows={5}
          placeholder={t("sheet.features.notesPlaceholder")}
          value={notes}
          disabled={readOnly}
          onChange={(e) => set("notes", e.target.value)}
          className={`${textarea} ${readOnly ? "opacity-70" : ""}`}
        />
      </Section>
    </>
  );
};
