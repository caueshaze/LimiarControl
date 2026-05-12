import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { APP_NAME } from "../../../app/config";
import { routes } from "../../../app/routes/routes";
import { BrandMark } from "../../../shared/ui";

type AuthMode = "login" | "register";

type AuthShellProps = {
  mode: AuthMode;
  title: string;
  subtitle: string;
  form: ReactNode;
  footer: ReactNode;
};

export const AuthShell = ({ mode, title, subtitle, form, footer }: AuthShellProps) => (
  <div className="relative min-h-screen overflow-hidden bg-void-950 text-slate-100">
    {/* Atmospheric orbs — same as WelcomePage */}
    <div
      aria-hidden
      className="pointer-events-none absolute -left-32 top-10 h-[420px] w-[420px] rounded-full bg-limiar-500/20 blur-[140px] motion-safe:animate-[landing-drift_18s_ease-in-out_infinite]"
    />
    <div
      aria-hidden
      className="pointer-events-none absolute right-0 top-0 h-[360px] w-[360px] rounded-full bg-sky-400/14 blur-[140px] motion-safe:animate-[landing-drift_22s_ease-in-out_infinite_reverse]"
    />
    <div
      aria-hidden
      className="pointer-events-none absolute -bottom-24 left-1/3 h-[340px] w-[340px] rounded-full bg-amber-400/10 blur-[160px] motion-safe:animate-[landing-float_16s_ease-in-out_infinite]"
    />

    <div className="relative flex min-h-screen items-center justify-center px-6 py-10">
      <div className={`w-full ${mode === "register" ? "max-w-xl" : "max-w-lg"}`}>

        {/* Branding pill */}
        <div className="mb-6 flex justify-center">
          <Link
            to={routes.root}
            className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/4 px-4 py-2.5 backdrop-blur-xl transition hover:border-white/20 hover:bg-white/6"
          >
            <BrandMark size="sm" />
            <span className="font-display text-sm font-bold text-white">{APP_NAME}</span>
          </Link>
        </div>

        {/* Card */}
        <div className="animate-[landing-rise_0.55s_ease-out] rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,24,39,0.85),rgba(2,6,23,0.94))] p-8 shadow-[0_30px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl">
          <h1 className="font-display text-3xl font-bold text-white">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-400">{subtitle}</p>

          <div className="mt-8">{form}</div>

          <div className="mt-6 border-t border-white/8 pt-5">{footer}</div>
        </div>

      </div>
    </div>
  </div>
);
