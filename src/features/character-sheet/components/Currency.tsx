import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { safeParseInt } from "../utils/calculations";

type Props = {
  currency: CharacterSheet["currency"];
  setCurrency: SheetActions["setCurrency"];
  readOnly?: boolean;
};

const COINS: { key: keyof CharacterSheet["currency"]; label: string; color: string }[] = [
  { key: "cp", label: "CP", color: "text-orange-400" },
  { key: "sp", label: "SP", color: "text-slate-300" },
  { key: "ep", label: "EP", color: "text-teal-400" },
  { key: "gp", label: "GP", color: "text-amber-400" },
  { key: "pp", label: "PP", color: "text-violet-400" },
];

export const Currency = ({ currency, setCurrency, readOnly = false }: Props) => (
  <Section title="Currency" color="bg-amber-400">
    <div className="grid grid-cols-5 gap-3">
      {COINS.map(({ key, label, color }) => (
        <div key={key} className="flex flex-col items-center gap-1.5">
          <span className={`text-[10px] font-bold uppercase tracking-widest ${color}`}>{label}</span>
          <input
            type="number"
            min={0}
            value={currency[key]}
            disabled={readOnly}
            onChange={(e) => setCurrency(key, Math.max(0, safeParseInt(e.target.value)))}
            className={`w-full rounded-xl border border-white/10 bg-void-900/50 py-2 text-center text-sm font-bold text-slate-100 focus:border-limiar-500 focus:outline-none focus:ring-1 focus:ring-limiar-500/50 ${readOnly ? "opacity-70" : ""}`}
          />
        </div>
      ))}
    </div>
  </Section>
);
