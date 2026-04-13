import { type BaseSpell } from "../../../../entities/base-spell";
import { type Item } from "../../../../entities/item";
import {
  type CombatAction,
  type CombatActionKind,
} from "../../../../entities/campaign-entity";
import { ACTION_KINDS, fieldClass } from "./constants";
import { CampaignEntitySpellActionFields } from "./CampaignEntitySpellActionFields";
import { CampaignEntityWeaponActionFields } from "./CampaignEntityWeaponActionFields";
import type {
  SetCombatActionField,
  SpellLabelFn,
  Translate,
  WeaponLabelFn,
} from "./types";

type Props = {
  action: CombatAction;
  index: number;
  catalogWeapons: Item[];
  catalogSpells: BaseSpell[];
  weaponById: Map<string, Item>;
  spellByKey: Map<string, BaseSpell>;
  setCombatAction: SetCombatActionField;
  setCombatActionKind: (index: number, kind: CombatActionKind) => void;
  selectWeaponCatalogAction: (index: number, campaignItemId: string) => void;
  selectSpellCatalogAction: (index: number, canonicalKey: string) => void;
  removeCombatAction: (index: number) => void;
  t: Translate;
  weaponLabel: WeaponLabelFn;
  spellLabel: SpellLabelFn;
};

export const CampaignEntityCombatActionCard = ({
  action,
  index,
  catalogWeapons,
  catalogSpells,
  weaponById,
  spellByKey,
  setCombatAction,
  setCombatActionKind,
  selectWeaponCatalogAction,
  selectSpellCatalogAction,
  removeCombatAction,
  t,
  weaponLabel,
  spellLabel,
}: Props) => {
  const isWeaponAction = action.kind === "weapon_attack";
  const isSpellLikeAction =
    action.kind === "spell_attack" || action.kind === "saving_throw" || action.kind === "heal";
  const isHealAction = action.kind === "heal";
  const isUtilityAction = action.kind === "utility";

  return (
    <div className="rounded-3xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.74),rgba(2,6,23,0.92))] p-4">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex-1 space-y-3">
          <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_240px]">
            <input
              value={action.name}
              onChange={(event) => setCombatAction(index, "name", event.target.value)}
              placeholder={t("entity.form.combatActionName")}
              className={fieldClass}
            />
            <select
              value={action.kind}
              onChange={(event) => setCombatActionKind(index, event.target.value as CombatActionKind)}
              className={fieldClass}
            >
              {ACTION_KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {t(`entity.form.combatActionKind.${kind}`)}
                </option>
              ))}
            </select>
          </div>

          {isUtilityAction ? (
            <div className="space-y-3">
              <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-xs text-amber-100">
                {t("entity.form.manualOnlyAction")}
              </div>
              <input
                value={action.description ?? ""}
                onChange={(event) => setCombatAction(index, "description", event.target.value)}
                placeholder={t("entity.form.combatActionDescription")}
                className={fieldClass}
              />
            </div>
          ) : (
            <div className="space-y-4">
              {isWeaponAction && (
                <CampaignEntityWeaponActionFields
                  action={action}
                  index={index}
                  catalogWeapons={catalogWeapons}
                  weaponById={weaponById}
                  setCombatAction={setCombatAction}
                  selectWeaponCatalogAction={selectWeaponCatalogAction}
                  t={t}
                  weaponLabel={weaponLabel}
                />
              )}

              {isSpellLikeAction && (
                <CampaignEntitySpellActionFields
                  action={action}
                  index={index}
                  catalogSpells={catalogSpells}
                  spellByKey={spellByKey}
                  setCombatAction={setCombatAction}
                  selectSpellCatalogAction={selectSpellCatalogAction}
                  t={t}
                  spellLabel={spellLabel}
                />
              )}

              {!isHealAction && (
                <input
                  value={action.description ?? ""}
                  onChange={(event) => setCombatAction(index, "description", event.target.value)}
                  placeholder={t("entity.form.combatActionDescription")}
                  className={fieldClass}
                />
              )}
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => removeCombatAction(index)}
          className="self-start rounded-full border border-red-500/30 px-4 py-2 text-[11px] font-semibold uppercase tracking-widest text-red-300 hover:bg-red-500/10"
        >
          {t("entity.form.removeCombatAction")}
        </button>
      </div>
    </div>
  );
};
