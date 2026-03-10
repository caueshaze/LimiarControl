import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";

type Props = {
  featuresAndTraits: CharacterSheet["featuresAndTraits"];
  notes: CharacterSheet["notes"];
  set: SheetActions["set"];
  readOnly?: boolean;
};

const textarea =
  "w-full rounded-xl border border-white/10 bg-void-900/50 px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:border-limiar-500 focus:outline-none focus:ring-1 focus:ring-limiar-500/50 resize-none";

export const FeaturesTraits = ({ featuresAndTraits, notes, set, readOnly = false }: Props) => (
  <>
    <Section title="Features & Traits" color="bg-emerald-500">
      <textarea
        rows={8}
        placeholder="Class features, racial traits, feats..."
        value={featuresAndTraits}
        disabled={readOnly}
        onChange={(e) => set("featuresAndTraits", e.target.value)}
        className={`${textarea} ${readOnly ? "opacity-70" : ""}`}
      />
    </Section>

    <Section title="Notes" color="bg-slate-500">
      <textarea
        rows={5}
        placeholder="Session notes, reminders, anything..."
        value={notes}
        disabled={readOnly}
        onChange={(e) => set("notes", e.target.value)}
        className={`${textarea} ${readOnly ? "opacity-70" : ""}`}
      />
    </Section>
  </>
);
