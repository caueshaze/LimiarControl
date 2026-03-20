import { useEffect, useState } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import type { BaseSpellUpdatePayload } from "../../../shared/api/baseSpellsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";
import { SpellCatalogField, SpellCatalogLegacyWarning, SpellCatalogToggleChip } from "./SpellCatalogEditorControls";
import {
  SPELL_CLASS_OPTIONS,
  SPELL_COMPONENT_OPTIONS,
  SPELL_DAMAGE_TYPE_OPTIONS,
  SPELL_LEVEL_OPTIONS,
  SPELL_SAVING_THROW_OPTIONS,
  SPELL_SCHOOL_OPTIONS,
  buildSpellUpdatePayload,
  createSpellEditorState,
  getUnsupportedSpellEditorValues,
  toggleSpellListValue,
} from "../utils/spellCatalogForm";

type Props = {
  spell: BaseSpell;
  onSave: (spellId: string, payload: BaseSpellUpdatePayload) => boolean | Promise<boolean>;
  onCancel: () => void;
};

const schoolLabelKey = (school: string): LocaleKey =>
  `catalog.spells.school.${school}` as LocaleKey;

export const SpellCatalogEditor = ({ spell, onSave, onCancel }: Props) => {
  const { t } = useLocale();
  const [state, setState] = useState(() => createSpellEditorState(spell));
  const [isSaving, setIsSaving] = useState(false);
  const unsupportedValues = getUnsupportedSpellEditorValues(spell);

  useEffect(() => {
    setState(createSpellEditorState(spell));
  }, [spell]);

  const canSave = Boolean(state.nameEn.trim()) && Boolean(state.descriptionEn.trim()) && state.level >= 0 && state.level <= 9;

  const handleSave = async () => {
    if (!canSave || isSaving) {
      return;
    }

    setIsSaving(true);
    try {
      const updated = await onSave(spell.id, buildSpellUpdatePayload(state));
      if (updated) {
        onCancel();
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <article className="relative overflow-hidden rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(8,12,28,0.96),rgba(2,6,23,0.98))] p-5 shadow-[0_18px_50px_rgba(2,6,23,0.3)]">
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("catalog.edit")}
            </p>
            <h3 className="mt-2 text-xl font-bold text-white">{spell.nameEn}</h3>
          </div>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-300">
            {spell.canonicalKey}
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <SpellCatalogField label={t("catalog.spells.form.nameEn")}>
            <input
              value={state.nameEn}
              onChange={(event) => setState((current) => ({ ...current, nameEn: event.target.value }))}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            />
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.namePt")}>
            <input
              value={state.namePt}
              onChange={(event) => setState((current) => ({ ...current, namePt: event.target.value }))}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            />
          </SpellCatalogField>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <SpellCatalogField label={t("catalog.spells.form.level")}>
            <select
              value={state.level}
              onChange={(event) =>
                setState((current) => ({ ...current, level: Number(event.target.value) }))
              }
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            >
              {SPELL_LEVEL_OPTIONS.map((level) => (
                <option key={level} value={level}>
                  {level === 0 ? t("catalog.spells.cantrip") : `${t("catalog.spells.levelLabel")} ${level}`}
                </option>
              ))}
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.school")}>
            <select
              value={state.school}
              onChange={(event) =>
                setState((current) => ({ ...current, school: event.target.value as BaseSpell["school"] }))
              }
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            >
              {SPELL_SCHOOL_OPTIONS.map((school) => (
                <option key={school} value={school}>
                  {t(schoolLabelKey(school))}
                </option>
              ))}
            </select>
          </SpellCatalogField>
        </div>

        {unsupportedValues.length > 0 ? (
          <SpellCatalogLegacyWarning
            title={t("catalog.spells.form.legacyWarningTitle")}
            description={t("catalog.spells.form.legacyWarningDescription")}
            values={unsupportedValues}
          />
        ) : null}

        <SpellCatalogField label={t("catalog.spells.form.classes")}>
          <div className="flex flex-wrap gap-2">
            {SPELL_CLASS_OPTIONS.map((className) => (
              <SpellCatalogToggleChip
                key={className}
                active={state.classesJson.includes(className)}
                label={className}
                onClick={() =>
                  setState((current) => ({
                    ...current,
                    classesJson: toggleSpellListValue(current.classesJson, className),
                  }))
                }
              />
            ))}
          </div>
        </SpellCatalogField>

        <div className="grid gap-4 sm:grid-cols-3">
          <SpellCatalogField label={t("catalog.spells.castingTime")}>
            <input
              value={state.castingTime}
              onChange={(event) => setState((current) => ({ ...current, castingTime: event.target.value }))}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            />
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.range")}>
            <input
              value={state.rangeText}
              onChange={(event) => setState((current) => ({ ...current, rangeText: event.target.value }))}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            />
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.duration")}>
            <input
              value={state.duration}
              onChange={(event) => setState((current) => ({ ...current, duration: event.target.value }))}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            />
          </SpellCatalogField>
        </div>

        <SpellCatalogField label={t("catalog.spells.form.components")}>
          <div className="flex flex-wrap gap-2">
            {SPELL_COMPONENT_OPTIONS.map((component) => (
              <SpellCatalogToggleChip
                key={component}
                active={state.componentsJson.includes(component)}
                label={component}
                onClick={() =>
                  setState((current) => ({
                    ...current,
                    componentsJson: toggleSpellListValue(current.componentsJson, component),
                  }))
                }
              />
            ))}
          </div>
        </SpellCatalogField>

        {state.componentsJson.includes("M") ? (
          <SpellCatalogField label={t("catalog.spells.form.material")}>
            <input
              value={state.materialComponentText}
              onChange={(event) =>
                setState((current) => ({ ...current, materialComponentText: event.target.value }))
              }
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            />
          </SpellCatalogField>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <SpellCatalogField label={t("catalog.spells.form.damageType")}>
            <select
              value={state.damageType}
              onChange={(event) => setState((current) => ({ ...current, damageType: event.target.value }))}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            >
              <option value="">{t("catalog.spells.form.none")}</option>
              {SPELL_DAMAGE_TYPE_OPTIONS.map((damageType) => (
                <option key={damageType} value={damageType}>
                  {damageType}
                </option>
              ))}
            </select>
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.savingThrow")}>
            <select
              value={state.savingThrow}
              onChange={(event) => setState((current) => ({ ...current, savingThrow: event.target.value }))}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            >
              <option value="">{t("catalog.spells.form.none")}</option>
              {SPELL_SAVING_THROW_OPTIONS.map((savingThrow) => (
                <option key={savingThrow} value={savingThrow}>
                  {savingThrow}
                </option>
              ))}
            </select>
          </SpellCatalogField>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <SpellCatalogField label={t("catalog.spells.form.descriptionEn")}>
            <textarea
              value={state.descriptionEn}
              onChange={(event) =>
                setState((current) => ({ ...current, descriptionEn: event.target.value }))
              }
              rows={5}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            />
          </SpellCatalogField>
          <SpellCatalogField label={t("catalog.spells.form.descriptionPt")}>
            <textarea
              value={state.descriptionPt}
              onChange={(event) =>
                setState((current) => ({ ...current, descriptionPt: event.target.value }))
              }
              rows={5}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none"
            />
          </SpellCatalogField>
        </div>

        <div className="flex flex-wrap gap-2">
          <SpellCatalogToggleChip
            active={state.concentration}
            label={t("catalog.spells.concentration")}
            onClick={() => setState((current) => ({ ...current, concentration: !current.concentration }))}
          />
          <SpellCatalogToggleChip
            active={state.ritual}
            label={t("catalog.spells.ritual")}
            onClick={() => setState((current) => ({ ...current, ritual: !current.ritual }))}
          />
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave || isSaving}
            className={`rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${
              !canSave || isSaving
                ? "cursor-not-allowed border border-white/8 text-slate-600"
                : "border border-violet-300/25 bg-violet-400/12 text-violet-100 hover:bg-violet-400/18"
            }`}
          >
            {isSaving ? t("catalog.saving") : t("catalog.save")}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 hover:border-white/20 hover:bg-white/[0.08]"
          >
            {t("catalog.cancel")}
          </button>
        </div>
      </div>
    </article>
  );
};
