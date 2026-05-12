import { useSession } from "./useSession";
export type { SessionCommand } from "./sessionRuntime.types";

export const useSessionCommands = () => {
  const {
    clearCommand,
    clearSessionEnded,
    combatActive,
    connectionState,
    lastCommand,
    restState,
    sessionEndedAt,
    shopOpen,
    gameTimeSeconds,
  } = useSession();

  return {
    lastCommand,
    clearCommand,
    connectionState,
    sessionEndedAt,
    clearSessionEnded,
    shopOpen,
    combatActive,
    restState,
    gameTimeSeconds,
  };
};
