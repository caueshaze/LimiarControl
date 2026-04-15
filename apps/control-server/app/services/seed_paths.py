from __future__ import annotations

from pathlib import Path


def resolve_base_seed_path(source_file: str | Path, filename: str) -> Path:
    source_path = Path(source_file).resolve()
    candidate_with_base_dir: Path | None = None
    last_candidate: Path | None = None

    for ancestor in (source_path.parent, *source_path.parents):
        candidate = ancestor / "Base" / filename
        if candidate.is_file():
            return candidate
        if candidate_with_base_dir is None and candidate.parent.is_dir():
            candidate_with_base_dir = candidate
        last_candidate = candidate

    return candidate_with_base_dir or last_candidate or Path("Base") / filename
