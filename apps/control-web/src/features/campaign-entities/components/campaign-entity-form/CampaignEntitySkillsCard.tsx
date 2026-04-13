import {
  ENTITY_SKILLS,
  getCampaignEntityAbilityModifier,
  withSignedBonus,
  type CampaignEntityPayload,
  type SkillName,
} from "../../../../entities/campaign-entity";
import { fieldClass, rowDisplayClass } from "./constants";
import type { NewSkillKey, Translate } from "./types";

type Props = {
  form: CampaignEntityPayload;
  availableSkills: typeof ENTITY_SKILLS;
  selectedSkills: typeof ENTITY_SKILLS;
  selectedNewSkillKey: NewSkillKey;
  setNewSkillKey: (value: NewSkillKey) => void;
  addSkill: () => void;
  setSkillBonus: (key: SkillName, value: string) => void;
  removeSkill: (key: SkillName) => void;
  t: Translate;
};

export const CampaignEntitySkillsCard = ({
  form,
  availableSkills,
  selectedSkills,
  selectedNewSkillKey,
  setNewSkillKey,
  addSkill,
  setSkillBonus,
  removeSkill,
  t,
}: Props) => (
  <div className="rounded-3xl border border-white/8 bg-white/3 p-4">
    <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
      {t("entity.form.specialSkills")}
    </p>
    <p className="mt-1 text-xs text-slate-500">
      {t("entity.form.specialSkillsDescription")}
    </p>

    <div className="mt-4">
      {availableSkills.length > 0 ? (
        <div className="grid gap-2 sm:grid-cols-[minmax(0,240px)_auto] sm:items-center">
          <select
            value={selectedNewSkillKey}
            onChange={(event) => setNewSkillKey(event.target.value as NewSkillKey)}
            className={`${fieldClass} min-w-0`}
          >
            {availableSkills.map((skill) => (
              <option key={skill.key} value={skill.key}>
                {skill.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={addSkill}
            className="rounded-full border border-white/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-200 transition hover:border-white/20 hover:bg-white/5 sm:justify-self-start"
          >
            {t("entity.form.addSkill")}
          </button>
        </div>
      ) : (
        <p className="text-xs text-slate-500">{t("entity.form.noSkillsLeft")}</p>
      )}
    </div>

    {selectedSkills.length === 0 ? (
      <p className="mt-4 text-sm text-slate-500">{t("entity.form.noSkills")}</p>
    ) : (
      <div className="mt-4 space-y-3">
        {selectedSkills.map((skill) => (
          <div key={skill.key} className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_160px_auto]">
            <div className={rowDisplayClass}>
              <div className="font-medium text-slate-100">{skill.label}</div>
              <div className="mt-1 text-xs text-slate-500">
                {skill.ability.toUpperCase()} · {t("entity.form.baseLabel")}{" "}
                {withSignedBonus(getCampaignEntityAbilityModifier(form.abilities[skill.ability]))}
              </div>
            </div>
            <input
              type="number"
              value={form.skills[skill.key] ?? ""}
              onChange={(event) => setSkillBonus(skill.key, event.target.value)}
              placeholder={skill.label}
              className={fieldClass}
            />
            <button
              type="button"
              onClick={() => removeSkill(skill.key)}
              className="rounded-full border border-red-500/30 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-red-300 transition hover:bg-red-500/10"
            >
              {t("entity.form.removeOptional")}
            </button>
          </div>
        ))}
      </div>
    )}
  </div>
);
