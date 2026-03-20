import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  featuresAndTraits: CharacterSheet["featuresAndTraits"];
  notes: CharacterSheet["notes"];
  set: SheetActions["set"];
  readOnly?: boolean;
};

const textarea =
  "w-full rounded-xl border border-white/10 bg-void-900/50 px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:border-limiar-500 focus:outline-none focus:ring-1 focus:ring-limiar-500/50 resize-none";

export const FeaturesTraits = ({ featuresAndTraits, notes, set, readOnly = false }: Props) => {
  const { t } = useLocale();

  return (
    <>
      <Section title={t("sheet.features.title")} color="bg-emerald-500">
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
