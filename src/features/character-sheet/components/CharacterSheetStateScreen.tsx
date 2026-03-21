type Props = {
  error?: string | null;
};

export const CharacterSheetStateScreen = ({ error = null }: Props) => {
  if (!error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-void-950 text-slate-400">
        Loading character sheet...
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-void-950">
      <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-6 text-center text-rose-300">
        <p className="mb-2 font-bold">Failed to load character sheet</p>
        <p className="text-xs text-rose-400/80">{error}</p>
      </div>
    </div>
  );
};
