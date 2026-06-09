import type { ReactNode } from "react";

import type { BaseSpell } from "../../../entities/base-spell";
import type { MagicItemRechargeType } from "../../../entities/base-item";
import { useLocale } from "../../../shared/hooks/useLocale";

type MagicBraceletFieldsProps = {
  spells: BaseSpell[];
  chargesMax: string;
  rechargeType: MagicItemRechargeType | "";
  spellCanonicalKey: string;
  castLevel: string;
  ignoreComponents: boolean;
  noFreeHandRequired: boolean;
  onChargesMaxChange: (value: string) => void;
  onRechargeTypeChange: (value: MagicItemRechargeType | "") => void;
  onSpellCanonicalKeyChange: (value: string) => void;
  onCastLevelChange: (value: string) => void;
  onIgnoreComponentsChange: (value: boolean) => void;
  onNoFreeHandRequiredChange: (value: boolean) => void;
};

const RECHARGE_OPTIONS: Array<{ value: MagicItemRechargeType; label: string }> = [
  { value: "none", label: "None" },
  { value: "short_rest", label: "Short rest" },
  { value: "long_rest", label: "Long rest" },
  { value: "dawn", label: "Dawn" },
  { value: "custom", label: "Custom" },
];

const Field = ({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) => (
  <label className="block">
    <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
      {label}
    </span>
    <div className="mt-2">{children}</div>
  </label>
);

export const MagicBraceletFields = ({
  spells,
  chargesMax,
  rechargeType,
  spellCanonicalKey,
  castLevel,
  ignoreComponents,
  noFreeHandRequired,
  onChargesMaxChange,
  onRechargeTypeChange,
  onSpellCanonicalKeyChange,
  onCastLevelChange,
  onIgnoreComponentsChange,
  onNoFreeHandRequiredChange,
}: MagicBraceletFieldsProps) => {
  const { locale, t } = useLocale();

  const sortedSpells = [...spells].sort((left, right) => {
    const leftName = locale === "pt" ? left.namePt || left.nameEn : left.nameEn;
    const rightName = locale === "pt" ? right.namePt || right.nameEn : right.nameEn;
    return leftName.localeCompare(rightName, locale === "pt" ? "pt-BR" : "en-US");
  });

  return (
    <div className="grid gap-4 rounded-[24px] border border-cyan-400/18 bg-cyan-500/6 p-4">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-200/80">
          {t("shop.form.magicBraceletTitle")}
        </p>
        <p className="mt-2 text-sm text-slate-300">
          {t("shop.form.magicBraceletDescription")}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Field label={t("shop.form.chargesMax")}>
          <input
            value={chargesMax}
            onChange={(event) => onChargesMaxChange(event.target.value)}
            className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
            inputMode="numeric"
            placeholder="1"
          />
        </Field>

        <Field label={t("shop.form.rechargeType")}>
          <select
            value={rechargeType}
            onChange={(event) => onRechargeTypeChange(event.target.value as MagicItemRechargeType | "")}
            className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
          >
            <option value="">{t("shop.form.optionNone")}</option>
            {RECHARGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {locale === "pt" ? t(`shop.form.recharge.${option.value}`) : option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label={t("shop.form.castSpellLevel")}>
          <input
            value={castLevel}
            onChange={(event) => onCastLevelChange(event.target.value)}
            className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
            inputMode="numeric"
            placeholder="1"
          />
        </Field>
      </div>

      <Field label={t("shop.form.linkedSpell")}>
        <select
          value={spellCanonicalKey}
          onChange={(event) => onSpellCanonicalKeyChange(event.target.value)}
          className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
        >
          <option value="">{t("shop.form.optionNone")}</option>
          {sortedSpells.map((spell) => {
            const label = locale === "pt" ? spell.namePt || spell.nameEn : spell.nameEn;
            return (
              <option key={spell.canonicalKey} value={spell.canonicalKey}>
                {label}
              </option>
            );
          })}
        </select>
      </Field>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex items-center gap-3 rounded-2xl border border-white/8 bg-slate-950/45 px-4 py-3 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={ignoreComponents}
            onChange={(event) => onIgnoreComponentsChange(event.target.checked)}
          />
          <span>{t("shop.form.ignoreComponents")}</span>
        </label>

        <label className="flex items-center gap-3 rounded-2xl border border-white/8 bg-slate-950/45 px-4 py-3 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={noFreeHandRequired}
            onChange={(event) => onNoFreeHandRequiredChange(event.target.checked)}
          />
          <span>{t("shop.form.noFreeHandRequired")}</span>
        </label>
      </div>
    </div>
  );
};
