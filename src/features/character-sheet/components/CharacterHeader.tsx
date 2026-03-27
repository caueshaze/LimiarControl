import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { formatMod } from "../utils/calculations";
import { CONDITION_LABELS, CONDITION_NAMES } from "../constants";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";

const REQUIRED_FIELD_LABEL_KEY: Record<RequiredField, LocaleKey> = {
  name: "sheet.basicInfo.characterName",
  class: "sheet.basicInfo.class",
  subclass: "sheet.basicInfo.subclass",
  subclassConfig: "sheet.basicInfo.subclassConfig",
  raceConfig: "sheet.raceConfig.title",
  race: "sheet.basicInfo.race",
  background: "sheet.basicInfo.background",
  alignment: "sheet.basicInfo.alignment",
  playerName: "sheet.basicInfo.playerName",
  fightingStyle: "sheet.basicInfo.fightingStyle",
  classSkills: "sheet.skillPicker.classSkills",
  classToolProficiencies: "sheet.toolPicker.title",
  raceToolProficiency: "sheet.raceToolPicker.title",
  equipmentChoices: "sheet.creation.equipmentChoices",
  languageChoices: "sheet.languages.choiceTitle",
  cantrips: "sheet.spells.cantrip",
  leveledSpells: "sheet.spells.knownTitle",
  expertise: "sheet.expertisePicker.title",
};

const TOTAL_REQUIRED_FIELDS = Object.keys(REQUIRED_FIELD_LABEL_KEY).length;

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
  backLabel?: string | null;
  isDirty: boolean;
  saving: boolean;
  saveError: string | null;
  saveDisabledReason?: string | null;
  missingRequiredFields?: RequiredField[];
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
  partyId, backHref, backLabel, isDirty, saving, saveError, saveDisabledReason, missingRequiredFields = [], onSave,
  importRef, importError, onExport, onImport, onReset,
}: Props) => {
  const navigate = useNavigate();
  const { t } = useLocale();
  const isCreation = mode === "creation";
  const activeConditions = CONDITION_NAMES.filter((c) => sheet.conditions[c]);
  const [showSaved, setShowSaved] = useState(false);

  // Show "Saved" briefly after a successful save
  useEffect(() => {
    if (canSave && !saving && !isDirty && !saveError && partyId) {
      setShowSaved(true);
      const timer = setTimeout(() => setShowSaved(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [canSave, saving, isDirty, saveError, partyId]);

  const handleBack = () => {
    if (backHref) {
      navigate(backHref);
      return;
    }
    if (window.history.length > 1) {
      navigate(-1);
    }
  };

  // Progress: count fields that are NOT missing
  const doneFields = TOTAL_REQUIRED_FIELDS - missingRequiredFields.length;
  const progressPct = Math.max(0, Math.min(100, (doneFields / TOTAL_REQUIRED_FIELDS) * 100));

  return (
    <div className="space-y-4 px-4 pt-4 lg:px-6">
      <div className="mx-auto flex max-w-[88rem] flex-wrap items-center gap-3">
        {(backHref || window.history.length > 1) && (
          <button
            type="button"
            onClick={handleBack}
            className="rounded-full border border-white/8 bg-white/2 px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-slate-300 transition-all hover:border-limiar-500/40 hover:text-limiar-300"
          >
            {backLabel ?? t("sheet.header.backToParty")}
          </button>
        )}
        {showResetImport && (
          <button type="button" onClick={onReset}
            className="rounded-full border border-white/8 bg-white/2 px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-slate-300 transition-all hover:border-rose-500/40 hover:text-rose-300">
            {t("sheet.header.reset")}
          </button>
        )}
        <button type="button" onClick={onExport}
          className="rounded-full border border-white/8 bg-white/2 px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-slate-300 transition-all hover:border-limiar-500/40 hover:text-limiar-300">
          {t("sheet.header.exportJson")}
        </button>
        {showResetImport && (
          <label className="cursor-pointer rounded-full border border-white/8 bg-white/2 px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-slate-300 transition-all hover:border-limiar-500/40 hover:text-limiar-300">
            {t("sheet.header.importJson")}
            <input ref={importRef} type="file" accept=".json" className="hidden" onChange={onImport} />
          </label>
        )}

        {/* Save UX — only shown when backed by a party */}
        {partyId && canSave && (
          <div className="ml-auto flex items-center gap-2">
            <SaveStatus isDirty={isDirty} saving={saving} saveError={saveError} showSaved={showSaved} t={t} />
            <button
              type="button"
              onClick={onSave}
              disabled={saving || !isDirty || !!saveDisabledReason}
              className={`rounded-full px-5 py-2 text-xs font-bold uppercase tracking-[0.24em] transition-colors ${
                saving || !isDirty || !!saveDisabledReason
                  ? "cursor-not-allowed border border-white/8 text-slate-600"
                  : "border border-limiar-500/40 bg-limiar-500/15 text-limiar-200 hover:bg-limiar-500/25"
              }`}
              title={saveDisabledReason ?? undefined}
            >
              {saving ? t("sheet.header.saving") : t("sheet.header.save")}
            </button>
          </div>
        )}
      </div>

      {!isCreation && (
        <div className="sticky top-18 z-30">
          <div className="mx-auto flex max-w-[88rem] flex-wrap items-center gap-x-5 gap-y-3 rounded-[26px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.94))] px-5 py-4 shadow-[0_16px_50px_rgba(2,6,23,0.42)] backdrop-blur-xl">
            <span className="flex items-center gap-2 text-sm font-bold text-slate-100">
              {sheet.inspiration && (
                <span className="h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]" title="Inspired" />
              )}
              {sheet.name || t("sheet.header.unnamed")}
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

      {importError && (
        <div className="mx-auto max-w-[88rem] rounded-2xl border border-rose-500/30 bg-rose-950/30 p-4 text-xs text-rose-300">
          <p className="mb-1 font-bold uppercase tracking-widest">{t("sheet.header.importError")}</p>
          <pre className="whitespace-pre-wrap font-mono text-[11px] text-rose-400/80">{importError}</pre>
        </div>
      )}

      {canSave && saveError && (
        <div className="mx-auto flex max-w-[88rem] items-center gap-3 rounded-2xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
          <span className="font-bold">{t("sheet.header.saveFailed")}:</span>
          <span className="text-rose-400/80">{saveError}</span>
          <button type="button" onClick={onSave} className="ml-auto rounded-full border border-rose-500/40 px-3 py-1 font-bold hover:bg-rose-900/30">
            {t("sheet.header.retry")}
          </button>
        </div>
      )}

      {canSave && missingRequiredFields.length > 0 && (
        <div className="mx-auto max-w-[88rem] space-y-3 rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4">
          {/* Progress bar */}
          <div className="flex items-center gap-3">
            <svg className="h-4 w-4 shrink-0 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <span className="text-xs font-bold uppercase tracking-widest text-amber-400">
              {t("sheet.header.requiredBefore")}
            </span>
            <span className="ml-auto text-[11px] font-semibold text-amber-300/70">
              {t("sheet.header.progressLabel")
                .replace("{done}", String(doneFields))
                .replace("{total}", String(TOTAL_REQUIRED_FIELDS))}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-amber-950/60">
            <div
              className="h-full rounded-full bg-amber-500/60 transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {missingRequiredFields.map((field) => (
              <span
                key={field}
                className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[11px] font-semibold text-amber-200"
              >
                {t(REQUIRED_FIELD_LABEL_KEY[field])}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const SaveStatus = ({
  isDirty, saving, saveError, showSaved, t,
}: {
  isDirty: boolean;
  saving: boolean;
  saveError: string | null;
  showSaved: boolean;
  t: (key: LocaleKey) => string;
}) => {
  if (saving) return <span className="text-[11px] text-slate-500">{t("sheet.header.saving")}</span>;
  if (saveError) return null;
  if (showSaved) return <span className="text-[11px] font-semibold text-emerald-400">{t("sheet.header.saved")}</span>;
  if (isDirty) return <span className="text-[11px] font-semibold text-amber-400">{t("sheet.header.unsaved")}</span>;
  return null;
};

const StatChip = ({ label, value, className = "text-slate-200" }: { label: string; value: string; className?: string }) => (
  <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/3 px-3 py-1.5 text-xs">
    <span className="font-bold uppercase tracking-[0.2em] text-slate-500">{label}</span>
    <span className={className}>{value}</span>
  </div>
);
