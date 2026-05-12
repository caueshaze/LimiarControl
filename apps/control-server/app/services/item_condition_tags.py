from __future__ import annotations

from collections.abc import Iterable

ALLOWED_ITEM_CONDITION_TAGS = {"broken"}


def normalize_item_condition_tags(tags: list[str] | None) -> list[str]:
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise ValueError("condition tags must be a list")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        if not isinstance(raw, str):
            raise ValueError("condition tag must be a string")
        tag = raw.strip()
        if not tag:
            raise ValueError("condition tag cannot be blank")
        if tag not in ALLOWED_ITEM_CONDITION_TAGS:
            raise ValueError(f"invalid condition tag: {tag}")
        if tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized


def add_item_condition_tag(existing: Iterable[str] | None, tag: str) -> tuple[list[str], bool]:
    current = normalize_item_condition_tags(list(existing) if existing is not None else [])
    if tag in current:
        return current, False
    return current + [tag], True


def remove_item_condition_tag(existing: Iterable[str] | None, tag: str) -> tuple[list[str], bool]:
    current = normalize_item_condition_tags(list(existing) if existing is not None else [])
    if tag not in current:
        return current, False
    return [value for value in current if value != tag], True

