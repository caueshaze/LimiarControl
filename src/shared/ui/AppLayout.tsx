import type { ReactNode } from "react";
import { Outlet } from "react-router-dom";
import { useLocale } from "../hooks/useLocale";
import type { RoleMode } from "../types/role";

type AppLayoutProps = {
  title: string;
  user?: { displayName?: string | null; username: string; role: RoleMode } | null;
  onLogout?: () => void;
};

export const AppLayout = ({ title, user, onLogout }: AppLayoutProps) => {
  const { toggleLocale, locale, t } = useLocale();

  return (
    <div className="min-h-screen text-slate-100">
      <header className="sticky top-0 z-50 border-b border-white/5 bg-gradient-to-r from-void-950 via-slate-950/90 to-limiar-950/40 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="h-2.5 w-2.5 rounded-full bg-limiar-400 shadow-[0_0_12px_rgba(92,248,208,0.6)]" />
            <div>
              <span className="block bg-gradient-to-r from-limiar-200 to-limiar-500 bg-clip-text text-lg font-bold tracking-tight text-transparent">
                {title}
              </span>
              <span className="block text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
                Campaign command
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <div className="hidden items-center gap-2 text-xs text-slate-300 md:flex">
                <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                  <span className="font-medium text-slate-200">
                    {user.displayName || user.username}
                  </span>
                </div>
                <span className="rounded-full border border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-300">
                  {user.role}
                </span>
                {onLogout && (
                  <button
                    type="button"
                    onClick={onLogout}
                    className="rounded-full border border-white/10 px-3 py-1 text-xs font-medium text-slate-300 transition-colors hover:bg-white/5 hover:text-white"
                  >
                    {t("auth.logout")}
                  </button>
                )}
              </div>
            )}
            <button
              type="button"
              onClick={toggleLocale}
              className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-slate-300 hover:bg-white/10 hover:text-white"
            >
              {locale === "en" ? "EN" : "PT"}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-5 py-8 pb-24">
        <Outlet />
      </main>
    </div>
  );
};
