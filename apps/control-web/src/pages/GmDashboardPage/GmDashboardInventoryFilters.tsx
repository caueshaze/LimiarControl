import type { SessionInventoryFilterGroup } from "../../features/inventory/components/sessionInventoryPanel.utils";

type Props = {
  userId: string;
  searchValue: string;
  equippedOnly: boolean;
  activeGroup: SessionInventoryFilterGroup;
  onSearchChange: (value: string) => void;
  onToggleEquippedOnly: () => void;
  onGroupChange: (group: SessionInventoryFilterGroup) => void;
};

export const GmDashboardInventoryFilters = ({
  searchValue,
  equippedOnly,
  activeGroup,
  onSearchChange,
  onToggleEquippedOnly,
  onGroupChange,
}: Props) => {
  return (
    <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
      <div className="flex flex-col gap-3 lg:flex-row">
        <input
          type="text"
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search inventory"
          className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:border-limiar-500 focus:outline-none"
        />
        <button
          type="button"
          onClick={onToggleEquippedOnly}
          className={`rounded-xl border px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] ${
            equippedOnly
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-slate-700 bg-slate-900 text-slate-300"
          }`}
        >
          Equipped only
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {(["all", "weapon", "armor", "magic", "consumable", "misc"] as const).map((entryGroup) => (
          <button
            key={entryGroup}
            type="button"
            onClick={() => onGroupChange(entryGroup)}
            className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
              activeGroup === entryGroup
                ? "border-limiar-500/30 bg-limiar-500/10 text-limiar-200"
                : "border-slate-700 bg-slate-900 text-slate-400"
            }`}
          >
            {entryGroup === "all"
              ? "All"
              : entryGroup === "weapon"
                ? "Weapon"
                : entryGroup === "armor"
                  ? "Armor"
                  : entryGroup === "magic"
                    ? "Magic"
                    : entryGroup === "consumable"
                      ? "Consumable"
                      : "Misc"}
          </button>
        ))}
      </div>
    </div>
  );
};
