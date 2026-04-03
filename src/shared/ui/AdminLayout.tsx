import { useMemo } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useLocale } from "../hooks/useLocale";
import type { RoleMode } from "../types/role";
import { BrandMark } from "./BrandMark";

type AdminLayoutProps = {
  user?: {
    displayName?: string | null;
    username: string;
    role: RoleMode;
    isSystemAdmin: boolean;
  } | null;
  onLogout?: () => void;
};

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  `flex items-center justify-between rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
    isActive
      ? "border-amber-400/30 bg-amber-400/12 text-amber-100"
      : "border-white/6 bg-white/3 text-slate-300 hover:border-white/12 hover:bg-white/6 hover:text-white"
  }`;

export const AdminLayout = ({ user, onLogout }: AdminLayoutProps) => {
  const { locale, toggleLocale, t } = useLocale();
  const location = useLocation();

  const pageMeta = useMemo(() => {
    if (location.pathname.startsWith(routes.adminCatalogSpells)) {
      return {
        eyebrow: t("admin.breadcrumb.spells"),
        title: t("admin.page.spells.title"),
        description: t("admin.page.spells.description"),
      };
    }
    if (location.pathname.startsWith(routes.adminUsers)) {
      return {
        eyebrow: t("admin.breadcrumb.users"),
        title: t("admin.page.users.title"),
        description: t("admin.page.users.description"),
      };
    }
    if (location.pathname.startsWith(routes.adminCampaigns)) {
      return {
        eyebrow: t("admin.breadcrumb.campaigns"),
        title: t("admin.page.campaigns.title"),
        description: t("admin.page.campaigns.description"),
      };
    }
    if (location.pathname.startsWith(routes.adminDiagnostics)) {
      return {
        eyebrow: t("admin.breadcrumb.diagnostics"),
        title: t("admin.page.diagnostics.title"),
        description: t("admin.page.diagnostics.description"),
      };
    }
    if (location.pathname.startsWith(routes.adminCatalogItems)) {
      return {
        eyebrow: t("admin.breadcrumb.items"),
        title: t("admin.page.items.title"),
        description: t("admin.page.items.description"),
      };
    }
    return {
      eyebrow: t("admin.breadcrumb.overview"),
      title: t("admin.page.overview.title"),
      description: t("admin.page.overview.description"),
    };
  }, [location.pathname, t]);

  const displayName = user?.displayName || user?.username || t("admin.userFallback");

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.18),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.12),transparent_24%),linear-gradient(180deg,#120f19_0%,#090c14_100%)] text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col xl:flex-row">
        <aside className="border-b border-white/8 bg-[linear-gradient(180deg,rgba(20,17,29,0.96),rgba(10,12,20,0.94))] xl:sticky xl:top-0 xl:h-screen xl:w-[320px] xl:overflow-y-auto xl:border-b-0 xl:border-r">
          <div className="flex h-full min-h-full flex-col px-5 py-5">
            <div className="rounded-[28px] border border-white/8 bg-white/4 p-4 shadow-[0_20px_50px_rgba(0,0,0,0.24)]">
              <Link to={routes.adminHome} className="flex items-center gap-3">
                <BrandMark size="sm" className="shrink-0" />
                <div className="min-w-0">
                  <p className="text-base font-bold text-white">{t("admin.brandTitle")}</p>
                  <p className="text-[11px] uppercase tracking-[0.24em] text-amber-200/70">
                    {t("admin.brandSubtitle")}
                  </p>
                </div>
              </Link>
              <div className="mt-4 rounded-2xl border border-amber-400/15 bg-amber-400/10 px-3 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-amber-200/80">
                  {t("admin.badge")}
                </p>
                <p className="mt-2 text-sm text-slate-200">{displayName}</p>
                <p className="mt-1 text-xs text-slate-400">@{user?.username}</p>
              </div>
            </div>

            <nav className="mt-6 space-y-3">
              <NavLink to={routes.adminHome} end className={navLinkClassName}>
                <span>{t("admin.nav.overview")}</span>
                <span className="text-xs uppercase tracking-[0.2em] text-slate-500">
                  {t("admin.nav.core")}
                </span>
              </NavLink>

              <div className="px-1 pt-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                  {t("admin.nav.catalog")}
                </p>
              </div>

              <NavLink to={routes.adminCatalogItems} className={navLinkClassName}>
                <span>{t("admin.nav.items")}</span>
                <span className="rounded-full border border-sky-400/25 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-sky-200">
                  {t("admin.nav.base")}
                </span>
              </NavLink>

              <NavLink to={routes.adminCatalogSpells} className={navLinkClassName}>
                <span>{t("admin.nav.spells")}</span>
                <span className="rounded-full border border-violet-400/25 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-violet-200">
                  {t("admin.nav.base")}
                </span>
              </NavLink>

              <div className="px-1 pt-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                  {t("admin.nav.governance")}
                </p>
              </div>

              <NavLink to={routes.adminUsers} className={navLinkClassName}>
                <span>{t("admin.nav.users")}</span>
                <span className="rounded-full border border-amber-400/25 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-amber-100">
                  IAM
                </span>
              </NavLink>

              <NavLink to={routes.adminCampaigns} className={navLinkClassName}>
                <span>{t("admin.nav.campaigns")}</span>
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-slate-300">
                  Ops
                </span>
              </NavLink>

              <NavLink to={routes.adminDiagnostics} className={navLinkClassName}>
                <span>{t("admin.nav.diagnostics")}</span>
                <span className="rounded-full border border-emerald-400/25 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-emerald-100">
                  Health
                </span>
              </NavLink>
            </nav>

            <div className="mt-6 rounded-[28px] border border-white/8 bg-white/3 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">
                {t("admin.workspace.title")}
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                {t("admin.workspace.description")}
              </p>
              <Link
                to={routes.workspaceHome}
                className="mt-4 inline-flex items-center rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-emerald-100 transition hover:bg-emerald-400/20"
              >
                {t("admin.openWorkspace")}
              </Link>
            </div>

            <div className="mt-6 rounded-[28px] border border-white/8 bg-white/3 p-4 text-sm text-slate-400 xl:mt-auto">
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">
                {t("admin.footerTitle")}
              </p>
              <p className="mt-3 leading-6">
                {t("admin.footerDescription")}
              </p>
            </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-40 border-b border-white/8 bg-[linear-gradient(180deg,rgba(9,12,20,0.9),rgba(9,12,20,0.72))] px-5 py-5 backdrop-blur-xl xl:px-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                  {t("admin.breadcrumb.root")} / {pageMeta.eyebrow}
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  <h1 className="text-3xl font-black tracking-tight text-white">{pageMeta.title}</h1>
                  <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-100">
                    {t("admin.badge")}
                  </span>
                </div>
                <p className="max-w-3xl text-sm leading-6 text-slate-300">{pageMeta.description}</p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={toggleLocale}
                  className="rounded-full border border-white/10 bg-white/3 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 transition hover:border-white/16 hover:bg-white/8"
                >
                  {t("auth.language")} {locale === "en" ? "EN" : "PT"}
                </button>
                {onLogout && (
                  <button
                    type="button"
                    onClick={onLogout}
                    className="rounded-full border border-rose-500/25 bg-rose-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-rose-200 transition hover:bg-rose-500/18"
                  >
                    {t("auth.logout")}
                  </button>
                )}
              </div>
            </div>
          </header>

          <main className="px-5 py-8 pb-24 xl:px-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
};
