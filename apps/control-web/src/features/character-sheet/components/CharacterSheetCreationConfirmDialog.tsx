import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  open: boolean;
  disabled: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export const CharacterSheetCreationConfirmDialog = ({
  open,
  disabled,
  onCancel,
  onConfirm,
}: Props) => {
  const { t } = useLocale();

  if (!open) {
    return null;
  }

  const confirmBody = t("sheet.creation.confirmBody");
  const marker = "cannot be changed";
  const [before, after] = confirmBody.split(marker);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl border border-amber-500/30 bg-slate-950 p-8 shadow-2xl">
        <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-amber-400">
          {t("sheet.creation.confirmWarning")}
        </p>
        <h2 className="mt-2 text-lg font-bold text-white">
          {t("sheet.creation.confirmTitle")}
        </h2>
        <p className="mt-3 text-sm text-slate-400">
          {after !== undefined ? (
            <>
              {before}
              <span className="font-semibold text-white">{marker}</span>
              {after}
            </>
          ) : (
            confirmBody
          )}
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
            disabled={disabled}
            className={`rounded-full px-5 py-2.5 text-xs font-bold uppercase tracking-widest ${
              disabled
                ? "cursor-not-allowed border border-white/8 text-slate-600"
                : "bg-amber-500 text-slate-950 hover:bg-amber-400 active:scale-95"
            }`}
          >
            {t("sheet.creation.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
};
