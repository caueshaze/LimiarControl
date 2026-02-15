import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useEffect, useState } from "react";
import { useShop } from "../../features/shop";
import { InventoryList, useInventory } from "../../features/inventory";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { useAuth } from "../../features/auth";
import { membersRepo } from "../../shared/api/membersRepo";
import type { RoleMode } from "../../shared/types/role";

export const InventoryPage = () => {
  const { items, selectedCampaignId } = useShop();
  const { user } = useAuth();
  const isGm = user?.role === "GM";
  const [members, setMembers] = useState<Array<{ id: string; displayName: string; roleMode: RoleMode }>>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [selectedMemberId, setSelectedMemberId] = useState<string | null>(null);
  const { inventory, inventoryLoading, inventoryError, toggleEquipped } =
    useInventory({ memberId: isGm ? selectedMemberId : undefined });
  const { t } = useLocale();
  const { toast, showToast, clearToast } = useToast();

  useEffect(() => {
    if (!inventoryError) {
      return;
    }
    showToast({
      variant: "error",
      title: t("inventory.loadErrorTitle"),
      description: t("inventory.loadErrorDescription"),
    });
  }, [inventoryError, showToast, t]);

  useEffect(() => {
    if (!selectedCampaignId || !isGm) {
      setMembers([]);
      setSelectedMemberId(null);
      return;
    }
    let active = true;
    setMembersLoading(true);
    membersRepo
      .list(selectedCampaignId)
      .then((data) => {
        if (!active) return;
        const players = Array.isArray(data)
          ? data.filter((member) => member.roleMode === "PLAYER")
          : [];
        setMembers(players);
        if (players.length > 0) {
          setSelectedMemberId((current) =>
            players.some((entry) => entry.id === current) ? current : players[0].id
          );
        } else {
          setSelectedMemberId(null);
        }
      })
      .finally(() => {
        if (!active) return;
        setMembersLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedCampaignId, isGm]);

  if (!selectedCampaignId) {
    return (
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold">{t("inventory.title")}</h1>
        <p className="text-sm text-slate-400">
          {t("inventory.noCampaign")}
        </p>
        <Link
          to={isGm ? routes.gmHome : routes.join}
          className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200"
        >
          {t("inventory.goCampaigns")}
        </Link>
      </section>
    );
  }

  const itemsById = items.reduce<Record<string, (typeof items)[number]>>(
    (acc, item) => {
      acc[item.id] = item;
      return acc;
    },
    {}
  );

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      <header>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          {t("inventory.title")}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">
          {t("inventory.subtitle")}
        </h1>
        <p className="mt-3 text-sm text-slate-400">
          {t("inventory.description")}
        </p>
        <div className="mt-4">
            <Link
              to={
                isGm && selectedCampaignId
                  ? routes.gmDashboard.replace(":campaignId", selectedCampaignId)
                : selectedCampaignId
                  ? routes.board.replace(":campaignId", selectedCampaignId)
                  : routes.playerHome
            }
            className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-800"
          >
            ← Back
          </Link>
        </div>
      </header>
      {isGm && (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-5">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            {t("inventory.playersTitle")}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.2em]">
            {membersLoading && (
              <span className="rounded-full border border-slate-700 px-3 py-1 text-slate-300">
                {t("inventory.playersLoading")}
              </span>
            )}
            {!membersLoading && members.length === 0 && (
              <span className="rounded-full border border-slate-700 px-3 py-1 text-slate-300">
                {t("inventory.playersEmpty")}
              </span>
            )}
            {!membersLoading &&
              members.map((member) => (
                <button
                  key={member.id}
                  type="button"
                  onClick={() => setSelectedMemberId(member.id)}
                  className={
                    member.id === selectedMemberId
                      ? "rounded-full bg-slate-100 px-3 py-1 text-slate-900"
                      : "rounded-full border border-slate-700 px-3 py-1 text-slate-200 hover:border-slate-500"
                  }
                >
                  {member.displayName}
                </button>
              ))}
          </div>
        </div>
      )}
      {inventoryLoading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
          {t("inventory.loading")}
        </div>
      ) : (
        <>
          {isGm && !selectedMemberId ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
              {t("inventory.playersSelect")}
            </div>
          ) : (
            <InventoryList
              inventory={inventory}
              itemsById={itemsById}
              onToggleEquipped={toggleEquipped}
            />
          )}
        </>
      )}
    </section>
  );
};
