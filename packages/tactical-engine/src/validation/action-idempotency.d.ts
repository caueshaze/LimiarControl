export declare class ActionIdempotencyTracker {
    private readonly seenActionIds;
    has(actionId: string): boolean;
    record(actionId: string): void;
}
