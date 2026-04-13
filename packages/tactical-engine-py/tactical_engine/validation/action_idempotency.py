import time

DEFAULT_TTL_SECONDS = 10 * 60  # 10 minutes


class ActionIdempotencyTracker:
    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._seen: dict[str, float] = {}  # action_id -> timestamp
        self._ttl = ttl_seconds

    def has(self, action_id: str) -> bool:
        self._evict()
        return action_id in self._seen

    def record(self, action_id: str) -> None:
        self._evict()
        self._seen[action_id] = time.monotonic()

    def _evict(self) -> None:
        cutoff = time.monotonic() - self._ttl
        self._seen = {k: v for k, v in self._seen.items() if v >= cutoff}
