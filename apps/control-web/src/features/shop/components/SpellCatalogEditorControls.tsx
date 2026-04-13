import type { ReactNode } from "react";

export const SpellCatalogField = ({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) => (
  <label className="space-y-2">
    <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
      {label}
    </span>
    {children}
  </label>
);

export const SpellCatalogToggleChip = ({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] transition ${
      active
        ? "border-violet-300/25 bg-violet-400/12 text-violet-100"
        : "border-white/8 bg-white/4 text-slate-400 hover:border-white/16 hover:bg-white/8"
    }`}
  >
    {label}
  </button>
);

export const SpellCatalogLegacyWarning = ({
  description,
  title,
  values,
}: {
  description: string;
  title: string;
  values: string[];
}) => (
  <div className="rounded-2xl border border-amber-300/15 bg-amber-400/10 px-4 py-3 text-xs leading-6 text-amber-100">
    <p className="font-semibold uppercase tracking-[0.18em] text-amber-200/90">{title}</p>
    <p className="mt-2">
      {description} {values.join(", ")}
    </p>
  </div>
);
