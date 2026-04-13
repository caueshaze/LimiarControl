"""Simple in-memory rate limiter for auth endpoints.

Uses a sliding-window counter per IP. No external dependencies.
Suitable for single-process deployments. For multi-process/multi-node,
move to Redis-backed rate limiting.
"""

import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Endpoints subject to rate limiting (path prefix, max_requests, window_seconds)
_RATE_LIMITED_PATHS: list[tuple[str, int, int]] = [
    ("/api/auth/login", 5, 60),
    ("/api/auth/register", 5, 60),
]

_hits: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(key: str, max_requests: int, window: int) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.monotonic()
    timestamps = _hits[key]
    # Prune old entries
    cutoff = now - window
    _hits[key] = [t for t in timestamps if t > cutoff]
    if len(_hits[key]) >= max_requests:
        return False
    _hits[key].append(now)
    return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        for prefix, max_req, window in _RATE_LIMITED_PATHS:
            if path == prefix and request.method == "POST":
                ip = _client_ip(request)
                key = f"{prefix}:{ip}"
                if not _check_rate_limit(key, max_req, window):
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Try again later."},
                    )
                break
        return await call_next(request)
