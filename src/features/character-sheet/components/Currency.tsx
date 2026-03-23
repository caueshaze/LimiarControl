import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { safeParseInt } from "../utils/calculations";
import { fromCopper, type CurrencyUnit } from "../../../shared/utils/money";

type Props = {
  currency: CharacterSheet["currency"];
  setCurrency: SheetActions["setCurrency"];
  readOnly?: boolean;
};

const COINS: { key: CurrencyUnit; label: string; accent: string }[] = [
  { key: "cp", label: "CP", accent: "border-rose-500/25 bg-rose-500/10 text-rose-200" },
  { key: "sp", label: "SP", accent: "border-slate-500/25 bg-slate-500/10 text-slate-200" },
  { key: "ep", label: "EP", accent: "border-lime-500/25 bg-lime-500/10 text-lime-200" },
  { key: "gp", label: "GP", accent: "border-amber-500/25 bg-amber-500/10 text-amber-200" },
  { key: "pp", label: "PP", accent: "border-cyan-500/25 bg-cyan-500/10 text-cyan-200" },
];

export const Currency = ({ currency, setCurrency, readOnly = false }: Props) => (
  <Section title="Currency" color="bg-amber-400">
    <div className="grid grid-cols-5 gap-3">
      {COINS.map(({ key, label, accent }) => (
        <div key={key} className="flex flex-col gap-2">
          <span className={`inline-flex items-center justify-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest ${accent}`}>
            {label}
          </span>
          <input
            type="number"
            min={0}
            value={fromCopper(currency.copperValue)[key]}
            disabled={readOnly}
            onChange={(e) => setCurrency(key, Math.max(0, safeParseInt(e.target.value)))}
            className={`w-full rounded-xl border border-white/10 bg-void-900/50 py-2 text-center text-sm font-bold text-slate-100 focus:border-limiar-500 focus:outline-none focus:ring-1 focus:ring-limiar-500/50 ${readOnly ? "opacity-70" : ""}`}
          />
        </div>
      ))}
    </div>
  </Section>
);
