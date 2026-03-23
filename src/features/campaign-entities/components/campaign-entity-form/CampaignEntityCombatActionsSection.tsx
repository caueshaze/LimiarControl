import { type BaseSpell } from "../../../../entities/base-spell";
import { type Item } from "../../../../entities/item";
import { type CampaignEntityPayload, type CombatAction, type CombatActionKind } from "../../../../entities/campaign-entity";
import { sectionClass } from "./constants";
import { CampaignEntityCombatActionCard } from "./CampaignEntityCombatActionCard";
import type {
  SetCombatActionField,
  SpellLabelFn,
  Translate,
  WeaponLabelFn,
} from "./types";

type Props = {
  form: CampaignEntityPayload;
  catalogWeapons: Item[];
  catalogSpells: BaseSpell[];
  catalogLoading: boolean;
  catalogError: string | null;
  weaponById: Map<string, Item>;
  spellByKey: Map<string, BaseSpell>;
  addCombatAction: () => void;
  removeCombatAction: (index: number) => void;
  setCombatAction: SetCombatActionField;
  setCombatActionKind: (index: number, kind: CombatActionKind) => void;
  selectWeaponCatalogAction: (index: number, campaignItemId: string) => void;
  selectSpellCatalogAction: (index: number, canonicalKey: string) => void;
  t: Translate;
  weaponLabel: WeaponLabelFn;
  spellLabel: SpellLabelFn;
};

export const CampaignEntityCombatActionsSection = ({
  form,
  catalogWeapons,
  catalogSpells,
  catalogLoading,
  catalogError,
  weaponById,
  spellByKey,
  addCombatAction,
  removeCombatAction,
  setCombatAction,
  setCombatActionKind,
  selectWeaponCatalogAction,
  selectSpellCatalogAction,
  t,
  weaponLabel,
  spellLabel,
}: Props) => (
  <div className={sectionClass}>
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.combatActions")}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          {t("entity.form.combatActionsDescription")}
        </p>
      </div>
      <button
        type="button"
        onClick={addCombatAction}
        className="rounded-full border border-slate-700 px-3 py-1 text-[11px] font-semibold uppercase tracking-widest text-slate-200 hover:bg-slate-800"
      >
        {t("entity.form.addCombatAction")}
      </button>
    </div>

    {form.combatActions.length === 0 ? (
      <p className="mt-3 text-xs text-slate-500">{t("entity.form.combatActionsEmpty")}</p>
    ) : (
      <div className="mt-4 space-y-4">
        {catalogLoading && (
          <p className="text-xs text-slate-500">{t("entity.form.catalogLoading")}</p>
        )}
        {catalogError && <p className="text-xs text-amber-200">{catalogError}</p>}
        {form.combatActions.map((action, index) => (
          <CampaignEntityCombatActionCard
            key={action.id}
            action={action}
            index={index}
            abilities={form.abilities}
            catalogWeapons={catalogWeapons}
            catalogSpells={catalogSpells}
            weaponById={weaponById}
            spellByKey={spellByKey}
            setCombatAction={setCombatAction}
            setCombatActionKind={setCombatActionKind}
            selectWeaponCatalogAction={selectWeaponCatalogAction}
            selectSpellCatalogAction={selectSpellCatalogAction}
            removeCombatAction={removeCombatAction}
            t={t}
            weaponLabel={weaponLabel}
            spellLabel={spellLabel}
          />
        ))}
      </div>
    )}
  </div>
);
