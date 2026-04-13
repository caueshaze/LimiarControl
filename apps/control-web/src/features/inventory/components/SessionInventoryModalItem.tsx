import { useState } from "react";
import { getItemPropertyLabels } from "../../../entities/item";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import { formatDamageLabel } from "../../../shared/i18n/domainLabels";
import { getInventoryItemName } from "./sessionInventoryPanel.utils";

const DetailPill = ({ label, value }: { label: string; value: string }) => (
  <p className="rounded-xl bg-slate-950/50 px-3 py-2">
    <span className="text-slate-500">{label}</span> {value}
  </p>
);

const formatSpellKeyLabel = (value?: string | null) =>
  value
    ?.split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ") ?? null;

export const SessionInventoryModalItem = ({
  canUseHealingConsumable,
  entry,
  item,
  isCurrentArmor,
  isCurrentWeapon,
  locale,
  onUseHealingConsumable,
}: {
  canUseHealingConsumable: boolean;
  entry: InventoryItem;
  item?: Item;
  isCurrentArmor: boolean;
  isCurrentWeapon: boolean;
  locale: "en" | "pt" | string;
  onUseHealingConsumable?: () => void;
}) => {
  const { t } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const propertyLabels = getItemPropertyLabels(item?.properties, locale);
  const expiresAtDate =
    typeof entry.expiresAt === "string" && entry.expiresAt ? new Date(entry.expiresAt) : null;
  const expiresAtLabel =
    expiresAtDate && !Number.isNaN(expiresAtDate.getTime())
      ? new Intl.DateTimeFormat(locale === "pt" ? "pt-BR" : "en-US", {
          dateStyle: "short",
          timeStyle: "short",
        }).format(expiresAtDate)
      : null;
  const magicEffect = item?.magicEffect;
  const chargeCapacity = item?.chargesMax ?? null;
  const chargesCurrent = entry.chargesCurrent ?? chargeCapacity;
  const spellLabel = formatSpellKeyLabel(magicEffect?.spellCanonicalKey ?? null);
  const hasDetails = Boolean(
    item?.description ||
      item?.damageDice ||
      item?.healDice ||
      typeof item?.healBonus === "number" ||
      magicEffect ||
      typeof chargesCurrent === "number" ||
      item?.armorClassBase != null ||
      item?.rangeMeters != null ||
      item?.weight != null ||
      propertyLabels.length > 0 ||
      entry.notes,
  );

  return (
    <div className="overflow-hidden rounded-3xl border border-white/8 bg-white/4">
      <div className="flex items-start justify-between gap-4 px-4 py-3">
        <button
          type="button"
          disabled={!hasDetails}
          onClick={() => hasDetails && setExpanded((current) => !current)}
          className={`min-w-0 flex-1 text-left ${hasDetails ? "transition hover:text-white" : "cursor-default"}`}
        >
          <p className="text-sm font-semibold text-white">
            {getInventoryItemName(entry, item, locale)}
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
            {expiresAtLabel && (
              <span className="rounded-full border border-violet-500/25 bg-violet-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-200">
                {t("inventory.temporary")}
              </span>
            )}
            {typeof chargesCurrent === "number" && typeof chargeCapacity === "number" ? (
              <span className="rounded-full border border-fuchsia-500/25 bg-fuchsia-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-fuchsia-200">
                {chargesCurrent}/{chargeCapacity}
              </span>
            ) : null}
          </div>
        </button>
        <div className="flex shrink-0 items-start gap-2">
          {canUseHealingConsumable && onUseHealingConsumable ? (
            <button
              type="button"
              onClick={onUseHealingConsumable}
              className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-200 transition hover:bg-emerald-500/20"
            >
              {t("inventory.useConsumable")}
            </button>
          ) : null}
          {hasDetails ? (
            <button
              type="button"
              onClick={() => setExpanded((current) => !current)}
              className="rounded-full border border-white/8 px-2.5 py-1 text-slate-500 transition hover:border-white/16 hover:text-white"
              aria-expanded={expanded}
              aria-label={expanded ? t("inventory.hideDetails") : t("inventory.showDetails")}
            >
              <span className={`block transition-transform ${expanded ? "rotate-180" : ""}`}>▼</span>
            </button>
          ) : null}
        </div>
      </div>
      {expanded && hasDetails && (
        <div className="space-y-3 border-t border-white/8 px-4 py-4 text-xs text-slate-300">
          {item?.description && <p className="text-sm leading-6 text-slate-400">{item.description}</p>}
          <div className="grid gap-2 sm:grid-cols-2">
            {item?.damageDice && (
              <DetailPill
                label={t("inventory.damage")}
                value={formatDamageLabel(item.damageDice, item.damageType, locale) ?? item.damageDice}
              />
            )}
            {(item?.healDice || typeof item?.healBonus === "number") && (
              <DetailPill
                label={t("inventory.healing")}
                value={
                  item.healDice
                    ? `${item.healDice}${typeof item.healBonus === "number" && item.healBonus !== 0 ? ` + ${item.healBonus}` : ""}`
                    : `${item.healBonus ?? 0}`
                }
              />
            )}
            {typeof chargesCurrent === "number" && typeof chargeCapacity === "number" ? (
              <DetailPill
                label={t("inventory.charges")}
                value={`${chargesCurrent}/${chargeCapacity}`}
              />
            ) : null}
            {magicEffect ? (
              <DetailPill
                label={t("inventory.magicEffect")}
                value={
                  spellLabel
                    ? `${spellLabel} (${t("inventory.castSpellLevel")} ${magicEffect.castLevel})`
                    : `${t("inventory.castSpellLevel")} ${magicEffect.castLevel}`
                }
              />
            ) : null}
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
            {magicEffect?.ignoreComponents ? (
              <DetailPill label={t("inventory.properties")} value={t("inventory.ignoreComponents")} />
            ) : null}
            {magicEffect?.noFreeHandRequired ? (
              <DetailPill label={t("inventory.properties")} value={t("inventory.noFreeHandRequired")} />
            ) : null}
            {typeof chargeCapacity === "number" && chargeCapacity === 1 ? (
              <DetailPill label={t("inventory.properties")} value={t("inventory.singleUse")} />
            ) : null}
            {item?.rechargeType === "none" ? (
              <DetailPill label={t("inventory.properties")} value={t("inventory.noRecharge")} />
            ) : null}
            {entry.notes && (
              <DetailPill label={t("inventory.notes")} value={entry.notes} />
            )}
            {expiresAtLabel && (
              <DetailPill label={t("inventory.expiresAt")} value={expiresAtLabel} />
            )}
          </div>
        </div>
      )}
    </div>
  );
};
