import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { formatMod } from "../utils/calculations";
import { CONDITION_LABELS, CONDITION_NAMES } from "../constants";

type Props = {
  sheet: CharacterSheet;
  mode: CharacterSheetMode;
  canSave: boolean;
  showResetImport: boolean;
  ac: number;
  initiative: number;
  profBonus: number;
  passivePerception: number;
  spellSaveDC: number | null;
  spellAttack: number | null;
  hpTextColor: string;
  // Save UX
  partyId?: string | null;
  backHref?: string | null;
  isDirty: boolean;
  saving: boolean;
  saveError: string | null;
  onSave: () => void;
  // Import / export
  importRef: React.RefObject<HTMLInputElement | null>;
  importError: string | null;
  onExport: SheetActions["handleExport"];
  onImport: SheetActions["handleImport"];
  onReset: SheetActions["resetSheet"];
};

export const CharacterHeader = ({
  sheet, mode, canSave, showResetImport, ac, initiative, profBonus, passivePerception,
  spellSaveDC, spellAttack, hpTextColor,
  partyId, backHref, isDirty, saving, saveError, onSave,
  importRef, importError, onExport, onImport, onReset,
}: Props) => {
  const isCreation = mode === "creation";
  const activeConditions = CONDITION_NAMES.filter((c) => sheet.conditions[c]);
  const [showSaved, setShowSaved] = useState(false);

  // Show "Saved" briefly after a successful save
  useEffect(() => {
    if (canSave && !saving && !isDirty && !saveError && partyId) {
      setShowSaved(true);
      const t = setTimeout(() => setShowSaved(false), 2000);
      return () => clearTimeout(t);
    }
  }, [canSave, saving, isDirty, saveError, partyId]);

  return (
    <div className="space-y-4 px-4 pt-4 lg:px-6">
      {!isCreation && (
        <div className="sticky top-16 z-40">
          <div className="mx-auto flex max-w-[88rem] flex-wrap items-center gap-x-5 gap-y-3 rounded-[26px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.94))] px-5 py-4 shadow-[0_16px_50px_rgba(2,6,23,0.42)] backdrop-blur-xl">
            <span className="flex items-center gap-2 text-sm font-bold text-slate-100">
              {sheet.inspiration && (
                <span className="h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]" title="Inspired" />
              )}
              {sheet.name || "Unnamed"}
              <span className="font-normal text-slate-500">
                — {sheet.class || "?"} Lv{sheet.level}
              </span>
            </span>
            <StatChip
              label="HP"
              value={`${sheet.currentHP}/${sheet.maxHP}${sheet.tempHP > 0 ? ` +${sheet.tempHP}` : ""}`}
              className={hpTextColor}
            />
            <StatChip label="AC" value={String(ac)} />
            <StatChip label="Init" value={formatMod(initiative)} />
            <StatChip label="Prof" value={formatMod(profBonus)} className="text-limiar-400" />
            <StatChip label="PP" value={String(passivePerception)} />
            {spellSaveDC !== null && (
              <>
                <StatChip label="Spell DC" value={String(spellSaveDC)} className="text-violet-400" />
                <StatChip label="Spell Atk" value={formatMod(spellAttack!)} className="text-violet-400" />
              </>
            )}
            {activeConditions.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {activeConditions.map((c) => (
                  <span key={c} className="rounded-full bg-rose-500/20 px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest text-rose-300">
                    {CONDITION_LABELS[c]}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="mx-auto flex max-w-[88rem] flex-wrap items-center gap-3">
        {backHref && (
          <Link
            to={backHref}
            className="rounded-full border border-white/8 bg-white/[0.02] px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-slate-300 transition-all hover:border-limiar-500/40 hover:text-limiar-300"
          >
            Back To Party
          </Link>
        )}
        {showResetImport && (
          <button type="button" onClick={onReset}
            className="rounded-full border border-white/8 bg-white/[0.02] px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-slate-300 transition-all hover:border-rose-500/40 hover:text-rose-300">
            Reset Sheet
          </button>
        )}
        <button type="button" onClick={onExport}
          className="rounded-full border border-white/8 bg-white/[0.02] px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-slate-300 transition-all hover:border-limiar-500/40 hover:text-limiar-300">
          Export JSON
        </button>
        {showResetImport && (
          <label className="cursor-pointer rounded-full border border-white/8 bg-white/[0.02] px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-slate-300 transition-all hover:border-limiar-500/40 hover:text-limiar-300">
            Import JSON
            <input ref={importRef} type="file" accept=".json" className="hidden" onChange={onImport} />
          </label>
        )}

        {/* Save UX — only shown when backed by a party */}
        {partyId && canSave && (
          <div className="ml-auto flex items-center gap-2">
            <SaveStatus isDirty={isDirty} saving={saving} saveError={saveError} showSaved={showSaved} />
            <button
              type="button"
              onClick={onSave}
              disabled={saving || !isDirty}
              className={`rounded-full px-5 py-2 text-xs font-bold uppercase tracking-[0.24em] transition-colors ${
                saving || !isDirty
                  ? "cursor-not-allowed border border-white/8 text-slate-600"
                  : "border border-limiar-500/40 bg-limiar-500/15 text-limiar-200 hover:bg-limiar-500/25"
              }`}
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        )}
      </div>

      {importError && (
        <div className="mx-auto max-w-[88rem] rounded-2xl border border-rose-500/30 bg-rose-950/30 p-4 text-xs text-rose-300">
          <p className="mb-1 font-bold uppercase tracking-widest">Import Error</p>
          <pre className="whitespace-pre-wrap font-mono text-[11px] text-rose-400/80">{importError}</pre>
        </div>
      )}

      {canSave && saveError && (
        <div className="mx-auto flex max-w-[88rem] items-center gap-3 rounded-2xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
          <span className="font-bold">Save failed:</span>
          <span className="text-rose-400/80">{saveError}</span>
          <button type="button" onClick={onSave} className="ml-auto rounded-full border border-rose-500/40 px-3 py-1 font-bold hover:bg-rose-900/30">
            Retry
          </button>
        </div>
      )}
    </div>
  );
};

const SaveStatus = ({ isDirty, saving, saveError, showSaved }: { isDirty: boolean; saving: boolean; saveError: string | null; showSaved: boolean }) => {
  if (saving) return <span className="text-[11px] text-slate-500">Saving...</span>;
  if (saveError) return null; // shown in banner below
  if (showSaved) return <span className="text-[11px] font-semibold text-emerald-400">Saved</span>;
  if (isDirty) return <span className="text-[11px] font-semibold text-amber-400">Unsaved changes</span>;
  return null;
};

const StatChip = ({ label, value, className = "text-slate-200" }: { label: string; value: string; className?: string }) => (
  <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/[0.03] px-3 py-1.5 text-xs">
    <span className="font-bold uppercase tracking-[0.2em] text-slate-500">{label}</span>
    <span className={className}>{value}</span>
  </div>
);
