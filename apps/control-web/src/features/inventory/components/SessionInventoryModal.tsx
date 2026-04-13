import { useEffect, useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import {
  sessionsRepo,
  type SessionHealingConsumableTarget,
  type SessionUseConsumableResult,
} from "../../../shared/api/sessionsRepo";
import type { LocaleKey } from "../../../shared/i18n";
import { useLocale } from "../../../shared/hooks/useLocale";
import {
  buildInventoryGroupsFromResolved,
  filterInventoryEntries,
  getInventoryItemName,
  isHealingConsumable,
  resolveInventoryEntries,
  type SessionInventoryFilterGroup,
} from "./sessionInventoryPanel.utils";
import { SessionInventoryModalItem } from "./SessionInventoryModalItem";
import { HealingConsumableDialog } from "./HealingConsumableDialog";

type Props = {
  activeSessionId?: string | null;
  combatActive?: boolean;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  locale: "en" | "pt" | string;
  open: boolean;
  selectedArmorId?: string | null;
  selectedWeaponId?: string | null;
  onConsumableUsed?: (result: SessionUseConsumableResult) => void | Promise<void>;
  onConsumableUseError?: (message: string) => void;
  onClose: () => void;
};

export const SessionInventoryModal = ({
  activeSessionId = null,
  combatActive = false,
  inventory,
  itemsById,
  locale,
  open,
  selectedArmorId = null,
  selectedWeaponId = null,
  onConsumableUsed,
  onConsumableUseError,
  onClose,
}: Props) => {
  const { t } = useLocale();
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState<SessionInventoryFilterGroup>("all");
  const [equippedOnly, setEquippedOnly] = useState(false);
  const [healingTargets, setHealingTargets] = useState<SessionHealingConsumableTarget[]>([]);
  const [loadingTargets, setLoadingTargets] = useState(false);
  const [consumableCandidate, setConsumableCandidate] = useState<{
    entry: InventoryItem;
    item: Item;
  } | null>(null);
  const [selectedTargetUserId, setSelectedTargetUserId] = useState("");
  const [rollMode, setRollMode] = useState<"system" | "manual">("system");
  const [manualRolls, setManualRolls] = useState<number[]>([]);
  const [submittingConsumable, setSubmittingConsumable] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose, open]);

  useEffect(() => {
    if (!open) return;
    setSearch("");
    setGroup("all");
    setEquippedOnly(false);
    setConsumableCandidate(null);
    setSelectedTargetUserId("");
    setRollMode("system");
    setManualRolls([]);
  }, [open]);

  useEffect(() => {
    if (!open || !activeSessionId || combatActive) {
      setHealingTargets([]);
      setLoadingTargets(false);
      return;
    }

    let active = true;
    setLoadingTargets(true);
    sessionsRepo
      .listHealingConsumableTargets(activeSessionId)
      .then((targets) => {
        if (!active) return;
        setHealingTargets(targets);
      })
      .catch((error) => {
        if (!active) return;
        setHealingTargets([]);
        onConsumableUseError?.(
          (error as { message?: string })?.message ??
            t("playerBoard.consumableUseErrorDescription"),
        );
      })
      .finally(() => {
        if (active) {
          setLoadingTargets(false);
        }
      });

    return () => {
      active = false;
    };
  }, [activeSessionId, combatActive, onConsumableUseError, open, t]);

  useEffect(() => {
    if (!consumableCandidate) {
      return;
    }
    if (selectedTargetUserId) {
      return;
    }
    const selfTarget = healingTargets.find((target) => target.isSelf);
    const fallbackTarget = selfTarget ?? healingTargets[0];
    setSelectedTargetUserId(fallbackTarget?.playerUserId ?? "");
  }, [consumableCandidate, healingTargets, selectedTargetUserId]);

  if (!open) {
    return null;
  }

  const resolvedEntries = resolveInventoryEntries(inventory, itemsById, locale);
  const filteredEntries = filterInventoryEntries(resolvedEntries, {
    equippedOnly,
    group,
    search,
  });
  const groups = buildInventoryGroupsFromResolved(filteredEntries);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/65 px-4 pb-0 pt-6 backdrop-blur-sm sm:items-center sm:pb-6"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[88vh] w-full max-w-4xl flex-col overflow-hidden rounded-t-4xl border border-white/10 bg-[linear-gradient(180deg,rgba(10,14,30,0.98),rgba(3,7,20,0.98))] shadow-2xl sm:rounded-4xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="border-b border-white/8 px-6 pb-5 pt-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                {t("playerBoard.inventoryStateLabel")}
              </p>
              <h2 className="mt-2 text-xl font-bold text-white">
                {t("playerBoard.inventoryTitle")}
              </h2>
              <p className="mt-2 text-sm text-slate-400">
                {inventory?.length ?? 0} {t("playerBoard.inventoryDistinctItems")}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-white/10 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300 transition hover:border-white/20 hover:text-white"
            >
              {t("playerBoard.closeInventoryModal")}
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          {inventory === null ? (
            <p className="text-sm text-slate-400">{t("inventory.loading")}</p>
          ) : inventory.length === 0 ? (
            <p className="text-sm text-slate-400">{t("inventory.empty")}</p>
          ) : (
            <div className="space-y-5">
              <div className="space-y-3 rounded-3xl border border-white/8 bg-white/3 p-4">
                <div className="flex flex-col gap-3 lg:flex-row">
                  <input
                    type="text"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder={t("inventory.searchPlaceholder")}
                    className="flex-1 rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-amber-400/60 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setEquippedOnly((current) => !current)}
                    className={`rounded-2xl border px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] transition ${
                      equippedOnly
                        ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200"
                        : "border-white/10 bg-white/4 text-slate-300 hover:border-white/20"
                    }`}
                  >
                    {t("inventory.equippedOnly")}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(["all", "weapon", "armor", "magic", "consumable", "misc"] as const).map((entryGroup) => (
                    <button
                      key={entryGroup}
                      type="button"
                      onClick={() => setGroup(entryGroup)}
                      className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] transition ${
                        group === entryGroup
                          ? "border-amber-400/40 bg-amber-400/10 text-amber-200"
                          : "border-white/10 bg-white/3 text-slate-400 hover:border-white/20"
                      }`}
                    >
                      {entryGroup === "all" ? t("inventory.filterAll") : getInventoryGroupLabel(entryGroup, t)}
                    </button>
                  ))}
                </div>
              </div>

              {filteredEntries.length === 0 ? (
                <p className="text-sm text-slate-400">{t("inventory.emptyFiltered")}</p>
              ) : null}

              {groups.map((section) => (
                <section key={section.group} className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="h-px flex-1 bg-white/8" />
                    <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                      {getInventoryGroupLabel(section.group, t)}
                    </p>
                    <span className="h-px flex-1 bg-white/8" />
                  </div>
                  <div className="space-y-3">
                    {section.entries.map((resolved) => {
                      const handleUseHealingConsumable =
                        resolved.item && isHealingConsumable(resolved.item)
                          ? (() => {
                              const item = resolved.item;
                              return () => {
                                setConsumableCandidate({
                                  entry: resolved.entry,
                                  item,
                                });
                                setSelectedTargetUserId("");
                                setRollMode("system");
                                setManualRolls([]);
                              };
                            })()
                          : undefined;
                      const canUseHealingConsumable =
                        Boolean(activeSessionId) && !combatActive && Boolean(handleUseHealingConsumable);

                      return (
                        <SessionInventoryModalItem
                          key={resolved.entry.id}
                          canUseHealingConsumable={canUseHealingConsumable}
                          entry={resolved.entry}
                          item={resolved.item ?? undefined}
                          isCurrentArmor={resolved.entry.id === selectedArmorId}
                          isCurrentWeapon={resolved.entry.id === selectedWeaponId}
                          locale={locale}
                          onUseHealingConsumable={
                            canUseHealingConsumable ? handleUseHealingConsumable : undefined
                          }
                        />
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>

        {consumableCandidate && (
          <HealingConsumableDialog
            activeSessionId={activeSessionId}
            item={consumableCandidate.item}
            targets={healingTargets}
            loadingTargets={loadingTargets}
            manualRolls={manualRolls}
            rollMode={rollMode}
            selectedTargetUserId={selectedTargetUserId}
            submitting={submittingConsumable}
            combatActive={combatActive}
            onClose={() => {
              setConsumableCandidate(null);
              setSelectedTargetUserId("");
              setRollMode("system");
              setManualRolls([]);
            }}
            onManualRollSelect={(value) => setManualRolls((current) => [...current, value])}
            onManualRollsClear={() => setManualRolls([])}
            onRollModeChange={(value) => {
              setRollMode(value);
              setManualRolls([]);
            }}
            onTargetChange={setSelectedTargetUserId}
            onSubmit={async (payload) => {
              if (!activeSessionId) {
                onConsumableUseError?.(t("playerBoard.consumableUseErrorDescription"));
                return;
              }
              setSubmittingConsumable(true);
              try {
                const result = await sessionsRepo.useConsumable(activeSessionId, {
                  inventoryItemId: consumableCandidate.entry.id,
                  targetPlayerUserId: selectedTargetUserId || null,
                  rollSource: payload.rollSource,
                  manualRolls: payload.manualRolls,
                });
                await onConsumableUsed?.(result);
                setConsumableCandidate(null);
                setSelectedTargetUserId("");
                setRollMode("system");
                setManualRolls([]);
              } catch (error) {
                onConsumableUseError?.(
                  (error as { message?: string })?.message ??
                    t("playerBoard.consumableUseErrorDescription"),
                );
              } finally {
                setSubmittingConsumable(false);
              }
            }}
          />
        )}
      </div>
    </div>
  );
};

const getInventoryGroupLabel = (
  group: "weapon" | "armor" | "magic" | "consumable" | "misc",
  t: (key: LocaleKey) => string,
) => {
  switch (group) {
    case "weapon":
      return t("playerParty.itemTypeWeapon");
    case "armor":
      return t("playerParty.itemTypeArmor");
    case "magic":
      return t("playerParty.itemTypeMagic");
    case "consumable":
      return t("playerParty.itemTypeConsumable");
    default:
      return t("playerParty.itemTypeMisc");
  }
};
