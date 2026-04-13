import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  open: boolean;
  fieldLabel: string;
  onCancel: () => void;
  onConfirm: () => void;
};

export const CharacterSheetInventoryResetConfirmDialog = ({
  open,
  fieldLabel,
  onCancel,
  onConfirm,
}: Props) => {
  const { t } = useLocale();

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl border border-rose-500/30 bg-slate-950 p-8 shadow-2xl">
        <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-rose-400">
          {t("sheet.creation.confirmWarning")}
        </p>
        <h2 className="mt-2 text-lg font-bold text-white">
          {t("sheet.creation.inventoryResetTitle")}
        </h2>
        <p className="mt-3 text-sm text-slate-400">
          {t("sheet.creation.inventoryResetBodyStart")}{" "}
          <span className="font-semibold text-white">{fieldLabel.toLowerCase()}</span>{" "}
          {t("sheet.creation.inventoryResetBodyEnd")}
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full border border-slate-700 px-5 py-2.5 text-xs font-bold uppercase tracking-widest text-slate-300 hover:border-slate-500"
          >
            {t("sheet.creation.cancel")}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-full bg-rose-500 px-5 py-2.5 text-xs font-bold uppercase tracking-widest text-slate-950 hover:bg-rose-400 active:scale-95"
          >
            {t("sheet.creation.inventoryResetConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
};
