import { useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";

type InventoryItemRowProps = {
  entry: InventoryItem;
  item: Item | undefined;
  onToggleEquipped: () => void;
};

export const InventoryItemRow = ({
  entry,
  item,
  onToggleEquipped,
}: InventoryItemRowProps) => {
  const { t } = useLocale();
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-100">
            {item?.name ?? t("inventory.unknownItem")}
          </p>
          <p className="text-xs text-slate-400">
            {item?.type ?? t("inventory.unknownType")}
          </p>
          {item?.description && (
            <p className="mt-2 text-xs text-slate-500">{item.description}</p>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-200">
          <span className="rounded-full border border-slate-700 px-3 py-1">
            {entry.quantity}
          </span>
          {item && (
            <button
              type="button"
              onClick={() => setExpanded((value) => !value)}
              className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200"
            >
              {expanded ? t("inventory.hideDetails") : t("inventory.showDetails")}
            </button>
          )}
          <button
            type="button"
            onClick={onToggleEquipped}
            className={
              entry.isEquipped
                ? "rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-900"
                : "rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200"
            }
          >
            {entry.isEquipped ? t("inventory.equipped") : t("inventory.equip")}
          </button>
        </div>
      </div>
      {expanded && item && (
        <div className="mt-3 space-y-2 text-xs text-slate-300">
          {item.damageDice && (
            <p>
              <span className="text-slate-400">{t("inventory.damage")}</span>{" "}
              {item.damageDice}
            </p>
          )}
          {item.rangeMeters !== undefined && item.rangeMeters !== null && (
            <p>
              <span className="text-slate-400">{t("inventory.range")}</span>{" "}
              {item.rangeMeters}m
            </p>
          )}
          {item.weight !== undefined && item.weight !== null && (
            <p>
              <span className="text-slate-400">{t("inventory.weight")}</span>{" "}
              {item.weight}
            </p>
          )}
          {item.properties && item.properties.length > 0 && (
            <p>
              <span className="text-slate-400">{t("inventory.properties")}</span>{" "}
              {item.properties.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
