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

const emptyManual = (): Omit<NPC, "id" | "createdAt"> => ({
  name: "",
  race: "",
  role: "",
  trait: "",
  goal: "",
  secret: "",
  notes: "",
});

type NpcGeneratorProps = {
  onSave: (payload: Omit<NPC, "id" | "createdAt">) => Promise<void> | void;
};

export const NpcGenerator = ({ onSave }: NpcGeneratorProps) => {
  const { t } = useLocale();
  const [mode, setMode] = useState<"random" | "manual">("random");

  // --- Random mode state ---
  const [draft, setDraft] = useState<Omit<NPC, "id" | "createdAt"> | null>(null);
  const [notes, setNotes] = useState("");

  // --- Manual mode state ---
  const [manual, setManual] = useState<Omit<NPC, "id" | "createdAt">>(emptyManual());
  const [saving, setSaving] = useState(false);

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

  const randomDetail = useMemo(() => {
    if (!draft) return null;
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
          onChange={(e) => setNotes(e.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 focus:border-slate-500 focus:outline-none"
          rows={3}
          placeholder={t("npc.notesPlaceholder")}
        />
      </div>
    );
  }, [draft, notes, t]);

  const handleSaveRandom = async () => {
    if (!draft) return;
    await onSave({ ...draft, notes: notes.trim() || undefined });
    setDraft(null);
    setNotes("");
  };

  const setField = (field: keyof typeof manual, value: string) =>
    setManual((prev) => ({ ...prev, [field]: value }));

  const handleSaveManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manual.name.trim() || !manual.trait.trim() || !manual.goal.trim()) return;
    setSaving(true);
    try {
      await onSave({
        name: manual.name.trim(),
        race: manual.race?.trim() || undefined,
        role: manual.role?.trim() || undefined,
        trait: manual.trait.trim(),
        goal: manual.goal.trim(),
        secret: manual.secret?.trim() || undefined,
        notes: manual.notes?.trim() || undefined,
      });
      setManual(emptyManual());
    } finally {
      setSaving(false);
    }
  };

  const fieldClass =
    "w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none placeholder:text-slate-600";

  return (
    <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      {/* Mode toggle */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-100">{t("npc.generatorTitle")}</p>
        <div className="flex rounded-full border border-slate-700 overflow-hidden text-xs font-semibold uppercase tracking-widest">
          <button
            type="button"
            onClick={() => setMode("random")}
            className={`px-3 py-1 transition-colors ${mode === "random" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"}`}
          >
            Random
          </button>
          <button
            type="button"
            onClick={() => setMode("manual")}
            className={`px-3 py-1 transition-colors ${mode === "manual" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"}`}
          >
            Manual
          </button>
        </div>
      </div>

      {/* Random mode */}
      {mode === "random" && (
        <>
          <button
            type="button"
            onClick={generate}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200 hover:bg-slate-800"
          >
            {t("npc.generate")}
          </button>
          {randomDetail || <p className="text-xs text-slate-400">{t("npc.generatorHint")}</p>}
          {draft && (
            <button
              type="button"
              onClick={handleSaveRandom}
              className="w-full rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-900"
            >
              {t("npc.save")}
            </button>
          )}
        </>
      )}

      {/* Manual mode */}
      {mode === "manual" && (
        <form onSubmit={handleSaveManual} className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <input
              value={manual.name}
              onChange={(e) => setField("name", e.target.value)}
              placeholder="Name *"
              required
              className={fieldClass}
            />
            <input
              value={manual.race ?? ""}
              onChange={(e) => setField("race", e.target.value)}
              placeholder="Race"
              className={fieldClass}
            />
            <input
              value={manual.role ?? ""}
              onChange={(e) => setField("role", e.target.value)}
              placeholder="Role"
              className={fieldClass}
            />
            <input
              value={manual.trait}
              onChange={(e) => setField("trait", e.target.value)}
              placeholder="Trait *"
              required
              className={fieldClass}
            />
          </div>
          <input
            value={manual.goal}
            onChange={(e) => setField("goal", e.target.value)}
            placeholder="Goal *"
            required
            className={fieldClass}
          />
          <input
            value={manual.secret ?? ""}
            onChange={(e) => setField("secret", e.target.value)}
            placeholder="Secret (optional)"
            className={fieldClass}
          />
          <textarea
            value={manual.notes ?? ""}
            onChange={(e) => setField("notes", e.target.value)}
            placeholder={t("npc.notesPlaceholder")}
            rows={3}
            className={fieldClass}
          />
          <button
            type="submit"
            disabled={saving || !manual.name.trim() || !manual.trait.trim() || !manual.goal.trim()}
            className="w-full rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-900 disabled:opacity-50"
          >
            {saving ? "Saving..." : t("npc.save")}
          </button>
        </form>
      )}
    </div>
  );
};
