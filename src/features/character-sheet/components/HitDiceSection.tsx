import type { CharacterSheet, CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { input, fieldLabel, btnOutline } from "./styles";
import { safeParseInt } from "../utils/calculations";

type Props = {
  sheet: Pick<CharacterSheet, "hitDiceType" | "hitDiceTotal" | "hitDiceRemaining" | "deathSaves">;
  mode: CharacterSheetMode;
  readOnly?: boolean;
  set: SheetActions["set"];
  useHitDie: SheetActions["useHitDie"];
  longRest: SheetActions["longRest"];
  setDeathSave: SheetActions["setDeathSave"];
};

export const HitDiceSection = ({ mode, sheet, readOnly = false, set, useHitDie, longRest, setDeathSave }: Props) => {
  if (mode === "creation") {
    return (
      <Section title="Hit Dice" color="bg-indigo-500">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={fieldLabel}>Die Type (Derived)</label>
            <input type="text" value={sheet.hitDiceType || "-"} disabled className={`${input} opacity-70`} />
          </div>
          <div>
            <label className={fieldLabel}>Total Hit Dice</label>
            <input type="number" min={0} value={sheet.hitDiceTotal} disabled className={`${input} opacity-70`} />
          </div>
        </div>
      </Section>
    );
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Section title="Hit Dice" color="bg-indigo-500">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={fieldLabel}>Die Type</label>
            <select value={sheet.hitDiceType} disabled={readOnly} onChange={(e) => set("hitDiceType", e.target.value)} className={`${input} ${readOnly ? "opacity-70" : ""}`}>
              {["d6", "d8", "d10", "d12"].map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className={fieldLabel}>Total</label>
            <input
              type="number" min={0} value={sheet.hitDiceTotal}
              disabled={readOnly}
              onChange={(e) => set("hitDiceTotal", Math.max(0, safeParseInt(e.target.value)))}
              className={`${input} ${readOnly ? "opacity-70" : ""}`}
            />
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between">
          <span className="text-sm text-slate-400">
            Remaining: <span className="font-bold text-slate-200">{sheet.hitDiceRemaining}/{sheet.hitDiceTotal}</span>
          </span>
          {!readOnly && (
            <button
              type="button" onClick={useHitDie}
              disabled={sheet.hitDiceRemaining <= 0}
              className={`${btnOutline} ${sheet.hitDiceRemaining <= 0 ? "opacity-40" : ""}`}
            >
              Use Hit Die
            </button>
          )}
        </div>
        {!readOnly && (
          <button type="button" onClick={longRest} className={`mt-2 w-full ${btnOutline}`}>
            Long Rest (Restore All)
          </button>
        )}
      </Section>

      <Section title="Death Saves" color="bg-slate-500">
        <div className="space-y-3">
          <SaveDots label="Successes" color="emerald" count={sheet.deathSaves.successes} readOnly={readOnly} onChange={(v) => setDeathSave("successes", v)} />
          <SaveDots label="Failures" color="rose" count={sheet.deathSaves.failures} readOnly={readOnly} onChange={(v) => setDeathSave("failures", v)} />
          {!readOnly && (
            <button
              type="button"
              onClick={() => { setDeathSave("successes", 0); setDeathSave("failures", 0); }}
              className={`w-full ${btnOutline}`}
            >
              Reset
            </button>
          )}
        </div>
      </Section>
    </div>
  );
};

const SaveDots = ({ label, color, count, readOnly, onChange }: { label: string; color: string; count: number; readOnly: boolean; onChange: (v: number) => void }) => (
  <div>
    <p className={`mb-2 text-xs font-semibold text-${color}-400`}>{label}</p>
    <div className="flex gap-3">
      {[0, 1, 2].map((i) => (
        <button
          key={i}
          type="button"
          disabled={readOnly}
          onClick={() => onChange(count === i + 1 ? i : i + 1)}
          className={`h-6 w-6 rounded-full border-2 transition-colors border-${color}-${i < count ? "500 bg-" + color + "-500" : "600 bg-transparent"} ${readOnly ? "cursor-not-allowed opacity-70" : ""}`}
        />
      ))}
    </div>
  </div>
);
