const DEFAULT_TTL_MS = 10 * 60 * 1000; // 10 minutes

export class ActionIdempotencyTracker {
  private readonly seen = new Map<string, number>(); // actionId -> timestamp
  private readonly ttlMs: number;

  constructor(ttlMs = DEFAULT_TTL_MS) {
    this.ttlMs = ttlMs;
  }

  has(actionId: string): boolean {
    this.evict();
    return this.seen.has(actionId);
  }

  record(actionId: string): void {
    this.evict();
    this.seen.set(actionId, Date.now());
  }

  private evict(): void {
    const cutoff = Date.now() - this.ttlMs;
    for (const [id, ts] of this.seen) {
      if (ts < cutoff) {
        this.seen.delete(id);
      }
    }
  }
}
