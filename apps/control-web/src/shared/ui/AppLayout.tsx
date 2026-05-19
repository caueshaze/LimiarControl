import { useEffect, useRef, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useLocale } from "../hooks/useLocale";
import type { RoleMode } from "../types/role";
import { BrandMark } from "./BrandMark";
import { ManagedImage } from "./ManagedImage";

type AppLayoutProps = {
  title: string;
  user?: {
    displayName?: string | null;
    username: string;
    role: RoleMode;
    isSystemAdmin: boolean;
    avatarUrl?: string | null;
  } | null;
  onLogout?: () => void;
};

const MODE_KEY = "limiar_experience_mode";

export const AppLayout = ({ title, user, onLogout }: AppLayoutProps) => {
  const { toggleLocale, locale, t } = useLocale();
  const { pathname } = useLocation();
  const isHome = pathname === routes.home;
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const [focusMode, setFocusMode] = useState<"GM" | "PLAYER">(() => {
    const saved = localStorage.getItem(MODE_KEY);
    return saved === "GM" || saved === "PLAYER" ? saved : "GM";
  });
  const [buttonOrder, setButtonOrder] = useState<["GM" | "PLAYER", "GM" | "PLAYER"]>(() => {
    const saved = localStorage.getItem(MODE_KEY);
    return saved === "PLAYER" ? ["PLAYER", "GM"] : ["GM", "PLAYER"];
  });

  // Re-sync order when entering home so the active preference is always on the left.
  // Does NOT run on every focusMode change — only when isHome flips to true.
  useEffect(() => {
    if (isHome) {
      const saved = localStorage.getItem(MODE_KEY) as "GM" | "PLAYER" | null;
      const current = saved === "GM" || saved === "PLAYER" ? saved : "GM";
      setButtonOrder(current === "PLAYER" ? ["PLAYER", "GM"] : ["GM", "PLAYER"]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isHome]);

  const switchMode = (m: "GM" | "PLAYER") => {
    setFocusMode(m);
    localStorage.setItem(MODE_KEY, m);
    window.dispatchEvent(new CustomEvent("limiar-mode-change"));
  };

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
      <header className="sticky top-0 z-50 border-b border-white/6 bg-[linear-gradient(180deg,rgba(5,2,8,0.92),rgba(5,2,8,0.78))] backdrop-blur-xl">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-limiar-300/35 to-transparent" />
        <div className="mx-auto flex w-full max-w-6xl items-center px-5 py-3.5">

          {/* Left: brand */}
          <div className="flex flex-1 items-center gap-2.5">
            <BrandMark size="sm" className="shrink-0" />
            <div className="hidden min-w-0 sm:block">
              <p className="bg-linear-to-r from-limiar-100 via-white to-sky-100 bg-clip-text text-base font-bold tracking-tight text-transparent">
                {title}
              </p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("home.subtitle")}
              </p>
            </div>
          </div>

          {/* Center: mode switch — only on home */}
          {user && isHome && (
            <div className="relative hidden h-8 items-center rounded-full border border-white/10 bg-white/4 p-1 sm:flex">
              <span
                aria-hidden
                className={`absolute top-1 bottom-1 w-[calc(50%-2px)] rounded-full transition-all duration-300 ease-in-out ${
                  focusMode === buttonOrder[0]
                    ? `left-1 ${buttonOrder[0] === "GM" ? "bg-amber-400/20" : "bg-sky-400/20"}`
                    : `left-[calc(50%+1px)] ${buttonOrder[1] === "GM" ? "bg-amber-400/20" : "bg-sky-400/20"}`
                }`}
              />
              {buttonOrder.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => switchMode(m)}
                  className={`relative z-10 w-20 text-[10px] font-bold uppercase tracking-[0.2em] transition-colors duration-200 ${
                    focusMode === m
                      ? m === "GM" ? "text-amber-200" : "text-sky-200"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {m === "GM" ? "Mestre" : "Jogador"}
                </button>
              ))}
            </div>
          )}

          {/* Right: user menu placeholder to balance layout */}
          <div className="flex flex-1 justify-end">

          {/* User menu */}
          {user && (
            <div ref={menuRef} className="relative">
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className={`flex items-center gap-3 rounded-full border px-2 py-2 pr-3.5 shadow-[0_10px_30px_rgba(0,0,0,0.18)] transition-all ${
                  open
                    ? "border-limiar-400/30 bg-limiar-950/35"
                    : "border-white/10 bg-white/4 hover:border-white/20 hover:bg-white/8"
                }`}
              >
                <div className="relative flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-limiar-500/18 text-xs font-bold text-limiar-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
                  {user.avatarUrl ? (
                    <ManagedImage src={user.avatarUrl} alt={user.username} className="h-full w-full object-cover" />
                  ) : (
                    initials
                  )}
                  <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border border-void-950 bg-emerald-400" />
                </div>
                <div className="hidden min-w-0 text-left sm:block">
                  <p className="truncate text-xs font-semibold text-slate-100">
                    {user.displayName || user.username}
                  </p>
                  <p className="truncate text-[10px] uppercase tracking-[0.18em] text-slate-500">
                    @{user.username}
                  </p>
                </div>
                <svg
                  className={`h-3.5 w-3.5 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {open && (
                <div className="absolute right-0 top-[calc(100%+10px)] w-56 overflow-hidden rounded-3xl border border-white/8 bg-void-950/95 shadow-2xl shadow-black/50 backdrop-blur-xl">
                  <div className="border-b border-white/6 px-4 py-3">
                    <p className="text-sm font-semibold text-white">
                      {user.displayName || user.username}
                    </p>
                    <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                      @{user.username}
                    </p>
                  </div>

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

                  {user.isSystemAdmin && (
                    <Link
                      to={routes.adminHome}
                      onClick={() => setOpen(false)}
                      className="flex w-full items-center justify-between px-4 py-3 text-xs font-semibold text-slate-300 transition-colors hover:bg-white/6 hover:text-white"
                    >
                      <span className="uppercase tracking-widest text-slate-500">
                        {t("admin.menuLabel")}
                      </span>
                      <span className="rounded-full border border-amber-400/30 px-2 py-0.5 font-bold uppercase tracking-widest text-amber-200">
                        {t("admin.badge")}
                      </span>
                    </Link>
                  )}

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
          </div>{/* end right */}
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-5 py-8 pb-24">
        <Outlet />
      </main>
    </div>
  );
};
