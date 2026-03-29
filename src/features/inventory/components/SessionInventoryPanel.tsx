import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import type { CurrencyWallet } from "../../../shared/api/inventoryRepo";
import type { SessionUseConsumableResult } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { SessionInventoryModal } from "./SessionInventoryModal";
import {
  buildInventorySummary,
  buildWalletCoins,
  getInventoryItemName,
  type SessionInventorySelectOption,
} from "./sessionInventoryPanel.utils";

type SessionInventoryPanelProps = {
  activeSessionId?: string | null;
  combatActive?: boolean;
  flash?: boolean;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  wallet?: CurrencyWallet | null;
  open: boolean;
  selectedArmorId?: string | null;
  selectedWeaponId?: string | null;
  armorOptions?: SessionInventorySelectOption[];
  weaponOptions?: SessionInventorySelectOption[];
  isSavingLoadout?: boolean;
  loadoutStatus?: string | null;
  onArmorChange?: (inventoryItemId: string | null) => void;
  onConsumableUsed?: (result: SessionUseConsumableResult) => void | Promise<void>;
  onConsumableUseError?: (message: string) => void;
  onToggleOpen: () => void;
  onWeaponChange?: (inventoryItemId: string | null) => void;
};

export const SessionInventoryPanel = ({
  activeSessionId = null,
  combatActive = false,
  flash = false,
  inventory,
  itemsById,
  wallet = null,
  open,
  selectedArmorId = null,
  selectedWeaponId = null,
  armorOptions = [],
  weaponOptions = [],
  isSavingLoadout = false,
  loadoutStatus = null,
  onArmorChange,
  onConsumableUsed,
  onConsumableUseError,
  onToggleOpen,
  onWeaponChange,
}: SessionInventoryPanelProps) => {
  const { locale, t } = useLocale();
  const summary = buildInventorySummary(inventory, itemsById, locale);
  const walletCoins = buildWalletCoins(wallet);
  const selectedWeaponLabel = weaponOptions.find((option) => option.value === selectedWeaponId)?.label ?? null;
  const selectedArmorLabel = armorOptions.find((option) => option.value === selectedArmorId)?.label ?? null;

  return (
    <>
      <div
        className={`overflow-hidden rounded-[32px] border bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] shadow-[0_18px_60px_rgba(2,6,23,0.2)] transition-all ${
          flash
            ? "border-emerald-500/35 shadow-[0_0_40px_rgba(16,185,129,0.12)]"
            : "border-white/8"
        }`}
      >
        <div className="px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
                {t("playerBoard.inventoryStateLabel")}
              </p>
              <h2 className="mt-2 flex items-center gap-3 text-sm font-bold uppercase tracking-[0.24em] text-slate-100">
                <span className="h-4 w-1 rounded-full bg-amber-500" />
                {t("playerBoard.inventoryTitle")}
              </h2>
            </div>
            <button
              type="button"
              onClick={onToggleOpen}
              className="rounded-full border border-white/10 bg-white/4 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-100 transition hover:border-white/20 hover:bg-white/8"
            >
              {t("playerBoard.openInventoryModal")}
            </button>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {walletCoins.map((coin) => (
              <span
                key={coin.coin}
                className={coin.className}
                title={coin.longLabel}
              >
                {coin.amount} {coin.shortLabel}
              </span>
            ))}
          </div>

          <div className="mt-5 grid gap-4">
            <LoadoutSelect
              label={t("playerBoard.currentWeaponLabel")}
              value={selectedWeaponId ?? ""}
              options={weaponOptions}
              placeholder={t("playerBoard.currentWeaponPlaceholder")}
              disabled={isSavingLoadout || inventory === null}
              helper={selectedWeaponLabel ?? t("playerBoard.currentWeaponHint")}
              onChange={(value) => onWeaponChange?.(value || null)}
            />
            <LoadoutSelect
              label={t("playerBoard.currentArmorLabel")}
              value={selectedArmorId ?? ""}
              options={armorOptions}
              placeholder={t("playerBoard.currentArmorPlaceholder")}
              disabled={isSavingLoadout || inventory === null}
              helper={selectedArmorLabel ?? t("playerBoard.currentArmorHint")}
              onChange={(value) => onArmorChange?.(value || null)}
            />
          </div>

          {loadoutStatus && (
            <p className="mt-4 text-xs font-medium text-amber-200">
              {loadoutStatus}
            </p>
          )}

          <div className="mt-5 flex flex-wrap gap-2">
            {summary.previewItems.length > 0 ? (
              summary.previewItems.map((entry) => (
                <span
                  key={entry.entry.id}
                  className="rounded-full border border-white/8 bg-white/4 px-3 py-1 text-xs text-slate-300"
                >
                  {getInventoryItemName(entry.entry, entry.item, locale)} x{entry.entry.quantity}
                </span>
              ))
            ) : (
              <p className="text-sm text-slate-400">
                {inventory === null ? t("inventory.loading") : t("inventory.empty")}
              </p>
            )}
          </div>
        </div>
      </div>

      <SessionInventoryModal
        activeSessionId={activeSessionId}
        combatActive={combatActive}
        open={open}
        inventory={inventory}
        itemsById={itemsById}
        selectedArmorId={selectedArmorId}
        selectedWeaponId={selectedWeaponId}
        locale={locale}
        onConsumableUsed={onConsumableUsed}
        onConsumableUseError={onConsumableUseError}
        onClose={onToggleOpen}
      />
    </>
  );
};

const LoadoutSelect = ({
  disabled,
  helper,
  label,
  onChange,
  options,
  placeholder,
  value,
}: {
  disabled: boolean;
  helper: string;
  label: string;
  onChange: (value: string) => void;
  options: SessionInventorySelectOption[];
  placeholder: string;
  value: string;
}) => (
  <label className="block">
    <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</span>
    <select
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-amber-400/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
    >
      <option value="">{placeholder}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.detail ? `${option.label} · ${option.detail}` : option.label}
        </option>
      ))}
    </select>
    <span className="mt-2 block text-xs text-slate-400">{helper}</span>
  </label>
);
