type Props = {
  isPlay: boolean;
  isSheetLocked: boolean;
  playContextLabel?: string | null;
};

export const CharacterSheetStatusBanners = ({
  isPlay,
  isSheetLocked,
  playContextLabel,
}: Props) => (
  <>
    {isSheetLocked && (
      <div className="rounded-2xl border border-slate-700/50 bg-slate-900/60 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="h-2 w-2 shrink-0 rounded-full bg-slate-500" />
          <p className="text-sm text-slate-400">
            Sua ficha está confirmada e{" "}
            <span className="font-semibold text-slate-300">não pode ser alterada</span>.
            Apenas o mestre pode fazer edições.
          </p>
        </div>
      </div>
    )}

    {isPlay && playContextLabel && (
      <div className="rounded-[28px] border border-sky-400/20 bg-sky-400/10 px-5 py-4 shadow-[0_16px_40px_rgba(14,165,233,0.12)]">
        <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-sky-300">
          GM Play View
        </p>
        <p className="mt-2 text-sm text-slate-100">
          Viewing <span className="font-semibold text-sky-200">{playContextLabel}</span>'s live
          {" "}play sheet from the GM dashboard.
        </p>
      </div>
    )}
  </>
);
