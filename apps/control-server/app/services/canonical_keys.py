from __future__ import annotations

import re


_SEPARATORS_RE = re.compile(r"[\s\-_]+")


def normalize_canonical_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip().lower()
    if not text:
        return ""
    return _SEPARATORS_RE.sub("_", text)


def canonical_keys_equal(a: object, b: object) -> bool:
    return normalize_canonical_key(a) == normalize_canonical_key(b)
