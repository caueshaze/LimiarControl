import { CampaignEntityAdvancedSection } from "./campaign-entity-form/CampaignEntityAdvancedSection";
import { CampaignEntityCombatActionsSection } from "./campaign-entity-form/CampaignEntityCombatActionsSection";
import { CampaignEntityCombatBlockSection } from "./campaign-entity-form/CampaignEntityCombatBlockSection";
import { CampaignEntityGeneralSection } from "./campaign-entity-form/CampaignEntityGeneralSection";
import { CampaignEntityNotesSection } from "./campaign-entity-form/CampaignEntityNotesSection";
import { useCampaignEntityForm } from "./campaign-entity-form/useCampaignEntityForm";
import type { CampaignEntityFormProps } from "./campaign-entity-form/types";

export const CampaignEntityForm = ({ onSave, initial, onCancel }: CampaignEntityFormProps) => {
  const state = useCampaignEntityForm({ initial, onSave });

  return (
    <form
      onSubmit={state.handleSubmit}
      className="space-y-4 rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(10,14,31,0.9),rgba(2,6,23,0.97))] p-4 sm:p-5 lg:p-6 shadow-[0_24px_80px_rgba(2,6,23,0.22)]"
    >
      <CampaignEntityGeneralSection
        form={state.form}
        hasInitialValue={Boolean(initial)}
        setField={state.setField}
        t={state.t}
      />

      <CampaignEntityCombatBlockSection
        form={state.form}
        derivedInitiativeBonus={state.derivedInitiativeBonus}
        setField={state.setField}
        setAbility={state.setAbility}
        t={state.t}
      />

      <CampaignEntityCombatActionsSection
        form={state.form}
        catalogWeapons={state.catalogWeapons}
        catalogSpells={state.catalogSpells}
        catalogLoading={state.catalogLoading}
        catalogError={state.catalogError}
        weaponById={state.weaponById}
        spellByKey={state.spellByKey}
        addCombatAction={state.addCombatAction}
        removeCombatAction={state.removeCombatAction}
        setCombatAction={state.setCombatAction}
        setCombatActionKind={state.setCombatActionKind}
        selectWeaponCatalogAction={state.selectWeaponCatalogAction}
        selectSpellCatalogAction={state.selectSpellCatalogAction}
        t={state.t}
        weaponLabel={state.weaponLabel}
        spellLabel={state.spellLabel}
      />

      <CampaignEntityAdvancedSection
        form={state.form}
        showAdvanced={state.showAdvanced}
        setShowAdvanced={state.setShowAdvanced}
        setField={state.setField}
        selectedSavingThrows={state.selectedSavingThrows}
        selectedSkills={state.selectedSkills}
        availableSaveAbilities={state.availableSaveAbilities}
        availableSkills={state.availableSkills}
        selectedNewSaveKey={state.selectedNewSaveKey}
        selectedNewSkillKey={state.selectedNewSkillKey}
        setNewSaveKey={state.setNewSaveKey}
        setNewSkillKey={state.setNewSkillKey}
        addSavingThrow={state.addSavingThrow}
        addSkill={state.addSkill}
        setSaveBonus={state.setSaveBonus}
        setSkillBonus={state.setSkillBonus}
        removeSavingThrow={state.removeSavingThrow}
        removeSkill={state.removeSkill}
        setSenseField={state.setSenseField}
        setSpellcastingField={state.setSpellcastingField}
        toggleListValue={state.toggleListValue}
        t={state.t}
      />

      <CampaignEntityNotesSection
        form={state.form}
        setField={state.setField}
        t={state.t}
      />

      <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row">
        <button
          type="submit"
          disabled={state.saving || !state.form.name.trim()}
          className="flex-1 rounded-full bg-emerald-200 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-950 transition hover:bg-emerald-100 disabled:opacity-50"
        >
          {state.saving ? state.t("entity.form.saving") : state.t("entity.form.save")}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-300 transition hover:border-white/20 hover:text-white"
          >
            {state.t("entity.form.cancel")}
          </button>
        )}
      </div>
    </form>
  );
};
