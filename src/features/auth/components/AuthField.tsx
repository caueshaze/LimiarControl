import type { InputHTMLAttributes, ReactNode } from "react";

type AuthFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string | null;
  hint?: string;
  icon?: ReactNode;
};

export const AuthField = ({
  label,
  error,
  hint,
  icon,
  className = "",
  ...props
}: AuthFieldProps) => (
  <div className="space-y-2">
    <label className="ml-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
      {label}
    </label>
    <div className="group relative">
      <div className="absolute -inset-0.5 rounded-[22px] bg-[linear-gradient(120deg,rgba(125,211,252,0.16),rgba(167,139,250,0.16),rgba(251,191,36,0.12))] opacity-0 blur-sm transition duration-500 group-focus-within:opacity-100" />
      <div className="relative flex items-center gap-3 rounded-[20px] border border-white/10 bg-slate-950/70 px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-xl transition-colors group-focus-within:border-limiar-300/35">
        {icon ? (
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-white/8 bg-white/[0.03] text-slate-300 transition-colors group-focus-within:text-white">
            {icon}
          </span>
        ) : null}
        <input
          {...props}
          className={`w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none ${className}`}
        />
      </div>
    </div>
    {error ? (
      <p className="ml-1 text-xs text-rose-300">{error}</p>
    ) : hint ? (
      <p className="ml-1 text-xs text-slate-500">{hint}</p>
    ) : null}
  </div>
);
