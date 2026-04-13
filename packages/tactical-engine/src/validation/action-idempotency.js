export class ActionIdempotencyTracker {
    seenActionIds = new Set();
    has(actionId) {
        return this.seenActionIds.has(actionId);
    }
    record(actionId) {
        this.seenActionIds.add(actionId);
    }
}
