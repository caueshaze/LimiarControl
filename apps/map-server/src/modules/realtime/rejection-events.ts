/**
 * Creates a rejection payload consistent with the HTTP and Centrifugo error shape.
 *
 *  - `reason`  — machine-readable code for programmatic handling
 *  - `message` — human-readable description for logs and debugging
 *
 * HTTP: { message, reason } at response root
 * Centrifugo: { reason, message } inside the event payload
 */
export function createRejectionPayload(
  reason: string,
  message: string,
  extra?: {
    details?: string;
    tokenId?: string;
    pathCostUnits?: number;
    movementBudget?: number;
    exceededBy?: number;
  }
) {
  return {
    reason,
    message,
    ...(extra ?? {})
  };
}
