import { useState } from "react";
import { card } from "./styles";

type SectionProps = {
  title: string;
  color: string;
  defaultOpen?: boolean;
  className?: string;
  children: React.ReactNode;
};

export const Section = ({ title, color, defaultOpen = true, className = "", children }: SectionProps) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`${card} ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer select-none items-center justify-between border-b border-white/6 pb-3 text-xs font-bold uppercase tracking-[0.3em] text-slate-300/90"
      >
        <span className="flex items-center gap-3">
          <span className={`h-4 w-1.5 rounded-full ${color}`} />
          {title}
        </span>
        <svg className={`h-4 w-4 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="mt-3">{children}</div>}
    </section>
  );
};

export const RemoveBtn = ({ onClick, title }: { onClick: () => void; title?: string }) => (
  <button
    type="button"
    onClick={onClick}
    className="shrink-0 self-center text-slate-600 transition-colors hover:text-rose-400"
    title={title ?? "Remove"}
  >
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  </button>
);
