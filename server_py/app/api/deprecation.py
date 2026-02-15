import logging
from datetime import date
from typing import Any

from fastapi import Request

logger = logging.getLogger("app.deprecation")


def log_deprecated_route(
    request: Request | None,
    *,
    old_path: str,
    new_path: str,
    removal_date: date,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "old_path": old_path,
        "new_path": new_path,
        "removal_date": removal_date.isoformat(),
    }
    if request is not None:
        payload["method"] = request.method
        payload["path"] = request.url.path
        payload["client"] = request.client.host if request.client else None
    if extra:
        payload.update(extra)
    logger.warning("Deprecated route used", extra=payload)
