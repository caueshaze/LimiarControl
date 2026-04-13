import { type Item } from "../../../../entities/item";
import {
  ENTITY_DAMAGE_TYPES,
  type CombatAction,
  type DamageType,
} from "../../../../entities/campaign-entity";
import { fieldClass, isDamageType, rowDisplayClass } from "./constants";
import { DiceExpressionSelect } from "./DiceExpressionSelect";
import type { SetCombatActionField, Translate, WeaponLabelFn } from "./types";

type Props = {
  action: CombatAction;
  index: number;
  catalogWeapons: Item[];
  weaponById: Map<string, Item>;
  setCombatAction: SetCombatActionField;
  selectWeaponCatalogAction: (index: number, campaignItemId: string) => void;
  t: Translate;
  weaponLabel: WeaponLabelFn;
};

export const CampaignEntityWeaponActionFields = ({
  action,
  index,
  catalogWeapons,
  weaponById,
  setCombatAction,
  selectWeaponCatalogAction,
  t,
  weaponLabel,
}: Props) => {
  const selectedWeapon = action.campaignItemId ? (weaponById.get(action.campaignItemId) ?? null) : null;
  const derivedWeaponDamageType = isDamageType(selectedWeapon?.damageType?.toLowerCase())
    ? (selectedWeapon?.damageType?.toLowerCase() as DamageType)
    : null;

  return (
    <>
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1.35fr)_180px_180px]">
        <select
          value={action.campaignItemId ?? ""}
          onChange={(event) => selectWeaponCatalogAction(index, event.target.value)}
          className={fieldClass}
        >
          <option value="">{t("entity.form.noCatalogWeapon")}</option>
          {catalogWeapons.map((weapon) => (
            <option key={weapon.id} value={weapon.id}>
              {weaponLabel(weapon)}
            </option>
          ))}
        </select>
        <input
          type="number"
          value={action.toHitBonus ?? ""}
          onChange={(event) =>
            setCombatAction(index, "toHitBonus", event.target.value === "" ? null : Number(event.target.value))
          }
          placeholder={t("entity.form.toHitBonus")}
          className={fieldClass}
        />
        <input
          type="number"
          value={action.damageBonus ?? ""}
          onChange={(event) =>
            setCombatAction(index, "damageBonus", event.target.value === "" ? null : Number(event.target.value))
          }
          placeholder={t("entity.form.damageBonus")}
          className={fieldClass}
        />
      </div>

      <div className="rounded-2xl border border-white/8 bg-white/3 px-4 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {selectedWeapon ? t("entity.form.catalogDerivedProfile") : t("entity.form.manualProfile")}
        </p>
        {selectedWeapon ? (
          <>
            <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-300">
              <span className="rounded-full border border-emerald-300/20 bg-emerald-400/10 px-3 py-1 text-emerald-100">
                {t("entity.form.usesCatalogWeapon")}: {weaponLabel(selectedWeapon)}
              </span>
              {selectedWeapon.damageDice && <span>{selectedWeapon.damageDice}</span>}
              {derivedWeaponDamageType && (
                <span>
                  {ENTITY_DAMAGE_TYPES.find((entry) => entry.key === derivedWeaponDamageType)?.label ??
                    derivedWeaponDamageType}
                </span>
              )}
              {selectedWeapon.rangeMeters != null && <span>{selectedWeapon.rangeMeters}m</span>}
              {selectedWeapon.weaponRangeType && (
                <span>
                  {selectedWeapon.weaponRangeType === "melee"
                    ? t("entity.form.rangeModeMelee")
                    : t("entity.form.rangeModeRanged")}
                </span>
              )}
            </div>
          </>
        ) : (
          <p className="mt-2 text-xs text-slate-400">{t("entity.form.actionOverrides")}</p>
        )}
      </div>

      {selectedWeapon ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className={rowDisplayClass}>{action.damageDice || t("entity.form.damageDice")}</div>
          <div className={rowDisplayClass}>
            {action.damageType
              ? (ENTITY_DAMAGE_TYPES.find((type) => type.key === action.damageType)?.label ?? action.damageType)
              : t("entity.form.damageType")}
          </div>
          <div className={rowDisplayClass}>
            {action.rangeMeters != null ? `${action.rangeMeters}m` : t("entity.form.rangeMeters")}
          </div>
          <div className={rowDisplayClass}>
            {action.isMelee == null
              ? t("entity.form.rangeMode")
              : action.isMelee
                ? t("entity.form.rangeModeMelee")
                : t("entity.form.rangeModeRanged")}
          </div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <DiceExpressionSelect
            value={action.damageDice}
            onChange={(value) => setCombatAction(index, "damageDice", value)}
            countPlaceholder="Qtd"
            sidesPlaceholder={t("entity.form.damageDice")}
          />
          <select
            value={action.damageType ?? ""}
            onChange={(event) =>
              setCombatAction(
                index,
                "damageType",
                event.target.value === "" ? null : (event.target.value as DamageType),
              )
            }
            className={fieldClass}
          >
            <option value="">{t("entity.form.damageType")}</option>
            {ENTITY_DAMAGE_TYPES.map((type) => (
              <option key={type.key} value={type.key}>
                {type.label}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={0}
            value={action.rangeMeters ?? ""}
            onChange={(event) =>
              setCombatAction(index, "rangeMeters", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.rangeMeters")}
            className={fieldClass}
          />
          <select
            value={action.isMelee == null ? "" : action.isMelee ? "melee" : "ranged"}
            onChange={(event) =>
              setCombatAction(index, "isMelee", event.target.value === "" ? null : event.target.value === "melee")
            }
            className={fieldClass}
          >
            <option value="">{t("entity.form.rangeMode")}</option>
            <option value="melee">{t("entity.form.rangeModeMelee")}</option>
            <option value="ranged">{t("entity.form.rangeModeRanged")}</option>
          </select>
        </div>
      )}
    </>
  );
};
