type Props = {
  players: { userId: string; displayName: string }[];
  onClose: () => void;
};

export const GmDashboardMissingSheetsBanner = ({ players, onClose }: Props) => {
  if (players.length === 0) return null;

  return (
    <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 shrink-0 text-lg text-amber-400">&#9888;</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-amber-300">
            Session blocked - players without a character sheet:
          </p>
          <ul className="mt-2 space-y-1">
            {players.map((player) => (
              <li key={player.userId} className="text-sm text-amber-200">
                {player.displayName}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-amber-500">
            All players must fill and save their character sheet before the session can start.
          </p>
        </div>
        <button onClick={onClose} className="shrink-0 text-xs text-amber-500 hover:text-amber-300">
          &#10005;
        </button>
      </div>
    </div>
  );
};
