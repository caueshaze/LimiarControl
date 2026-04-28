import { useState, type ReactNode } from "react";

type Props = {
  title: string;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  children: ReactNode;
};

export const SystemSpellCatalogFormSection = ({
  title,
  collapsible = false,
  defaultCollapsed = false,
  children,
}: Props) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <div className="rounded-2xl border border-white/8 bg-slate-950/35 p-4">
      <button
        type="button"
        onClick={collapsible ? () => setCollapsed((c) => !c) : undefined}
        className={`flex w-full items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400 ${
          collapsible ? "cursor-pointer hover:text-slate-200" : "cursor-default"
        }`}
      >
        <span>{title}</span>
        {collapsible && (
          <svg
            className={`h-3 w-3 shrink-0 transition-transform duration-200 ${
              collapsed ? "-rotate-90" : "rotate-0"
            }`}
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 5l3 3 3-3" />
          </svg>
        )}
      </button>
      {(!collapsible || !collapsed) && (
        <div className="mt-4 space-y-4">{children}</div>
      )}
    </div>
  );
};
