import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { adminSystemRepo } from "../../shared/api/adminSystemRepo";
import type { AdminOverview } from "../../entities/admin-system";
import { useLocale } from "../../shared/hooks/useLocale";

export const AdminHomePage = () => {
  const { t } = useLocale();
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadOverview = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await adminSystemRepo.overview();

        if (!cancelled) {
          setOverview(result);
        }
      } catch (loadError) {
        if (!cancelled) {
          const message =
            loadError instanceof Error
              ? loadError.message
              : t("admin.overview.loadErrorDescription");
          setError(message);
          setOverview(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadOverview();
    return () => {
      cancelled = true;
    };
  }, [t]);

  return (
    <section className="space-y-6">
      <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(17,24,39,0.82),rgba(7,10,18,0.94))] p-6 shadow-[0_30px_90px_rgba(0,0,0,0.24)]">
        <div className="grid gap-4 lg:grid-cols-2">
          <Link
            to={routes.adminCatalogItems}
            className="rounded-[28px] border border-sky-400/18 bg-sky-400/10 p-5 transition hover:border-sky-300/32 hover:bg-sky-400/14"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-200/80">
              {t("admin.quickLinks.catalog")}
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">
              {t("admin.quickLinks.itemsTitle")}
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-200">
              {t("admin.quickLinks.itemsDescription")}
            </p>
          </Link>

          <Link
            to={routes.adminCatalogSpells}
            className="rounded-[28px] border border-violet-400/18 bg-violet-400/10 p-5 transition hover:border-violet-300/32 hover:bg-violet-400/14"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-200/80">
              {t("admin.quickLinks.catalog")}
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">
              {t("admin.quickLinks.spellsTitle")}
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-200">
              {t("admin.quickLinks.spellsDescription")}
            </p>
          </Link>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <Link
            to={routes.adminUsers}
            className="rounded-[28px] border border-amber-400/18 bg-amber-400/10 p-5 transition hover:border-amber-300/32 hover:bg-amber-400/14"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-200/80">
              {t("admin.quickLinks.governance")}
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">
              {t("admin.quickLinks.usersTitle")}
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-200">
              {t("admin.quickLinks.usersDescription")}
            </p>
          </Link>
          <Link
            to={routes.adminCampaigns}
            className="rounded-[28px] border border-white/12 bg-white/5 p-5 transition hover:border-white/18 hover:bg-white/8"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {t("admin.quickLinks.operations")}
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">
              {t("admin.quickLinks.campaignsTitle")}
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-200">
              {t("admin.quickLinks.campaignsDescription")}
            </p>
          </Link>
          <Link
            to={routes.adminDiagnostics}
            className="rounded-[28px] border border-emerald-400/18 bg-emerald-400/10 p-5 transition hover:border-emerald-300/32 hover:bg-emerald-400/14"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-200/80">
              {t("admin.quickLinks.health")}
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">
              {t("admin.quickLinks.diagnosticsTitle")}
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-200">
              {t("admin.quickLinks.diagnosticsDescription")}
            </p>
          </Link>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.95fr)]">
        <section className="rounded-[32px] border border-white/8 bg-white/4 p-6">
          <div className="flex items-center justify-between gap-4 border-b border-white/8 pb-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                {t("admin.state.eyebrow")}
              </p>
              <h3 className="mt-2 text-2xl font-semibold text-white">
                {t("admin.state.title")}
              </h3>
            </div>
            <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-slate-400">
              {t("admin.badge")}
            </span>
          </div>

          {loading ? (
            <p className="mt-5 text-sm text-slate-400">{t("admin.overview.loading")}</p>
          ) : error ? (
            <div className="mt-5 rounded-2xl border border-rose-500/25 bg-rose-500/10 p-4 text-sm text-rose-200">
              <p className="font-semibold">{t("admin.overview.loadErrorTitle")}</p>
              <p className="mt-2">{error}</p>
            </div>
          ) : overview ? (
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div className="rounded-[28px] border border-sky-400/18 bg-sky-400/10 p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-200/80">
                  {t("admin.metrics.items")}
                </p>
                <div className="mt-4 flex items-end gap-4">
                  <div>
                    <p className="text-3xl font-black text-white">{overview.baseItemsActive}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">
                      {t("admin.metrics.active")}
                    </p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-200">{overview.baseItemsInactive}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                      {t("admin.metrics.inactive")}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-[28px] border border-violet-400/18 bg-violet-400/10 p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-200/80">
                  {t("admin.metrics.spells")}
                </p>
                <div className="mt-4 flex items-end gap-4">
                  <div>
                    <p className="text-3xl font-black text-white">{overview.baseSpellsActive}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">
                      {t("admin.metrics.active")}
                    </p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-200">{overview.baseSpellsInactive}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                      {t("admin.metrics.inactive")}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-[28px] border border-white/10 bg-black/20 p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  {t("admin.metrics.users")}
                </p>
                <p className="mt-4 text-3xl font-black text-white">{overview.usersTotal}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-400">
                  {t("admin.metrics.systemAdmins")}: {overview.systemAdminsTotal}
                </p>
              </div>

              <div className="rounded-[28px] border border-white/10 bg-black/20 p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  {t("admin.metrics.campaigns")}
                </p>
                <p className="mt-4 text-3xl font-black text-white">{overview.campaignsTotal}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-400">
                  {t("admin.metrics.parties")}: {overview.partiesTotal}
                </p>
              </div>
            </div>
          ) : null}
        </section>

        <section className="rounded-[32px] border border-white/8 bg-white/4 p-6">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
            {t("admin.runtime.eyebrow")}
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-white">
            {t("admin.runtime.title")}
          </h3>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            {t("admin.runtime.description")}
          </p>

          {overview ? (
            <div className="mt-5 grid gap-3">
              {[
                [t("admin.metrics.sessions"), overview.sessionsTotal],
                [t("admin.metrics.activeSessions"), overview.activeSessionsTotal],
                [t("admin.metrics.parties"), overview.partiesTotal],
              ].map(([label, value]) => (
                <div
                  key={String(label)}
                  className="rounded-2xl border border-white/8 bg-black/20 px-4 py-4"
                >
                  <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                    {label}
                  </p>
                  <p className="mt-3 text-3xl font-black text-white">{value}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-white/8 bg-black/20 px-4 py-4 text-sm text-slate-400">
              {t("admin.runtime.empty")}
            </div>
          )}
        </section>
      </div>
    </section>
  );
};
