import { useLocale } from "../../shared/hooks/useLocale";
import type { CatalogTab } from "./catalogPage.utils";

type Props = {
  activeTab: CatalogTab;
  onChange: (value: CatalogTab) => void;
};

export const CatalogTabs = ({ activeTab, onChange }: Props) => {
  const { t } = useLocale();

  return (
    <div className="flex w-fit gap-1 rounded-full border border-white/8 bg-white/[0.02] p-1">
      <TabButton
        active={activeTab === "items"}
        label={t("catalog.tabItems")}
        onClick={() => onChange("items")}
      />
      <TabButton
        active={activeTab === "spells"}
        label={t("catalog.tabSpells")}
        onClick={() => onChange("spells")}
      />
    </div>
  );
};

const TabButton = ({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`rounded-full px-5 py-2.5 text-xs font-bold uppercase tracking-[0.22em] transition-all ${
      active
        ? "bg-white/10 text-white shadow-[0_2px_12px_rgba(255,255,255,0.06)]"
        : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
    }`}
  >
    {label}
  </button>
);
