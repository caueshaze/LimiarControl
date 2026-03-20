import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { APP_NAME } from "../../../app/config";
import { routes } from "../../../app/routes/routes";
import { useLocale } from "../../../shared/hooks/useLocale";
import { BrandMark } from "../../../shared/ui";
import { AuthShowcase } from "./AuthShowcase";

type AuthMode = "login" | "register";

type AuthShellProps = {
  mode: AuthMode;
  title: string;
  subtitle: string;
  form: ReactNode;
  footer: ReactNode;
};

const headerLabels = {
  pt: {
    home: "Voltar para home",
    login: "Entrar",
    register: "Criar conta",
    caption: "Mesa digital para campanhas conectadas",
  },
  en: {
    home: "Back to home",
    login: "Sign in",
    register: "Create account",
    caption: "Digital tabletop for connected campaigns",
  },
} as const;

export const AuthShell = ({
  mode,
  title,
  subtitle,
  form,
  footer,
}: AuthShellProps) => {
  const { locale } = useLocale();
  const copy = headerLabels[locale];

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050208] text-slate-100 selection:bg-limiar-400/25 selection:text-white">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(167,139,250,0.18),transparent_26%),radial-gradient(circle_at_18%_28%,rgba(34,211,238,0.16),transparent_18%),radial-gradient(circle_at_84%_18%,rgba(251,191,36,0.1),transparent_18%),linear-gradient(180deg,#050208_0%,#090413_34%,#050208_100%)]" />
        <div className="absolute inset-0 opacity-[0.06] [background-image:linear-gradient(rgba(255,255,255,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.18)_1px,transparent_1px)] [background-size:72px_72px]" />
        <div className="absolute -left-20 top-10 h-72 w-72 rounded-full bg-limiar-500/20 blur-[140px] motion-safe:animate-[landing-drift_16s_ease-in-out_infinite]" />
        <div className="absolute right-0 top-0 h-[28rem] w-[28rem] rounded-full bg-sky-500/10 blur-[150px] motion-safe:animate-[landing-drift_18s_ease-in-out_infinite_reverse]" />
        <div className="absolute bottom-[-7rem] left-1/3 h-72 w-72 rounded-full bg-amber-400/10 blur-[150px] motion-safe:animate-[landing-float_15s_ease-in-out_infinite]" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4 py-2">
          <Link
            to={routes.root}
            className="inline-flex items-center gap-4 rounded-full border border-white/10 bg-slate-950/50 px-4 py-2.5 backdrop-blur-xl transition-colors hover:border-limiar-300/20 hover:bg-slate-950/70"
          >
            <BrandMark size="md" />
            <span>
              <span className="block font-display text-lg font-bold text-white">{APP_NAME}</span>
              <span className="block text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                {copy.caption}
              </span>
            </span>
          </Link>

          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/50 p-1 backdrop-blur-xl">
            <Link
              to={routes.root}
              className="rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400 transition-colors hover:text-white"
            >
              {copy.home}
            </Link>
            <Link
              to={routes.login}
              className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] transition-colors ${
                mode === "login" ? "bg-white text-slate-950" : "text-slate-300 hover:text-white"
              }`}
            >
              {copy.login}
            </Link>
            <Link
              to={routes.register}
              className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] transition-colors ${
                mode === "register" ? "bg-white text-slate-950" : "text-slate-300 hover:text-white"
              }`}
            >
              {copy.register}
            </Link>
          </div>
        </header>

        <main className="flex flex-1 items-center py-6 lg:py-10">
          <div className="grid w-full items-stretch gap-8 lg:grid-cols-[minmax(0,1.12fr)_minmax(0,0.88fr)]">
            <div className="order-2 lg:order-1 motion-safe:animate-[landing-rise_0.85s_ease-out_both]">
              <AuthShowcase mode={mode} />
            </div>

            <section className="order-1 flex items-center lg:order-2">
              <div className="w-full rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(10,15,30,0.9),rgba(4,8,20,0.96))] p-1 shadow-[0_32px_100px_rgba(2,6,23,0.54)]">
                <div className="rounded-[32px] border border-white/6 bg-slate-950/75 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-xl sm:p-8">
                  <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] p-6 sm:p-7">
                    <div className="inline-flex items-center gap-2 rounded-full border border-limiar-300/15 bg-limiar-400/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.28em] text-limiar-100">
                      <BrandMark size="sm" className="h-7 w-7 rounded-lg shadow-none" imageClassName="p-1" />
                      {APP_NAME}
                    </div>
                    <h1 className="mt-5 text-3xl font-bold text-white sm:text-4xl">{title}</h1>
                    <p className="mt-3 max-w-xl text-sm leading-7 text-slate-400 sm:text-base">{subtitle}</p>

                    <div className="mt-8">{form}</div>
                    <div className="mt-8 border-t border-white/8 pt-6">{footer}</div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
};
