import type { ReactNode } from "react";

export const SpellCatalogFieldHelp = ({ text }: { text: string }) => (
  <span className="group relative inline-flex" tabIndex={0} aria-label={text}>
    <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-500/60 text-[10px] font-bold leading-none text-slate-400 transition group-hover:border-violet-300/70 group-hover:text-violet-100 group-focus-visible:border-violet-300/70 group-focus-visible:text-violet-100">
      i
    </span>
    <span className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 hidden w-56 -translate-x-1/2 rounded-md border border-white/10 bg-slate-950 px-3 py-2 text-[11px] normal-case leading-5 text-slate-100 shadow-xl group-hover:block group-focus-visible:block">
      {text}
    </span>
  </span>
);

export const SpellCatalogField = ({
  help,
  label,
  children,
}: {
  help?: string;
  label: string;
  children: ReactNode;
}) => (
  <label className="space-y-2">
    <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
      <span>{label}</span>
      {help ? <SpellCatalogFieldHelp text={help} /> : null}
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
