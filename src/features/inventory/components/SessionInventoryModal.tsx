import { useEffect, useState } from "react";
import { getItemPropertyLabels } from "../../../entities/item";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import type { LocaleKey } from "../../../shared/i18n";
import { useLocale } from "../../../shared/hooks/useLocale";
import { buildInventoryGroups, getInventoryItemName } from "./sessionInventoryPanel.utils";

type Props = {
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  open: boolean;
  selectedArmorId?: string | null;
  selectedWeaponId?: string | null;
  onClose: () => void;
};

export const SessionInventoryModal = ({
  inventory,
  itemsById,
  open,
  selectedArmorId = null,
  selectedWeaponId = null,
  onClose,
}: Props) => {
  const { t } = useLocale();

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

  if (!open) {
    return null;
  }

  const groups = buildInventoryGroups(inventory, itemsById);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/65 px-4 pb-0 pt-6 backdrop-blur-sm sm:items-center sm:pb-6"
      onClick={onClose}
    >
      <div
        className="flex max-h-[88vh] w-full max-w-4xl flex-col overflow-hidden rounded-t-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(10,14,30,0.98),rgba(3,7,20,0.98))] shadow-2xl sm:rounded-[32px]"
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
                    {section.entries.map((resolved) => (
                      <SessionInventoryModalItem
                        key={resolved.entry.id}
                        entry={resolved.entry}
                        item={resolved.item ?? undefined}
                        isCurrentArmor={resolved.entry.id === selectedArmorId}
                        isCurrentWeapon={resolved.entry.id === selectedWeaponId}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>
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

const SessionInventoryModalItem = ({
  entry,
  item,
  isCurrentArmor,
  isCurrentWeapon,
}: {
  entry: InventoryItem;
  item?: Item;
  isCurrentArmor: boolean;
  isCurrentWeapon: boolean;
}) => {
  const { locale, t } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const propertyLabels = getItemPropertyLabels(item?.properties, locale);
  const hasDetails = Boolean(
    item?.description ||
      item?.damageDice ||
      item?.armorClassBase != null ||
      item?.rangeMeters != null ||
      item?.weight != null ||
      propertyLabels.length > 0 ||
      entry.notes,
  );

  return (
    <div className="overflow-hidden rounded-[24px] border border-white/8 bg-white/[0.04]">
      <button
        type="button"
        onClick={() => hasDetails && setExpanded((current) => !current)}
        className={`flex w-full items-start justify-between gap-4 px-4 py-3 text-left ${hasDetails ? "hover:bg-white/[0.03]" : ""}`}
      >
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white">
            {getInventoryItemName(entry, item)}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="rounded-full border border-slate-700 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-300">
              x{entry.quantity}
            </span>
            {entry.isEquipped && (
              <span className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-300">
                {t("inventory.equipped")}
              </span>
            )}
            {isCurrentWeapon && (
              <span className="rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-200">
                {t("playerBoard.currentWeaponBadge")}
              </span>
            )}
            {isCurrentArmor && (
              <span className="rounded-full border border-sky-500/25 bg-sky-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-sky-200">
                {t("playerBoard.currentArmorBadge")}
              </span>
            )}
          </div>
        </div>
        {hasDetails && (
          <span className={`pt-1 text-slate-500 transition-transform ${expanded ? "rotate-180" : ""}`}>
            ▼
          </span>
        )}
      </button>
      {expanded && hasDetails && (
        <div className="space-y-3 border-t border-white/8 px-4 py-4 text-xs text-slate-300">
          {item?.description && <p className="text-sm leading-6 text-slate-400">{item.description}</p>}
          <div className="grid gap-2 sm:grid-cols-2">
            {item?.damageDice && (
              <DetailPill label={t("inventory.damage")} value={`${item.damageDice}${item.damageType ? ` ${item.damageType}` : ""}`} />
            )}
            {item?.armorClassBase != null && (
              <DetailPill label={t("playerBoard.armorClassLabel")} value={String(item.armorClassBase)} />
            )}
            {item?.rangeMeters != null && (
              <DetailPill label={t("inventory.range")} value={`${item.rangeMeters}m`} />
            )}
            {item?.weight != null && (
              <DetailPill label={t("inventory.weight")} value={String(item.weight)} />
            )}
            {propertyLabels.length > 0 && (
              <DetailPill label={t("inventory.properties")} value={propertyLabels.join(", ")} />
            )}
            {entry.notes && (
              <DetailPill label={t("inventory.notes")} value={entry.notes} />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const DetailPill = ({ label, value }: { label: string; value: string }) => (
  <p className="rounded-xl bg-slate-950/50 px-3 py-2">
    <span className="text-slate-500">{label}</span> {value}
  </p>
);
