import { useEffect, useRef, useState } from "react";
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
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const initials = user
    ? (user.displayName || user.username).charAt(0).toUpperCase()
    : null;

  return (
    <div className="min-h-screen text-slate-100">
      <header className="sticky top-0 z-50 border-b border-white/6 bg-void-950/80 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-3">

          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 shrink-0 rounded-full bg-limiar-400 shadow-[0_0_10px_rgba(92,248,208,0.55)]" />
            <span className="bg-linear-to-r from-limiar-200 to-limiar-400 bg-clip-text text-base font-bold tracking-tight text-transparent">
              {title}
            </span>
          </div>

          {/* User menu */}
          {user && (
            <div ref={menuRef} className="relative">
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className={`flex items-center gap-1.5 rounded-full border py-1 pl-1 pr-2.5 transition-colors ${
                  open
                    ? "border-limiar-500/30 bg-limiar-950/40"
                    : "border-white/8 bg-white/4 hover:border-white/[0.14] hover:bg-white/[0.07]"
                }`}
              >
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-limiar-500/20 text-[10px] font-bold text-limiar-300">
                  {initials}
                </div>
                <span className="hidden text-xs font-medium text-slate-200 sm:block">
                  {user.displayName || user.username}
                </span>
                <span className="rounded-full bg-white/6 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-slate-500">
                  {user.role}
                </span>
                <svg
                  className={`h-3 w-3 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {open && (
                <div className="absolute right-0 top-[calc(100%+8px)] w-48 overflow-hidden rounded-2xl border border-white/8 bg-void-950/95 shadow-2xl shadow-black/50 backdrop-blur-xl">
                  {/* Language */}
                  <button
                    type="button"
                    onClick={() => { toggleLocale(); setOpen(false); }}
                    className="flex w-full items-center justify-between px-4 py-3 text-xs font-semibold text-slate-300 transition-colors hover:bg-white/6 hover:text-white"
                  >
                    <span className="uppercase tracking-widest text-slate-500">
                      {t("auth.language")}
                    </span>
                    <span className="rounded-full border border-white/10 px-2 py-0.5 font-bold uppercase tracking-widest">
                      {locale === "en" ? "EN" : "PT"}
                    </span>
                  </button>

                  <div className="mx-3 border-t border-white/6" />

                  {/* Logout */}
                  {onLogout && (
                    <button
                      type="button"
                      onClick={() => { onLogout(); setOpen(false); }}
                      className="flex w-full items-center gap-2 px-4 py-3 text-xs font-semibold text-slate-400 transition-colors hover:bg-rose-500/10 hover:text-rose-300"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
                      </svg>
                      {t("auth.logout")}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-5 py-8 pb-24">
        <Outlet />
      </main>
    </div>
  );
};
