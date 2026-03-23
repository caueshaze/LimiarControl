import { type ReactNode, useState } from "react";
import {
  ENTITY_ABILITIES,
  ENTITY_CONDITIONS,
  ENTITY_DAMAGE_TYPES,
  getCampaignEntityAbilityModifier,
  getCampaignEntityExplicitSkillEntries,
  getCampaignEntityInitiativeBonus,
  getCampaignEntitySavingThrowEntries,
  withSignedBonus,
  type CampaignEntity,
  type CampaignEntityPayload,
} from "../../../entities/campaign-entity";
import { describeCombatAction } from "../../../entities/campaign-entity/describeCombatAction";
import { useLocale } from "../../../shared/hooks/useLocale";
import { CategoryBadge } from "./CategoryBadge";
import { CampaignEntityForm } from "./CampaignEntityForm";

type Props = {
  entity: CampaignEntity;
  onUpdate?: (entityId: string, payload: CampaignEntityPayload) => Promise<void> | void;
  onRemove?: (entityId: string) => Promise<void> | void;
};

const StatPill = ({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "override";
}) => (
  <span
    className={`rounded-lg px-2 py-1 text-[10px] font-bold uppercase ${
      tone === "override"
        ? "border border-emerald-500/30 bg-emerald-500/12 text-emerald-200"
        : "bg-slate-800 text-slate-300"
    }`}
  >
    {children}
  </span>
);

export const CampaignEntityCard = ({ entity, onUpdate, onRemove }: Props) => {
  const { t } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(false);

  const handleRemove = async () => {
    if (!onRemove) return;
    setRemoving(true);
    try {
      await onRemove(entity.id);
    } finally {
      setRemoving(false);
    }
  };

  if (editing && onUpdate) {
    return (
      <CampaignEntityForm
        initial={entity}
        onSave={async (payload) => {
          await onUpdate(entity.id, payload);
          setEditing(false);
        }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  const saveEntries = getCampaignEntitySavingThrowEntries(entity);
  const skillEntries = getCampaignEntityExplicitSkillEntries(entity);
  const initiativeBonus = getCampaignEntityInitiativeBonus(entity);
  const damageTypeLabels = new Map(ENTITY_DAMAGE_TYPES.map((entry) => [entry.key, entry.label]));
  const conditionLabels = new Map(ENTITY_CONDITIONS.map((entry) => [entry.key, entry.label]));

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="truncate text-base font-semibold text-slate-100">{entity.name}</p>
            <CategoryBadge category={entity.category} />
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-400">
            {entity.size && <span>{entity.size}</span>}
            {entity.creatureType && (
              <span>
                {entity.creatureType}
                {entity.creatureSubtype ? ` (${entity.creatureSubtype})` : ""}
              </span>
            )}
            {entity.armorClass != null && <span>AC {entity.armorClass}</span>}
            {entity.maxHp != null && <span>HP {entity.maxHp}</span>}
            {entity.speedMeters != null && <span>{entity.speedMeters}m</span>}
            <span>{t("entity.card.initiativeShort")} {withSignedBonus(initiativeBonus)}</span>
          </div>
          {entity.description && (
            <p className="mt-1 text-xs text-slate-400 line-clamp-2">{entity.description}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="shrink-0 rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200"
        >
          {expanded ? t("entity.card.hide") : t("entity.card.details")}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 space-y-3 text-xs text-slate-300">
          <div className="grid gap-3 lg:grid-cols-2">
            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                {t("entity.form.abilities")}
              </p>
              <div className="flex flex-wrap gap-2">
                {ENTITY_ABILITIES.map((ability) => (
                  <StatPill key={ability.key}>
                    {ability.short} {entity.abilities[ability.key]} ({withSignedBonus(getCampaignEntityAbilityModifier(entity.abilities[ability.key]))})
                  </StatPill>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                {t("entity.form.savingThrows")}
              </p>
              <div className="flex flex-wrap gap-2">
                {saveEntries.map((ability) => (
                  <StatPill key={ability.key} tone={ability.isOverride ? "override" : "default"}>
                    {ability.short} {withSignedBonus(ability.bonus)}
                  </StatPill>
                ))}
              </div>
            </div>
          </div>

          {skillEntries.length > 0 && (
            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                {t("entity.form.skills")}
              </p>
              <div className="flex flex-wrap gap-2">
                {skillEntries.map((skill) => (
                  <StatPill key={skill.key}>
                    {skill.label} {withSignedBonus(skill.bonus)}
                  </StatPill>
                ))}
              </div>
            </div>
          )}

          <div className="grid gap-3 lg:grid-cols-2">
            {entity.senses && (
              <div>
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  {t("entity.form.senses")}
                </p>
                <div className="flex flex-wrap gap-2">
                  {entity.senses.darkvisionMeters != null && <StatPill>Darkvision {entity.senses.darkvisionMeters}m</StatPill>}
                  {entity.senses.blindsightMeters != null && <StatPill>Blindsight {entity.senses.blindsightMeters}m</StatPill>}
                  {entity.senses.tremorsenseMeters != null && <StatPill>Tremorsense {entity.senses.tremorsenseMeters}m</StatPill>}
                  {entity.senses.truesightMeters != null && <StatPill>Truesight {entity.senses.truesightMeters}m</StatPill>}
                  {entity.senses.passivePerception != null && <StatPill>PP {entity.senses.passivePerception}</StatPill>}
                </div>
              </div>
            )}

            {entity.spellcasting && (
              <div>
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  {t("entity.form.spellcasting")}
                </p>
                <div className="flex flex-wrap gap-2">
                  {entity.spellcasting.ability && <StatPill>{entity.spellcasting.ability}</StatPill>}
                  {entity.spellcasting.saveDc != null && <StatPill>DC {entity.spellcasting.saveDc}</StatPill>}
                  {entity.spellcasting.attackBonus != null && <StatPill>Spell {withSignedBonus(entity.spellcasting.attackBonus)}</StatPill>}
                </div>
              </div>
            )}
          </div>

          {(entity.damageResistances.length > 0 ||
            entity.damageImmunities.length > 0 ||
            entity.damageVulnerabilities.length > 0 ||
            entity.conditionImmunities.length > 0) && (
            <div className="grid gap-3 lg:grid-cols-2">
              {entity.damageResistances.length > 0 && (
                <div>
                  <span className="text-slate-500">{t("entity.form.damageResistances")}: </span>
                  {entity.damageResistances.map((entry) => damageTypeLabels.get(entry) ?? entry).join(", ")}
                </div>
              )}
              {entity.damageImmunities.length > 0 && (
                <div>
                  <span className="text-slate-500">{t("entity.form.damageImmunities")}: </span>
                  {entity.damageImmunities.map((entry) => damageTypeLabels.get(entry) ?? entry).join(", ")}
                </div>
              )}
              {entity.damageVulnerabilities.length > 0 && (
                <div>
                  <span className="text-slate-500">{t("entity.form.damageVulnerabilities")}: </span>
                  {entity.damageVulnerabilities.map((entry) => damageTypeLabels.get(entry) ?? entry).join(", ")}
                </div>
              )}
              {entity.conditionImmunities.length > 0 && (
                <div>
                  <span className="text-slate-500">{t("entity.form.conditionImmunities")}: </span>
                  {entity.conditionImmunities.map((entry) => conditionLabels.get(entry) ?? entry).join(", ")}
                </div>
              )}
            </div>
          )}

          {entity.actions && (
            <div>
              <span className="text-slate-500">{t("entity.form.actions")}: </span>
              <span className="whitespace-pre-wrap">{entity.actions}</span>
            </div>
          )}

          {entity.combatActions.length > 0 && (
            <div>
              <span className="text-slate-500">{t("entity.form.combatActions")}: </span>
              <div className="mt-2 space-y-2">
                {entity.combatActions.map((action) => (
                  <div key={action.id} className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2">
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
            </div>
          )}

          {entity.notesPublic && (
            <div>
              <span className="text-slate-500">{t("entity.form.notesPublic")}: </span>
              {entity.notesPublic}
            </div>
          )}

          {entity.notesPrivate && (
            <div>
              <span className="text-amber-500/70">{t("entity.form.notesPrivate")}: </span>
              {entity.notesPrivate}
            </div>
          )}

          {entity.imageUrl && (
            <img
              src={entity.imageUrl}
              alt={entity.name}
              className="mt-2 h-24 w-24 rounded-xl border border-slate-700 object-cover"
            />
          )}

          <div className="flex gap-2 pt-2">
            {onUpdate && (
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
              >
                {t("entity.card.edit")}
              </button>
            )}
            {onRemove && (
              <button
                type="button"
                onClick={handleRemove}
                disabled={removing}
                className="rounded-full border border-red-500/30 px-3 py-1 text-xs text-red-400 hover:bg-red-500/10 disabled:opacity-50"
              >
                {removing ? "..." : t("entity.card.remove")}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
