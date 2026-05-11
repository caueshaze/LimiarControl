export const MISSING_DISTANCE_MARKER = "distance not configured";
export const INVALID_EFFECTIVE_FOOTPRINT_CODE = "invalid_effective_footprint";

export function isMissingDistanceError(msg: string): boolean {
  return msg.toLowerCase().includes(MISSING_DISTANCE_MARKER);
}

export function isInvalidEffectiveFootprintError(value: unknown): boolean {
  if (!value) {
    return false;
  }
  if (typeof value === "string") {
    return value.toLowerCase().includes(INVALID_EFFECTIVE_FOOTPRINT_CODE);
  }
  if (typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  if (record.code === INVALID_EFFECTIVE_FOOTPRINT_CODE) {
    return true;
  }
  if (record.error === INVALID_EFFECTIVE_FOOTPRINT_CODE) {
    return true;
  }
  if (record.reason === INVALID_EFFECTIVE_FOOTPRINT_CODE) {
    return true;
  }
  if (record.detail && record.detail !== value) {
    return isInvalidEffectiveFootprintError(record.detail);
  }
  if (record.message && record.message !== value) {
    return isInvalidEffectiveFootprintError(record.message);
  }
  return false;
}

function extractErrorMessage(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  const record = value as Record<string, unknown>;
  if (typeof record.detail === "string") {
    return record.detail;
  }
  if (typeof record.message === "string") {
    return record.message;
  }
  if (typeof record.error === "string") {
    return record.error;
  }
  return "";
}

export function toPlayerFriendlyError(rawMsg: unknown): string {
  if (isInvalidEffectiveFootprintError(rawMsg)) {
    return "Não há espaço suficiente para Aumentar este alvo.";
  }
  const message = extractErrorMessage(rawMsg);
  if (isMissingDistanceError(message)) {
    return "Distância não configurada — aguarde o GM definir as distâncias antes de agir.";
  }
  return message;
}
