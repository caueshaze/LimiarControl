import type { CampaignEntity, CampaignEntityPayload, EntityCategory } from "../../../entities/campaign-entity";
import { useLocale } from "../../../shared/hooks/useLocale";
import { CampaignEntityCard } from "./CampaignEntityCard";

const CATEGORY_TABS: Array<EntityCategory | "all"> = ["all", "npc", "enemy", "creature", "ally"];

type Props = {
  entities: CampaignEntity[];
  query: string;
  onQueryChange: (query: string) => void;
  categoryFilter: EntityCategory | "all";
  onCategoryChange: (category: EntityCategory | "all") => void;
  onUpdate?: (entityId: string, payload: CampaignEntityPayload) => Promise<void> | void;
  onRemove?: (entityId: string) => Promise<void> | void;
};

export const CampaignEntityList = ({
  entities,
  query,
  onQueryChange,
  categoryFilter,
  onCategoryChange,
  onUpdate,
  onRemove,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="space-y-4">
      <div className="rounded-[26px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.72),rgba(2,6,23,0.92))] p-4 shadow-[0_18px_50px_rgba(2,6,23,0.2)]">
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={t("entity.search")}
          className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-slate-100 transition focus:border-emerald-300/35 focus:outline-none placeholder:text-slate-500"
        />
        <div className="mt-4 flex flex-wrap gap-2">
          {CATEGORY_TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => onCategoryChange(tab)}
              className={`rounded-full border px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.24em] transition-colors ${
                categoryFilter === tab
                  ? "border-emerald-300/30 bg-emerald-400/10 text-white"
                  : "border-white/8 bg-white/[0.03] text-slate-300 hover:bg-white/[0.06] hover:text-white"
              }`}
            >
              {t(`entity.category.${tab}`)}
            </button>
          ))}
        </div>
      </div>

      {entities.length === 0 ? (
        <div className="rounded-[26px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.72),rgba(2,6,23,0.92))] p-5 text-sm text-slate-400">
          {t("entity.empty")}
        </div>
      ) : (
        <div className="space-y-3">
          {entities.map((entity) => (
            <CampaignEntityCard
              key={entity.id}
              entity={entity}
              onUpdate={onUpdate}
              onRemove={onRemove}
            />
          ))}
        </div>
      )}
    </div>
  );
};
