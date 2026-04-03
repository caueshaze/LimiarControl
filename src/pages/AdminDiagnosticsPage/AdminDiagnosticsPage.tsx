import { useEffect, useState } from "react";
import { adminSystemRepo } from "../../shared/api/adminSystemRepo";
import type { AdminDiagnostics } from "../../entities/admin-system";
import { useLocale } from "../../shared/hooks/useLocale";

const formatDateTime = (value: string | null | undefined, locale: "pt" | "en") => {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(locale === "pt" ? "pt-BR" : "en-US");
};

export const AdminDiagnosticsPage = () => {
  const { t, locale } = useLocale();
  const [diagnostics, setDiagnostics] = useState<AdminDiagnostics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadDiagnostics = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await adminSystemRepo.diagnostics();
        if (!cancelled) {
          setDiagnostics(result);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : t("admin.diagnostics.loadErrorDescription"),
          );
          setDiagnostics(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadDiagnostics();
    return () => {
      cancelled = true;
    };
  }, [t]);

  return (
    <section className="space-y-6">
      {loading ? (
        <div className="rounded-[30px] border border-white/8 bg-white/4 p-6 text-sm text-slate-400">
          {t("admin.diagnostics.loading")}
        </div>
      ) : error ? (
        <div className="rounded-[30px] border border-rose-500/25 bg-rose-500/10 p-6 text-sm text-rose-200">
          <p className="font-semibold">{t("admin.diagnostics.loadErrorTitle")}</p>
          <p className="mt-3">{error}</p>
        </div>
      ) : diagnostics ? (
        <>
          <section className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-[30px] border border-white/8 bg-white/4 p-6">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                {t("admin.diagnostics.database")}
              </p>
              <div className="mt-3 flex items-center gap-3">
                <span
                  className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${
                    diagnostics.databaseOk
                      ? "border border-emerald-400/25 bg-emerald-400/10 text-emerald-100"
                      : "border border-rose-500/25 bg-rose-500/10 text-rose-200"
                  }`}
                >
                  {diagnostics.databaseOk
                    ? t("admin.diagnostics.databaseOk")
                    : t("admin.diagnostics.databaseError")}
                </span>
              </div>
              <p className="mt-4 text-sm text-slate-300">{diagnostics.databaseMessage || "—"}</p>
            </div>

            <div className="rounded-[30px] border border-white/8 bg-white/4 p-6">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                {t("admin.diagnostics.environment")}
              </p>
              <p className="mt-4 text-2xl font-black text-white">{diagnostics.appEnv}</p>
              <p className="mt-2 text-sm text-slate-400">
                {t("admin.diagnostics.autoMigrate")}:{" "}
                {diagnostics.autoMigrate ? t("admin.users.adminYes") : t("admin.users.adminNo")}
              </p>
            </div>

            <div className="rounded-[30px] border border-white/8 bg-white/4 p-6">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                {t("admin.diagnostics.timestamp")}
              </p>
              <p className="mt-4 text-sm leading-7 text-slate-200">
                {formatDateTime(diagnostics.utcNow, locale)}
              </p>
            </div>
          </section>

          <section className="rounded-[30px] border border-white/8 bg-white/4 p-6">
            <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
              {t("admin.diagnostics.runtimeTitle")}
            </p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {[
                ["users", diagnostics.usersTotal],
                ["campaigns", diagnostics.campaignsTotal],
                ["parties", diagnostics.partiesTotal],
                ["sessions", diagnostics.sessionsTotal],
                ["activeSessions", diagnostics.activeSessionsTotal],
                ["activeCombats", diagnostics.activeCombatsTotal],
              ].map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-[24px] border border-white/8 bg-black/20 px-4 py-4"
                >
                  <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                    {t(`admin.diagnostics.metrics.${key}` as never)}
                  </p>
                  <p className="mt-3 text-3xl font-black text-white">{value}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </section>
  );
};
