import {
  ENTITY_CONDITIONS,
  ENTITY_DAMAGE_TYPES,
  type EntityCategory,
} from "../../../entities/campaign-entity";
import type { SessionEntityPlayer } from "../../../entities/session-entity";
import { CategoryBadge } from "../../campaign-entities";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  entity: SessionEntityPlayer;
};

export const PlayerEntityCard = ({ entity }: Props) => {
  const { t } = useLocale();
  const ce = entity.entity;
  if (!ce) return null;

  const displayName = entity.label ? `${ce.name} (${entity.label})` : ce.name;
  const category = (ce.category ?? "npc") as EntityCategory;
  const isDead = typeof entity.currentHp === "number" && entity.currentHp <= 0;
  const damageTypeLabels = new Map(ENTITY_DAMAGE_TYPES.map((entry) => [entry.key, entry.label]));
  const conditionLabels = new Map(ENTITY_CONDITIONS.map((entry) => [entry.key, entry.label]));

  return (
    <div className="rounded-[24px] border border-white/8 bg-white/4 p-4 text-sm text-slate-200">
      <div className="flex items-center gap-2">
        <p className="text-base font-semibold text-white">{displayName}</p>
        <CategoryBadge category={category} />
        {isDead && (
          <span className="rounded-full border border-red-500/30 bg-red-500/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.18em] text-red-200">
            {t("entity.dead")}
          </span>
        )}
      </div>

      {ce.description && (
        <p className="mt-3 text-sm leading-7 text-slate-100/95">
          {ce.description}
        </p>
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

      {ce.notesPublic && (
        <p className="mt-2 text-xs text-slate-400">{ce.notesPublic}</p>
      )}

      {ce.imageUrl && (
        <img
          src={ce.imageUrl}
          alt={ce.name}
          className="mt-3 w-full rounded-xl border border-slate-700 object-contain"
        />
      )}
    </div>
  );
};
