import type { useLocale } from "../../../../shared/hooks/useLocale";
import type { BaseSpell } from "../../../../entities/base-spell";
import type { Item } from "../../../../entities/item";
import type {
  AbilityName,
  CampaignEntity,
  CampaignEntityPayload,
  CombatAction,
  EntityCategory,
  SkillName,
} from "../../../../entities/campaign-entity";

export type CampaignEntityFormProps = {
  onSave: (payload: CampaignEntityPayload) => Promise<void> | void;
  initial?: CampaignEntity | null;
  onCancel?: () => void;
};

export type Translate = ReturnType<typeof useLocale>["t"];

export type SetCampaignEntityField = <K extends keyof CampaignEntityPayload>(
  key: K,
  value: CampaignEntityPayload[K],
) => void;

export type SetCombatActionField = <K extends keyof CombatAction>(
  index: number,
  key: K,
  value: CombatAction[K],
) => void;

export type WeaponLabelFn = (weapon: Item) => string;
export type SpellLabelFn = (spell: BaseSpell) => string;

export type NewSaveKey = AbilityName | "";
export type NewSkillKey = SkillName | "";

export type CategoryOption = EntityCategory;
