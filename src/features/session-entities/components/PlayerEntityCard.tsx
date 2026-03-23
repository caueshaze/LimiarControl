import type { ReactNode } from "react";
import {
  ENTITY_ABILITIES,
  ENTITY_CONDITIONS,
  ENTITY_DAMAGE_TYPES,
  getCampaignEntityAbilityModifier,
  getCampaignEntityExplicitSkillEntries,
  getCampaignEntityInitiativeBonus,
  getCampaignEntitySavingThrowEntries,
  withSignedBonus,
  type EntityCategory,
} from "../../../entities/campaign-entity";
import type { SessionEntityPlayer } from "../../../entities/session-entity";
import { describeCombatAction } from "../../../entities/campaign-entity/describeCombatAction";
import { CategoryBadge } from "../../campaign-entities";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  entity: SessionEntityPlayer;
};

const StatPill = ({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "override";
}) => (
  <span
    className={`rounded-lg px-2 py-0.5 text-[10px] font-bold uppercase ${
      tone === "override"
        ? "border border-emerald-500/30 bg-emerald-500/12 text-emerald-200"
        : "bg-slate-800 text-slate-300"
    }`}
  >
    {children}
  </span>
);

export const PlayerEntityCard = ({ entity }: Props) => {
  const { t } = useLocale();
  const ce = entity.entity;
  if (!ce) return null;

  const displayName = entity.label ? `${ce.name} (${entity.label})` : ce.name;
  const category = (ce.category ?? "npc") as EntityCategory;
  const isDead = typeof entity.currentHp === "number" && entity.currentHp <= 0;
  const initiativeBonus = getCampaignEntityInitiativeBonus(ce);
  const saveEntries = getCampaignEntitySavingThrowEntries(ce);
  const skillEntries = getCampaignEntityExplicitSkillEntries(ce);
  const damageTypeLabels = new Map(ENTITY_DAMAGE_TYPES.map((entry) => [entry.key, entry.label]));
  const conditionLabels = new Map(ENTITY_CONDITIONS.map((entry) => [entry.key, entry.label]));

  return (
    <div className="rounded-[24px] border border-white/8 bg-white/[0.04] p-4 text-sm text-slate-200">
      <div className="flex items-center gap-2">
        <p className="text-base font-semibold text-white">{displayName}</p>
        <CategoryBadge category={category} />
        {isDead && (
          <span className="rounded-full border border-red-500/30 bg-red-500/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.18em] text-red-200">
            {t("entity.dead")}
          </span>
        )}
      </div>

      <div className="mt-1 flex flex-wrap gap-3 text-xs">
        {entity.currentHp != null && (
          <span className="rounded-lg border border-red-500/20 bg-red-500/10 px-2 py-0.5 font-bold text-red-300">
            HP {ce.maxHp != null ? `${entity.currentHp}/${ce.maxHp}` : entity.currentHp}
          </span>
        )}
        {ce.armorClass != null && (
          <span className="rounded-lg border border-sky-500/20 bg-sky-500/10 px-2 py-0.5 font-bold text-sky-300">
            AC {ce.armorClass}
          </span>
        )}
        {ce.speedMeters != null && (
          <span className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 font-bold text-emerald-300">
            {ce.speedMeters}m
          </span>
        )}
        <span className="rounded-lg border border-white/10 bg-white/[0.04] px-2 py-0.5 font-bold text-slate-300">
          {t("entity.card.initiativeShort")} {withSignedBonus(initiativeBonus)}
        </span>
      </div>

      {ce.description && (
        <p className="mt-2 text-xs text-slate-400">{ce.description}</p>
      )}

      <div className="mt-2 flex flex-wrap gap-1.5">
        {ENTITY_ABILITIES.map((ability) => (
          <StatPill key={ability.key}>
            {ability.short} {ce.abilities[ability.key]} ({withSignedBonus(getCampaignEntityAbilityModifier(ce.abilities[ability.key]))})
          </StatPill>
        ))}
      </div>

      <div className="mt-2 text-xs text-slate-300">
        <span className="text-slate-500">{t("entity.form.savingThrows")}: </span>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {saveEntries.map((ability) => (
            <StatPill key={ability.key} tone={ability.isOverride ? "override" : "default"}>
              {ability.short} {withSignedBonus(ability.bonus)}
            </StatPill>
          ))}
        </div>
      </div>

      {skillEntries.length > 0 && (
        <div className="mt-2 text-xs text-slate-300">
          <span className="text-slate-500">{t("entity.form.skills")}: </span>
          {skillEntries
            .map((skill) => `${skill.label} ${withSignedBonus(skill.bonus)}`)
            .join(", ")}
        </div>
      )}

      {ce.senses && (
        <div className="mt-2 text-xs text-slate-300">
          <span className="text-slate-500">{t("entity.form.senses")}: </span>
          {[
            ce.senses.darkvisionMeters != null ? `Darkvision ${ce.senses.darkvisionMeters}m` : null,
            ce.senses.blindsightMeters != null ? `Blindsight ${ce.senses.blindsightMeters}m` : null,
            ce.senses.tremorsenseMeters != null ? `Tremorsense ${ce.senses.tremorsenseMeters}m` : null,
            ce.senses.truesightMeters != null ? `Truesight ${ce.senses.truesightMeters}m` : null,
            ce.senses.passivePerception != null ? `PP ${ce.senses.passivePerception}` : null,
          ]
            .filter(Boolean)
            .join(", ")}
        </div>
      )}

      {(ce.damageResistances.length > 0 ||
        ce.damageImmunities.length > 0 ||
        ce.damageVulnerabilities.length > 0 ||
        ce.conditionImmunities.length > 0) && (
        <div className="mt-2 space-y-1 text-xs text-slate-300">
          {ce.damageResistances.length > 0 && (
            <p>
              <span className="text-slate-500">{t("entity.form.damageResistances")}: </span>
              {ce.damageResistances.map((entry) => damageTypeLabels.get(entry) ?? entry).join(", ")}
            </p>
          )}
          {ce.damageImmunities.length > 0 && (
            <p>
              <span className="text-slate-500">{t("entity.form.damageImmunities")}: </span>
              {ce.damageImmunities.map((entry) => damageTypeLabels.get(entry) ?? entry).join(", ")}
            </p>
          )}
          {ce.damageVulnerabilities.length > 0 && (
            <p>
              <span className="text-slate-500">{t("entity.form.damageVulnerabilities")}: </span>
              {ce.damageVulnerabilities.map((entry) => damageTypeLabels.get(entry) ?? entry).join(", ")}
            </p>
          )}
          {ce.conditionImmunities.length > 0 && (
            <p>
              <span className="text-slate-500">{t("entity.form.conditionImmunities")}: </span>
              {ce.conditionImmunities.map((entry) => conditionLabels.get(entry) ?? entry).join(", ")}
            </p>
          )}
        </div>
      )}

      {ce.actions && (
        <div className="mt-2 text-xs text-slate-300">
          <span className="text-slate-500">{t("entity.form.actions")}: </span>
          <span className="whitespace-pre-wrap">{ce.actions}</span>
        </div>
      )}

      {ce.combatActions.length > 0 && (
        <div className="mt-2 space-y-2 text-xs text-slate-300">
          <span className="text-slate-500">{t("entity.form.combatActions")}:</span>
          {ce.combatActions.map((action) => (
            <div key={action.id} className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-slate-100">{action.name}</span>
                <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
                  {action.kind.replace(/_/g, " ")}
                </span>
              </div>
              {describeCombatAction(action) && (
                <p className="mt-1 text-slate-400">{describeCombatAction(action)}</p>
              )}
              {action.description && (
                <p className="mt-1 text-slate-500">{action.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {ce.notesPublic && (
        <p className="mt-2 text-xs text-slate-400">{ce.notesPublic}</p>
      )}

      {ce.imageUrl && (
        <img
          src={ce.imageUrl}
          alt={ce.name}
          className="mt-2 h-20 w-20 rounded-xl border border-slate-700 object-cover"
        />
      )}
    </div>
  );
};
