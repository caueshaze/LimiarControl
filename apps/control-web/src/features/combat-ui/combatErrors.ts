export const MISSING_DISTANCE_MARKER = "distance not configured";

export function isMissingDistanceError(msg: string): boolean {
  return msg.toLowerCase().includes(MISSING_DISTANCE_MARKER);
}

export function toPlayerFriendlyError(rawMsg: string): string {
  if (isMissingDistanceError(rawMsg)) {
    return "Distância não configurada — aguarde o GM definir as distâncias antes de agir.";
  }
  return rawMsg;
}
