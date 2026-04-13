import type { CombatState, ControllerType, Token } from "@limiarmap/shared-contracts";
import { canTokenAct } from "@limiarmap/tactical-engine";

export function canControlToken(
  actorId: string,
  actorType: ControllerType,
  token: Token
): boolean {
  if (actorType === "gm" || actorType === "limiarControl") {
    return true;
  }

  return token.controllerId === actorId && token.controllerType === actorType;
}

export function canSubmitTacticalAction(
  actorId: string,
  actorType: ControllerType,
  token: Token,
  combatState: CombatState
): boolean {
  return canControlToken(actorId, actorType, token) && canTokenAct(combatState, token.combatantId);
}

export function getTacticalActionRejectionReason(
  actorId: string,
  actorType: ControllerType,
  token: Token,
  combatState: CombatState
): string | null {
  if (!canControlToken(actorId, actorType, token)) {
    return "not_token_controller";
  }

  if (!canTokenAct(combatState, token.combatantId)) {
    return "out_of_turn";
  }

  return null;
}
