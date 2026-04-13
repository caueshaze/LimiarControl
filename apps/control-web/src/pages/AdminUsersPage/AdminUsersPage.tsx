import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { adminSystemRepo } from "../../shared/api/adminSystemRepo";
import type { AdminUser, AdminUserUpdatePayload } from "../../entities/admin-system";
import type { RoleMode } from "../../shared/types/role";
import { useLocale, useToast } from "../../shared/hooks";
import { Toast } from "../../shared/ui";

type RoleFilter = "ALL" | RoleMode;
type AdminFilter = "all" | "admins" | "non_admins";
type UserDraftMap = Record<string, { role: RoleMode; isSystemAdmin: boolean }>;

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

export const AdminUsersPage = () => {
  const { t, locale } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [drafts, setDrafts] = useState<UserDraftMap>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("ALL");
  const [adminFilter, setAdminFilter] = useState<AdminFilter>("all");
  const [savingUserId, setSavingUserId] = useState<string | null>(null);
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const result = await adminSystemRepo.listUsers({
        search: deferredSearch.trim() || undefined,
        role: roleFilter === "ALL" ? undefined : roleFilter,
        isSystemAdmin:
          adminFilter === "all" ? undefined : adminFilter === "admins",
        limit: 200,
      });
      setUsers(result);
      setDrafts(
        Object.fromEntries(
          result.map((user) => [
            user.id,
            { role: user.role, isSystemAdmin: user.isSystemAdmin },
          ]),
        ),
      );
    } catch (error) {
      showToast({
        variant: "error",
        title: t("admin.users.loadErrorTitle"),
        description:
          error instanceof Error ? error.message : t("admin.users.loadErrorDescription"),
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, [deferredSearch, roleFilter, adminFilter]);

  const userCards = useMemo(
    () =>
      users.map((user) => {
        const draft = drafts[user.id] ?? {
          role: user.role,
          isSystemAdmin: user.isSystemAdmin,
        };
        const dirty =
          draft.role !== user.role || draft.isSystemAdmin !== user.isSystemAdmin;
        return { user, draft, dirty };
      }),
    [drafts, users],
  );

  const handleDraftChange = (
    userId: string,
    patch: Partial<{ role: RoleMode; isSystemAdmin: boolean }>,
  ) => {
    setDrafts((current) => ({
      ...current,
      [userId]: {
        role: patch.role ?? current[userId]?.role ?? "PLAYER",
        isSystemAdmin:
          patch.isSystemAdmin ?? current[userId]?.isSystemAdmin ?? false,
      },
    }));
  };

  const handleSave = async (user: AdminUser) => {
    const draft = drafts[user.id];
    if (!draft) {
      return;
    }

    const payload: AdminUserUpdatePayload = {};
    if (draft.role !== user.role) {
      payload.role = draft.role;
    }
    if (draft.isSystemAdmin !== user.isSystemAdmin) {
      payload.isSystemAdmin = draft.isSystemAdmin;
    }
    if (Object.keys(payload).length === 0) {
      return;
    }

    setSavingUserId(user.id);
    try {
      const updated = await adminSystemRepo.updateUser(user.id, payload);
      setUsers((current) =>
        current.map((entry) => (entry.id === updated.id ? updated : entry)),
      );
      setDrafts((current) => ({
        ...current,
        [updated.id]: { role: updated.role, isSystemAdmin: updated.isSystemAdmin },
      }));
      showToast({
        variant: "success",
        title: t("admin.users.saveSuccessTitle"),
        description: t("admin.users.saveSuccessDescription"),
      });
    } catch (error) {
      showToast({
        variant: "error",
        title: t("admin.users.saveErrorTitle"),
        description:
          error instanceof Error ? error.message : t("admin.users.saveErrorDescription"),
      });
    } finally {
      setSavingUserId(null);
    }
  };

  const handleDelete = async (user: AdminUser) => {
    const confirmed = window.confirm(
      t("admin.users.deleteConfirm").replace("{name}", user.displayName),
    );
    if (!confirmed) {
      return;
    }

    setDeletingUserId(user.id);
    try {
      await adminSystemRepo.deleteUser(user.id);
      setUsers((current) => current.filter((entry) => entry.id !== user.id));
      setDrafts((current) => {
        const next = { ...current };
        delete next[user.id];
        return next;
      });
      showToast({
        variant: "success",
        title: t("admin.users.deleteSuccessTitle"),
        description: t("admin.users.deleteSuccessDescription"),
      });
    } catch (error) {
      showToast({
        variant: "error",
        title: t("admin.users.deleteErrorTitle"),
        description:
          error instanceof Error ? error.message : t("admin.users.deleteErrorDescription"),
      });
    } finally {
      setDeletingUserId(null);
    }
  };

  return (
    <>
      <Toast toast={toast} onClose={clearToast} />
      <section className="space-y-6">
        <section className="rounded-[30px] border border-white/8 bg-white/4 p-6">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_repeat(2,minmax(180px,0.35fr))]">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("admin.users.filters.search")}
              </span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("admin.users.filters.searchPlaceholder")}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white placeholder:text-slate-500"
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("admin.users.filters.role")}
              </span>
              <select
                value={roleFilter}
                onChange={(event) => setRoleFilter(event.target.value as RoleFilter)}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white"
              >
                <option value="ALL">{t("admin.users.filters.allRoles")}</option>
                <option value="GM">GM</option>
                <option value="PLAYER">Player</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("admin.users.filters.admin")}
              </span>
              <select
                value={adminFilter}
                onChange={(event) => setAdminFilter(event.target.value as AdminFilter)}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white"
              >
                <option value="all">{t("admin.users.filters.allAdmins")}</option>
                <option value="admins">{t("admin.users.filters.onlyAdmins")}</option>
                <option value="non_admins">{t("admin.users.filters.onlyNonAdmins")}</option>
              </select>
            </label>
          </div>
        </section>

        {loading ? (
          <div className="rounded-[30px] border border-white/8 bg-white/4 p-6 text-sm text-slate-400">
            {t("admin.users.loading")}
          </div>
        ) : userCards.length === 0 ? (
          <div className="rounded-[30px] border border-white/8 bg-white/4 p-6 text-sm text-slate-400">
            {t("admin.users.empty")}
          </div>
        ) : (
          <div className="space-y-4">
            {userCards.map(({ user, draft, dirty }) => (
              <section
                key={user.id}
                className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.92))] p-6"
              >
                <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="text-2xl font-semibold text-white">{user.displayName}</h2>
                      <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-slate-400">
                        @{user.username}
                      </span>
                      {user.isSystemAdmin && (
                        <span className="rounded-full border border-amber-400/25 bg-amber-400/10 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-amber-100">
                          {t("admin.badge")}
                        </span>
                      )}
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                          {t("admin.users.stats.campaigns")}
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">{user.campaignsCount}</p>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                          {t("admin.users.stats.gmCampaigns")}
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">{user.gmCampaignsCount}</p>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                          {t("admin.users.stats.parties")}
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">{user.partiesCount}</p>
                      </div>
                    </div>
                    <p className="text-xs text-slate-500">
                      {t("admin.users.createdAt")}: {formatDateTime(user.createdAt, locale)}
                    </p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[380px]">
                    <label className="space-y-2">
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                        {t("admin.users.roleLabel")}
                      </span>
                      <select
                        value={draft.role}
                        onChange={(event) =>
                          handleDraftChange(user.id, { role: event.target.value as RoleMode })
                        }
                        className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white"
                      >
                        <option value="GM">GM</option>
                        <option value="PLAYER">Player</option>
                      </select>
                    </label>

                    <label className="space-y-2">
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                        {t("admin.users.adminLabel")}
                      </span>
                      <select
                        value={draft.isSystemAdmin ? "true" : "false"}
                        onChange={(event) =>
                          handleDraftChange(user.id, {
                            isSystemAdmin: event.target.value === "true",
                          })
                        }
                        className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white"
                      >
                        <option value="true">{t("admin.users.adminYes")}</option>
                        <option value="false">{t("admin.users.adminNo")}</option>
                      </select>
                    </label>

                    <div className="sm:col-span-2 flex items-center justify-between gap-4 rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
                      <p className={`text-xs uppercase tracking-[0.18em] ${dirty ? "text-amber-200" : "text-slate-500"}`}>
                        {dirty ? t("admin.users.pendingChanges") : t("admin.users.synced")}
                      </p>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          disabled={deletingUserId === user.id}
                          onClick={() => {
                            void handleDelete(user);
                          }}
                          className="rounded-full border border-rose-500/25 bg-rose-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-rose-200 transition hover:bg-rose-500/18 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {deletingUserId === user.id
                            ? t("admin.users.deleting")
                            : t("admin.users.deleteAction")}
                        </button>
                        <button
                          type="button"
                          disabled={!dirty || savingUserId === user.id || deletingUserId === user.id}
                          onClick={() => {
                            void handleSave(user);
                          }}
                          className="rounded-full border border-amber-400/25 bg-amber-400/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-amber-100 transition hover:bg-amber-400/18 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {savingUserId === user.id
                            ? t("admin.users.saving")
                            : t("admin.users.saveAction")}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            ))}
          </div>
        )}
      </section>
    </>
  );
};
