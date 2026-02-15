import { useMemo, useState } from "react";
import type { NPC } from "../../../entities/npc";
import { useLocale } from "../../../shared/hooks/useLocale";

const names = ["Arin", "Mara", "Tomas", "Lysa", "Kael", "Nira", "Bram", "Sora"];
const races = ["Human", "Elf", "Dwarf", "Tiefling", "Halfling", "Orc"];
const roles = ["Merchant", "Guard", "Scholar", "Smuggler", "Priest", "Hunter"];
const traits = ["Blunt", "Curious", "Generous", "Cautious", "Ambitious", "Eccentric"];
const goals = [
  "Find a lost heirloom",
  "Protect the village",
  "Pay off a debt",
  "Expose a rival",
  "Recruit allies",
  "Escape a curse",
];
const secrets = [
  "Works for a rival faction",
  "Is secretly noble",
  "Stole the item",
  "Knows a hidden passage",
  "Owes a blood debt",
];

const pick = (list: string[]) => list[Math.floor(Math.random() * list.length)];

type NpcGeneratorProps = {
  onSave: (payload: Omit<NPC, "id" | "createdAt">) => Promise<void> | void;
};

export const NpcGenerator = ({ onSave }: NpcGeneratorProps) => {
  const { t } = useLocale();
  const [draft, setDraft] = useState<Omit<NPC, "id" | "createdAt"> | null>(null);
  const [notes, setNotes] = useState("");

  const generate = () => {
    setDraft({
      name: pick(names),
      race: pick(races),
      role: pick(roles),
      trait: pick(traits),
      goal: pick(goals),
      secret: Math.random() > 0.5 ? pick(secrets) : undefined,
    });
    setNotes("");
  };

  const detail = useMemo(() => {
    if (!draft) {
      return null;
    }
    return (
      <div className="space-y-2 text-sm text-slate-200">
        <p className="text-base font-semibold text-slate-100">{draft.name}</p>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
          {draft.race} · {draft.role}
        </p>
        <p>{draft.trait}</p>
        <p>{draft.goal}</p>
        {draft.secret && <p className="text-xs text-slate-400">{draft.secret}</p>}
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 focus:border-slate-500 focus:outline-none"
          rows={3}
          placeholder={t("npc.notesPlaceholder")}
        />
      </div>
    );
  }, [draft, notes, t]);

  const handleSave = async () => {
    if (!draft) {
      return;
    }
    await onSave({ ...draft, notes: notes.trim() || undefined });
    setDraft(null);
    setNotes("");
  };

  return (
    <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-100">{t("npc.generatorTitle")}</p>
        <button
          type="button"
          onClick={generate}
          className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200"
        >
          {t("npc.generate")}
        </button>
      </div>
      {detail || (
        <p className="text-xs text-slate-400">{t("npc.generatorHint")}</p>
      )}
      {draft && (
        <button
          type="button"
          onClick={handleSave}
          className="w-full rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-900"
        >
          {t("npc.save")}
        </button>
      )}
    </div>
  );
};
