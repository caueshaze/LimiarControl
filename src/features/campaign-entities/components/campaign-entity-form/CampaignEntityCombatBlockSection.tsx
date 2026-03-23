import {
  ENTITY_ABILITIES,
  getCampaignEntityAbilityModifier,
  type AbilityName,
  type CampaignEntityPayload,
  withSignedBonus,
} from "../../../../entities/campaign-entity";
import { fieldClass, sectionClass } from "./constants";
import type { SetCampaignEntityField, Translate } from "./types";

type Props = {
  form: CampaignEntityPayload;
  derivedInitiativeBonus: number;
  setField: SetCampaignEntityField;
  setAbility: (key: AbilityName, value: string) => void;
  t: Translate;
};

export const CampaignEntityCombatBlockSection = ({
  form,
  derivedInitiativeBonus,
  setField,
  setAbility,
  t,
}: Props) => (
  <div className={sectionClass}>
    <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
      {t("entity.form.combatBlockSection")}
    </p>

    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <input
        type="number"
        min={0}
        value={form.armorClass ?? ""}
        onChange={(event) =>
          setField("armorClass", event.target.value === "" ? null : Number(event.target.value))
        }
        placeholder={t("entity.form.ac")}
        className={fieldClass}
      />
      <input
        type="number"
        min={0}
        value={form.maxHp ?? ""}
        onChange={(event) =>
          setField("maxHp", event.target.value === "" ? null : Number(event.target.value))
        }
        placeholder={t("entity.form.hp")}
        className={fieldClass}
      />
      <input
        type="number"
        min={0}
        value={form.speedMeters ?? ""}
        onChange={(event) =>
          setField("speedMeters", event.target.value === "" ? null : Number(event.target.value))
        }
        placeholder={t("entity.form.speedMeters")}
        className={fieldClass}
      />
      <input
        type="number"
        value={form.initiativeBonus ?? ""}
        onChange={(event) =>
          setField("initiativeBonus", event.target.value === "" ? null : Number(event.target.value))
        }
        placeholder={t("entity.form.initiativeBonus")}
        className={fieldClass}
      />
    </div>

    <div className="mt-4">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        {t("entity.form.abilities")}
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {ENTITY_ABILITIES.map((ability) => (
          <div
            key={ability.key}
            className="rounded-2xl border border-white/8 bg-white/3 p-3"
          >
            <label className="mb-1 block text-center text-[10px] font-bold uppercase tracking-widest text-slate-500">
              {ability.short}
            </label>
            <input
              type="number"
              min={1}
              max={30}
              value={form.abilities[ability.key]}
              onChange={(event) => setAbility(ability.key, event.target.value)}
              className={`${fieldClass} text-center`}
            />
            <p className="mt-2 text-center text-[11px] font-semibold text-emerald-200">
              {withSignedBonus(getCampaignEntityAbilityModifier(form.abilities[ability.key]))}
            </p>
          </div>
        ))}
      </div>
    </div>

    <p className="mt-3 text-xs text-slate-500">
      {t("entity.form.initiativeHint")}{" "}
      <span className="font-semibold text-emerald-200">
        {withSignedBonus(derivedInitiativeBonus) ?? "+0"}
      </span>
    </p>
  </div>
);
