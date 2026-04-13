import type { SessionCommand, SessionRuntimeState } from "./sessionRuntime.types";
import { createInitialSessionRuntimeState } from "./sessionRuntime.types";

type SessionRealtimeMessage = {
  payload?: Record<string, unknown>;
  type?: string;
};

const toSessionCommand = (
  command: SessionCommand["command"],
  payload?: Record<string, unknown>,
): SessionCommand => ({
  command,
  data: payload,
  issuedBy: typeof payload?.issuedBy === "string" ? payload.issuedBy : undefined,
  issuedAt: typeof payload?.issuedAt === "string" ? payload.issuedAt : undefined,
});

export const reduceSessionRuntimeMessage = (
  current: SessionRuntimeState,
  message: SessionRealtimeMessage,
): SessionRuntimeState => {
  const type = message.type ?? "";
  const payload = message.payload;

  switch (type) {
    case "shop_opened":
      return {
        ...current,
        shopOpen: true,
        lastCommand: toSessionCommand("open_shop", payload),
      };
    case "shop_closed":
      return {
        ...current,
        shopOpen: false,
        lastCommand: toSessionCommand("close_shop", payload),
      };
    case "roll_requested":
      return {
        ...current,
        lastCommand: toSessionCommand("request_roll", payload),
      };
    case "combat_started":
      return {
        ...current,
        combatActive: true,
      };
    case "combat_ended":
      return {
        ...current,
        combatActive: false,
      };
    case "rest_started":
      return {
        ...current,
        restState: payload?.restType === "long_rest" ? "long_rest" : "short_rest",
      };
    case "rest_ended":
      return {
        ...current,
        restState: "exploration",
      };
    case "gm_command": {
      const commandPayload = payload?.command && typeof payload.command === "string"
        ? payload
        : null;
      if (!commandPayload) {
        return current;
      }
      return {
        ...current,
        shopOpen:
          commandPayload.command === "open_shop"
            ? true
            : commandPayload.command === "close_shop"
              ? false
              : current.shopOpen,
        lastCommand: {
          command: commandPayload.command as SessionCommand["command"],
          data:
            typeof commandPayload.data === "object" && commandPayload.data
              ? (commandPayload.data as Record<string, unknown>)
              : undefined,
          issuedBy:
            typeof commandPayload.issuedBy === "string" ? commandPayload.issuedBy : undefined,
          issuedAt:
            typeof commandPayload.issuedAt === "string" ? commandPayload.issuedAt : undefined,
        },
      };
    }
    case "session_closed":
    case "session_ended":
      return {
        ...createInitialSessionRuntimeState(),
        sessionEndedAt:
          typeof payload?.endedAt === "string" ? payload.endedAt : new Date().toISOString(),
      };
    default:
      return current;
  }
};
