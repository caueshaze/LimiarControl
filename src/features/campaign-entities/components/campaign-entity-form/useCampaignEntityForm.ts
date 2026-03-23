import { type FormEvent, useEffect, useState } from "react";
import {
  ENTITY_ABILITIES,
  ENTITY_SKILLS,
  getCampaignEntityAbilityModifier,
  getCampaignEntitySkillBonus,
  type AbilityName,
  type CampaignEntityPayload,
  type SkillName,
} from "../../../../entities/campaign-entity";
import { useCampaigns } from "../../../campaign-select";
import { useLocale } from "../../../../shared/hooks/useLocale";
import {
  createInitialPayload,
  hasAdvancedData,
  isAbilityName,
  isSkillName,
} from "./constants";
import {
  createCombatActionAdder,
  createCombatActionFieldSetter,
  createCombatActionKindSetter,
  createCombatActionRemover,
  createSpellCatalogActionSelector,
  createWeaponCatalogActionSelector,
} from "./combatActionState";
import { buildCampaignEntitySubmitPayload } from "./submit";
import type { CampaignEntityFormProps, NewSaveKey, NewSkillKey } from "./types";
import { useCombatActionCatalog } from "./useCombatActionCatalog";

export const useCampaignEntityForm = ({ initial, onSave }: Pick<CampaignEntityFormProps, "initial" | "onSave">) => {
  const { t, locale } = useLocale();
  const { selectedCampaign, selectedCampaignId } = useCampaigns();
  const [form, setForm] = useState<CampaignEntityPayload>(createInitialPayload(initial));
  const [saving, setSaving] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(() => hasAdvancedData(initial));
  const [newSaveKey, setNewSaveKey] = useState<NewSaveKey>("");
  const [newSkillKey, setNewSkillKey] = useState<NewSkillKey>("");

  useEffect(() => {
    setForm(createInitialPayload(initial));
    setShowAdvanced(hasAdvancedData(initial));
  }, [initial]);
  const {
    catalogWeapons,
    catalogSpells,
    catalogLoading,
    catalogError,
    weaponLabel,
    spellLabel,
    weaponById,
    spellByKey,
  } = useCombatActionCatalog({
    locale,
    selectedCampaignId,
    systemType: selectedCampaign?.systemType,
    t,
  });

  const setField = <K extends keyof CampaignEntityPayload>(key: K, value: CampaignEntityPayload[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const setAbility = (key: AbilityName, value: string) => {
    const numeric = value === "" ? 10 : Number(value);
    setForm((prev) => ({
      ...prev,
      abilities: {
        ...prev.abilities,
        [key]: Number.isFinite(numeric) ? numeric : 10,
      },
    }));
  };

  const setSaveBonus = (key: AbilityName, value: string) => {
    setForm((prev) => {
      const next = { ...prev.savingThrows };
      if (value === "") {
        delete next[key];
      } else {
        next[key] = Number(value);
      }
      return { ...prev, savingThrows: next };
    });
  };

  const setSkillBonus = (key: SkillName, value: string) => {
    setForm((prev) => {
      const next = { ...prev.skills };
      if (value === "") {
        delete next[key];
      } else {
        next[key] = Number(value);
      }
      return { ...prev, skills: next };
    });
  };

  const removeSavingThrow = (key: AbilityName) => {
    setForm((prev) => {
      const next = { ...prev.savingThrows };
      delete next[key];
      return { ...prev, savingThrows: next };
    });
  };

  const removeSkill = (key: SkillName) => {
    setForm((prev) => {
      const next = { ...prev.skills };
      delete next[key];
      return { ...prev, skills: next };
    });
  };

  const toggleListValue = <T extends string>(
    field: "damageResistances" | "damageImmunities" | "damageVulnerabilities" | "conditionImmunities",
    value: T,
  ) => {
    setForm((prev) => {
      const current = prev[field] as T[];
      const next = current.includes(value)
        ? current.filter((entry) => entry !== value)
        : [...current, value];
      return { ...prev, [field]: next };
    });
  };

  const setSenseField = (
    key: "darkvisionMeters" | "blindsightMeters" | "tremorsenseMeters" | "truesightMeters" | "passivePerception",
    value: string,
  ) => {
    setForm((prev) => {
      const next = { ...(prev.senses ?? {}) };
      if (value === "") {
        delete next[key];
      } else {
        next[key] = Number(value);
      }
      return { ...prev, senses: Object.keys(next).length > 0 ? next : null };
    });
  };

  const setSpellcastingField = (key: "ability" | "saveDc" | "attackBonus", value: string) => {
    setForm((prev) => {
      const next = { ...(prev.spellcasting ?? {}) };
      if (value === "") {
        delete next[key];
      } else if (key === "ability" && isAbilityName(value)) {
        next[key] = value;
      } else if (key !== "ability") {
        next[key] = Number(value);
      }
      return { ...prev, spellcasting: Object.keys(next).length > 0 ? next : null };
    });
  };

  const setCombatAction = createCombatActionFieldSetter({ setForm });
  const setCombatActionKind = createCombatActionKindSetter({ setForm });
  const selectWeaponCatalogAction = createWeaponCatalogActionSelector({
    setForm,
    weaponById,
    weaponLabel,
  });
  const selectSpellCatalogAction = createSpellCatalogActionSelector({
    setForm,
    spellByKey,
    spellLabel,
  });
  const addCombatAction = createCombatActionAdder({ setForm });
  const removeCombatAction = createCombatActionRemover({ setForm });

  const selectedSavingThrows = ENTITY_ABILITIES.filter(
    (ability) => typeof form.savingThrows[ability.key] === "number",
  );
  const selectedSkills = ENTITY_SKILLS.filter(
    (skill) => typeof form.skills[skill.key] === "number",
  );
  const availableSaveAbilities = ENTITY_ABILITIES.filter(
    (ability) => typeof form.savingThrows[ability.key] !== "number",
  );
  const availableSkills = ENTITY_SKILLS.filter(
    (skill) => typeof form.skills[skill.key] !== "number",
  );
  const selectedNewSaveKey: NewSaveKey =
    isAbilityName(newSaveKey) && availableSaveAbilities.some((ability) => ability.key === newSaveKey)
      ? newSaveKey
      : (availableSaveAbilities[0]?.key ?? "");
  const selectedNewSkillKey: NewSkillKey =
    isSkillName(newSkillKey) && availableSkills.some((skill) => skill.key === newSkillKey)
      ? newSkillKey
      : (availableSkills[0]?.key ?? "");
  const derivedInitiativeBonus = getCampaignEntityAbilityModifier(form.abilities.dexterity);

  const addSavingThrow = () => {
    if (!selectedNewSaveKey) return;
    setForm((prev) => ({
      ...prev,
      savingThrows: {
        ...prev.savingThrows,
        [selectedNewSaveKey]: getCampaignEntityAbilityModifier(prev.abilities[selectedNewSaveKey]),
      },
    }));
    setNewSaveKey("");
  };

  const addSkill = () => {
    if (!selectedNewSkillKey) return;
    setForm((prev) => ({
      ...prev,
      skills: {
        ...prev.skills,
        [selectedNewSkillKey]: getCampaignEntitySkillBonus(
          { abilities: prev.abilities, skills: {} },
          selectedNewSkillKey,
        ),
      },
    }));
    setNewSkillKey("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await onSave(buildCampaignEntitySubmitPayload(form));
      if (!initial) {
        setForm(createInitialPayload(null));
      }
    } finally {
      setSaving(false);
    }
  };

  return {
    t,
    form,
    saving,
    showAdvanced,
    setShowAdvanced,
    newSaveKey,
    setNewSaveKey,
    newSkillKey,
    setNewSkillKey,
    catalogWeapons,
    catalogSpells,
    catalogLoading,
    catalogError,
    weaponById,
    spellByKey,
    weaponLabel,
    spellLabel,
    setField,
    setAbility,
    setSaveBonus,
    setSkillBonus,
    removeSavingThrow,
    removeSkill,
    toggleListValue,
    setSenseField,
    setSpellcastingField,
    setCombatAction,
    setCombatActionKind,
    selectWeaponCatalogAction,
    selectSpellCatalogAction,
    addCombatAction,
    removeCombatAction,
    selectedSavingThrows,
    selectedSkills,
    availableSaveAbilities,
    availableSkills,
    selectedNewSaveKey,
    selectedNewSkillKey,
    derivedInitiativeBonus,
    addSavingThrow,
    addSkill,
    handleSubmit,
  };
};
