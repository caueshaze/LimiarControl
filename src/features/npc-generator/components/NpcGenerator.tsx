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
    "w-full rounded-[20px] border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-limiar-300/35 placeholder:text-slate-500";

  return (
    <section className="relative overflow-hidden rounded-[32px] border border-white/8 bg-[#070712] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(139,92,246,0.16),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.9),rgba(2,6,23,0.96))]" />
        <div className="absolute inset-0 opacity-[0.08] [background-image:linear-gradient(rgba(255,255,255,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.18)_1px,transparent_1px)] [background-size:42px_42px]" />
      </div>

      <div className="relative space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-limiar-100/85">
              {t("npc.title")}
            </p>
            <h2 className="mt-3 text-2xl font-bold text-white">{t("npc.generatorTitle")}</h2>
            <p className="mt-3 text-sm leading-7 text-slate-300">{t("npc.generatorDescription")}</p>
          </div>
          <div className="flex overflow-hidden rounded-full border border-white/10 bg-white/[0.04] text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-300">
            <button
              type="button"
              onClick={() => setMode("random")}
              className={`px-4 py-2.5 transition-colors ${mode === "random" ? "bg-limiar-500 text-white" : "hover:bg-white/[0.06]"}`}
            >
              {t("npc.modeRandom")}
            </button>
            <button
              type="button"
              onClick={() => setMode("manual")}
              className={`px-4 py-2.5 transition-colors ${mode === "manual" ? "bg-limiar-500 text-white" : "hover:bg-white/[0.06]"}`}
            >
              {t("npc.modeManual")}
            </button>
          </div>
        </div>

        {mode === "random" && (
          <>
            <button
              type="button"
              onClick={generate}
              className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2.5 text-xs font-semibold uppercase tracking-[0.22em] text-slate-100 transition hover:border-white/20 hover:bg-white/[0.08]"
            >
              {t("npc.generate")}
            </button>

            {randomDetail ? (
              <div className="rounded-[24px] border border-white/8 bg-white/[0.05] p-5 backdrop-blur-xl">
                {randomDetail}
              </div>
            ) : (
              <div className="rounded-[24px] border border-dashed border-white/10 bg-white/[0.03] p-5 text-sm leading-7 text-slate-300">
                {t("npc.generatorHint")}
              </div>
            )}

            {draft && (
              <button
                type="button"
                onClick={handleSaveRandom}
                className="w-full rounded-full bg-limiar-500 px-4 py-3 text-xs font-bold uppercase tracking-[0.22em] text-white transition hover:bg-limiar-400"
              >
                {t("npc.save")}
              </button>
            )}
          </>
        )}

        {mode === "manual" && (
          <form onSubmit={handleSaveManual} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input
                value={manual.name}
                onChange={(e) => setField("name", e.target.value)}
                placeholder={t("npc.fieldName")}
                required
                className={fieldClass}
              />
              <input
                value={manual.race ?? ""}
                onChange={(e) => setField("race", e.target.value)}
                placeholder={t("npc.fieldRace")}
                className={fieldClass}
              />
              <input
                value={manual.role ?? ""}
                onChange={(e) => setField("role", e.target.value)}
                placeholder={t("npc.fieldRole")}
                className={fieldClass}
              />
              <input
                value={manual.trait}
                onChange={(e) => setField("trait", e.target.value)}
                placeholder={t("npc.fieldTrait")}
                required
                className={fieldClass}
              />
            </div>
            <input
              value={manual.goal}
              onChange={(e) => setField("goal", e.target.value)}
              placeholder={t("npc.fieldGoal")}
              required
              className={fieldClass}
            />
            <input
              value={manual.secret ?? ""}
              onChange={(e) => setField("secret", e.target.value)}
              placeholder={t("npc.fieldSecret")}
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
              className="w-full rounded-full bg-limiar-500 px-4 py-3 text-xs font-bold uppercase tracking-[0.22em] text-white transition hover:bg-limiar-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? t("npc.saving") : t("npc.save")}
            </button>
          </form>
        )}
      </div>
    </section>
  );
};
