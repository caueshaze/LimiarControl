/**
 * Centralized dedup for roll events.
 *
 * When the local user submits a roll via HTTP, the event_id is marked as known.
 * When the same event arrives via Centrifugo, the realtime handler skips the
 * toast (the user already saw the result in the dialog).
 *
 * In-memory Set — clears on page refresh; activity log is the durable source.
 */

const knownEventIds = new Set<string>();
const MAX_SIZE = 100;

export function markRollEventKnown(eventId: string) {
  if (knownEventIds.size >= MAX_SIZE) {
    const first = knownEventIds.values().next().value;
    if (first) knownEventIds.delete(first);
  }
  knownEventIds.add(eventId);
}

export function isRollEventKnown(eventId: string): boolean {
  return knownEventIds.has(eventId);
}
