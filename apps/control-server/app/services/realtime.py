from datetime import datetime, timezone
from typing import Any


def campaign_channel(campaign_id: str) -> str:
    return f"campaign:{campaign_id}"


def session_channel(session_id: str) -> str:
    return f"session:{session_id}"


def event_version(timestamp: datetime | None = None) -> int:
    source = timestamp or datetime.now(timezone.utc)
    return int(source.timestamp() * 1000)


def build_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    version: int | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {"type": event_type, "payload": payload}
    if version is not None:
        message["version"] = version
    return message
