import { useState } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import type { BaseSpellUpdatePayload } from "../../../shared/api/baseSpellsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";
import { SpellCatalogEditor } from "./SpellCatalogEditor";

type Props = {
  spell: BaseSpell;
  onUpdate?: (
    spellId: string,
    payload: BaseSpellUpdatePayload,
  ) => boolean | Promise<boolean>;
};

const SCHOOL_COLORS: Record<string, { chip: string; accent: string }> = {
  abjuration: { chip: "border-sky-300/20 bg-sky-400/12 text-sky-100", accent: "from-sky-400/18" },
  conjuration: { chip: "border-amber-300/20 bg-amber-400/12 text-amber-100", accent: "from-amber-400/18" },
  divination: { chip: "border-cyan-300/20 bg-cyan-400/12 text-cyan-100", accent: "from-cyan-400/18" },
  enchantment: { chip: "border-pink-300/20 bg-pink-400/12 text-pink-100", accent: "from-pink-400/18" },
  evocation: { chip: "border-rose-300/20 bg-rose-400/12 text-rose-100", accent: "from-rose-400/18" },
  illusion: { chip: "border-violet-300/20 bg-violet-400/12 text-violet-100", accent: "from-violet-400/18" },
  necromancy: { chip: "border-emerald-300/20 bg-emerald-400/12 text-emerald-100", accent: "from-emerald-400/18" },
  transmutation: { chip: "border-orange-300/20 bg-orange-400/12 text-orange-100", accent: "from-orange-400/18" },
};

const schoolKey = (school: string): LocaleKey =>
  `catalog.spells.school.${school}` as LocaleKey;

const levelLabel = (level: number, t: (key: LocaleKey) => string) =>
  level === 0 ? t("catalog.spells.cantrip") : `${t("catalog.spells.levelLabel")} ${level}`;

export const SpellCatalogCard = ({ spell, onUpdate }: Props) => {
  const { t, locale } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const displayName = (locale === "pt" && spell.namePt) ? spell.namePt : spell.nameEn;
  const colors = SCHOOL_COLORS[spell.school] ?? SCHOOL_COLORS.evocation;
  const components = spell.componentsJson?.join(", ") ?? "";

  if (isEditing && onUpdate) {
    return (
      <SpellCatalogEditor
        spell={spell}
        onSave={onUpdate}
        onCancel={() => setIsEditing(false)}
      />
    );
  }

  return (
    <div className="group relative overflow-hidden rounded-[22px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(2,6,23,0.96))] shadow-[0_12px_40px_rgba(2,6,23,0.22)] transition-all hover:border-white/14 hover:shadow-[0_16px_50px_rgba(2,6,23,0.32)]">
      <div className={`pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,var(--tw-gradient-stops))] ${colors.accent} to-transparent opacity-60`} />

      <div className="relative space-y-3 p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-sm font-bold text-slate-100">{displayName}</h3>
            {locale === "pt" && spell.namePt && (
              <p className="truncate text-[10px] text-slate-500">{spell.nameEn}</p>
            )}
          </div>
          <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest ${colors.chip}`}>
            {t(schoolKey(spell.school))}
          </span>
        </div>

        {/* Level + badges */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold text-violet-200">
            {levelLabel(spell.level, t)}
          </span>
          {spell.concentration && (
            <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-200">
              {t("catalog.spells.concentration")}
            </span>
          )}
          {spell.ritual && (
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-200">
              {t("catalog.spells.ritual")}
            </span>
          )}
        </div>

        {/* Stats row */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-400">
          {spell.castingTime && (
            <span>
              <span className="font-semibold text-slate-500">{t("catalog.spells.castingTime")}: </span>
              {spell.castingTime}
            </span>
          )}
          {spell.rangeText && (
            <span>
              <span className="font-semibold text-slate-500">{t("catalog.spells.range")}: </span>
              {spell.rangeText}
            </span>
          )}
          {spell.duration && (
            <span>
              <span className="font-semibold text-slate-500">{t("catalog.spells.duration")}: </span>
              {spell.duration}
            </span>
          )}
          {components && (
            <span>
              <span className="font-semibold text-slate-500">{t("catalog.spells.components")}: </span>
              {components}
            </span>
          )}
        </div>

        {/* Classes */}
        {spell.classesJson && spell.classesJson.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {spell.classesJson.map((cls) => (
              <span
                key={cls}
                className="rounded-full border border-white/8 bg-white/[0.03] px-2 py-0.5 text-[9px] font-semibold text-slate-400"
              >
                {cls}
              </span>
            ))}
          </div>
        )}

        {/* Description (expandable) */}
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          {expanded ? (
            <p className="whitespace-pre-wrap leading-relaxed text-slate-400">
              {(locale === "pt" && spell.descriptionPt) ? spell.descriptionPt : spell.descriptionEn}
            </p>
          ) : (
            <p className="line-clamp-2 leading-relaxed">
              {(locale === "pt" && spell.descriptionPt) ? spell.descriptionPt : spell.descriptionEn}
            </p>
          )}
        </button>

        {onUpdate ? (
          <div className="pt-1">
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-100 transition hover:border-white/20 hover:bg-white/[0.09]"
            >
              {t("catalog.edit")}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
};
